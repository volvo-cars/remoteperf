# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import time
from contextlib import contextmanager
from typing import Dict, List, Tuple

from remoteperf._parsers import linux as linux_parsers
from remoteperf._parsers.generic import ParsingError
from remoteperf.handlers.posix_implementation_handler import PosixHandlerException, PosixImplementationHandler
from remoteperf.models.base import (
    BaseMemorySample,
    DiskInfo,
    DiskIOInfo,
    LinuxNetworkInterfaceDeltaSampleList,
    LinuxNetworkReceiveDeltaSample,
    LinuxNetworkTransmitDeltaSample,
    Process,
    Sample,
    SystemMemory,
    SystemUptimeInfo,
)
from remoteperf.models.linux import LinuxCpuUsageInfo, LinuxResourceSample
from remoteperf.models.super import (
    CpuList,
    DiskInfoList,
    DiskIOList,
    DiskIOProcessSample,
    DiskIOSampleProcessInfo,
    LinuxNetworkInterfaceList,
    MemoryList,
    MemorySampleProcessInfo,
    ProcessDiskIOList,
    ProcessMemoryList,
    ProcessResourceList,
    ResourceSampleProcessInfo,
)
from remoteperf.utils import _dict_utils as dict_utils


class BaseLinuxHandlerException(PosixHandlerException):
    pass


@contextmanager
def _handle_parsing_error(sample1, sample2=None):
    try:
        yield
    except ParsingError as e:
        result = sample1
        if sample2:
            result = f"(sample 1):{sample1}\n\n(sample 2):{sample2}"
        raise BaseLinuxHandlerException(f"Failed to parse data {result}") from e


class BaseLinuxHandler(PosixImplementationHandler):  # pylint: disable=R0904 (too-many-public-methods)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._nonexistant_separator_file = "e39f7761903b"

    def get_cpu_usage(self, interval: float = 0.3) -> LinuxCpuUsageInfo:
        timestamp = time.time()
        cpu_sample_1 = self._cpu_measurement()
        time.sleep(max(timestamp + interval - time.time(), 0))
        cpu_sample_2 = self._cpu_measurement()
        with _handle_parsing_error(cpu_sample_1, cpu_sample_2):
            return LinuxCpuUsageInfo(**linux_parsers.parse_proc_stat(cpu_sample_1, cpu_sample_2))

    def get_mem_usage(self) -> SystemMemory:
        output = self._mem_measurement()
        with _handle_parsing_error(output):
            return SystemMemory(**linux_parsers.parse_proc_meminfo(output))

    def get_network_usage_total(self) -> LinuxNetworkInterfaceList:
        return linux_parsers.parse_net_data(self._net_measurement())

    def get_network_usage(self, interval: float = 0.3) -> LinuxNetworkInterfaceList:
        net_sample_1 = self._net_measurement()
        time.sleep(max(time.time() + interval - time.time(), 0))
        return LinuxNetworkInterfaceList(
            linux_parsers.parse_net_deltadata(dict_utils.dict_diff(net_sample_1, self._net_measurement()))
        )

    def get_cpu_usage_proc_wise(self, interval: float = 0.3, **_) -> ProcessResourceList:
        timestamp = time.time()
        cpu_sample_1 = self._cpu_measurement_proc_wise()
        time.sleep(max(timestamp + interval - time.time(), 0))
        cpu_sample_2 = self._cpu_measurement_proc_wise()
        with _handle_parsing_error(cpu_sample_1, cpu_sample_2):
            return ProcessResourceList(
                ResourceSampleProcessInfo(**p.model_dump(), samples=[sample])
                for p, sample in linux_parsers.parse_cpu_usage_from_proc_files(
                    cpu_sample_1, cpu_sample_2, self._nonexistant_separator_file
                ).items()
            )

    def get_mem_usage_proc_wise(self, **_) -> ProcessMemoryList:
        output = self._mem_measurement_proc_wise()
        with _handle_parsing_error(output):
            return ProcessMemoryList(
                MemorySampleProcessInfo(**p.model_dump(), samples=[sample])
                for p, sample in linux_parsers.parse_mem_usage_from_proc_files(
                    output, self._nonexistant_separator_file
                ).items()
            )

    def get_system_uptime(self) -> SystemUptimeInfo:
        """Gets the system uptime in seconds"""
        command = "cat /proc/uptime | cut -d ' ' -f 1"
        output = self._client.run_command(command)
        return SystemUptimeInfo(total=float(output))

    def get_diskinfo(self) -> DiskInfoList:
        output = linux_parsers.parse_df(self._get_df())
        return DiskInfoList([DiskInfo(**kpis) for _, kpis in output.items()])

    def get_diskio(self) -> DiskIOList:
        output = linux_parsers.parse_proc_diskio(self._get_diskstats())
        return DiskIOList([DiskIOInfo(**kpis) for _, kpis in output.items()])

    def get_diskio_proc_wise(self) -> ProcessDiskIOList:
        output = self._diskio_measurement_proc_wise()
        with _handle_parsing_error(output):
            return ProcessDiskIOList(
                DiskIOSampleProcessInfo(**p.model_dump(), samples=[sample])
                for p, sample in linux_parsers.parse_disk_usage_from_proc_files(
                    output, self._nonexistant_separator_file
                ).items()
            )

    def start_cpu_measurement(self, interval: float) -> None:
        self._start_measurement(self._cpu_measurement, interval)

    def stop_cpu_measurement(self) -> CpuList:
        results, _ = self._stop_measurement(self._cpu_measurement)
        if len(results) < 2:
            results.append(Sample(data=self._cpu_measurement()))
        parsed_results = []
        for s1, s2 in zip(results, results[1:]):
            with _handle_parsing_error(s1, s2):
                parsed_results.append(
                    LinuxCpuUsageInfo(**linux_parsers.parse_proc_stat(s1.data, s2.data, timestamp=s2.timestamp))
                )
        return CpuList(parsed_results)

    def start_net_interface_measurement(self, interval: float) -> None:
        self._start_measurement(self._net_measurement, interval)

    def stop_mem_measurement(self) -> MemoryList:
        results, _ = self._stop_measurement(self._mem_measurement)
        parsed_results = []
        for sample in results:
            with _handle_parsing_error(sample):
                parsed_results.append(
                    SystemMemory(**linux_parsers.parse_proc_meminfo(sample.data, timestamp=sample.timestamp))
                )
        return MemoryList(parsed_results)

    def start_diskinfo_measurement(self, interval: float) -> None:
        self._start_measurement(self._get_df, interval)

    def stop_diskinfo_measurement(self) -> DiskInfoList:
        results, _ = self._stop_measurement(self._get_df)
        processed_results = []
        for sample in results:
            with _handle_parsing_error(sample.data):
                output = linux_parsers.parse_df(sample.data)
                for _, kpis in output.items():
                    kpis["timestamp"] = sample.timestamp
                    processed_results.append(DiskInfo(**kpis))

        return DiskInfoList(processed_results)

    def start_diskio_measurement(self, interval: float) -> None:
        """Starts disk usage measurement"""
        self._start_measurement(self._get_diskstats, interval)

    def stop_diskio_measurement(self) -> DiskIOList:
        """Stops disk usage measurement"""
        results, _ = self._stop_measurement(self._get_diskstats)
        processed_results = []
        for sample in results:
            with _handle_parsing_error(sample):
                output = linux_parsers.parse_proc_diskio(sample.data)
                for _, kpis in output.items():
                    kpis["timestamp"] = sample.timestamp
                    processed_results.append(DiskIOInfo(**kpis))

        return DiskIOList(processed_results)

    def stop_net_interface_measurement(self) -> LinuxNetworkInterfaceList:
        results, _ = self._stop_measurement(self._net_measurement)
        parsed_results = {}
        if len(results) < 2:
            results.append(Sample(data=self._net_measurement()))
        for s1, s2 in zip(results, results[1:]):
            samples = dict_utils.dict_diff(s1.data, s2.data)
            for interface, sample in samples.items():
                if sample:
                    parsed_results.setdefault(interface, {"name": interface})
                    parsed_results[interface].setdefault("receive", []).append(
                        LinuxNetworkReceiveDeltaSample(**sample["receive"])
                    )
                    parsed_results[interface].setdefault("transmit", []).append(
                        LinuxNetworkTransmitDeltaSample(**sample["transmit"])
                    )
        lst = [LinuxNetworkInterfaceDeltaSampleList(**data) for data in parsed_results.values()]
        return LinuxNetworkInterfaceList(lst)

    def start_cpu_measurement_proc_wise(self, interval: float) -> None:
        self._start_measurement(self._cpu_measurement_proc_wise, interval, self._process_cpu_measurements)

    def start_mem_measurement_proc_wise(self, interval: float) -> None:
        self._start_measurement(self._mem_measurement_proc_wise, interval, self._process_mem_measurements)

    def start_diskio_measurement_proc_wise(self, interval: float) -> None:
        self._start_measurement(self._diskio_measurement_proc_wise, interval, self._process_diskio_measurements)

    def stop_cpu_measurement_proc_wise(self) -> ProcessResourceList:
        _, results = self._stop_measurement(self._cpu_measurement_proc_wise)
        lst = [ResourceSampleProcessInfo(**p.model_dump(), samples=samples) for p, samples in results.items()]
        output = ProcessResourceList(lst)
        return output

    def stop_mem_measurement_proc_wise(self) -> ProcessMemoryList:
        _, results = self._stop_measurement(self._mem_measurement_proc_wise)
        output = ProcessMemoryList(
            MemorySampleProcessInfo(**p.model_dump(), samples=samples) for p, samples in results.items()
        )
        return output

    def stop_diskio_measurement_proc_wise(self) -> ProcessDiskIOList:
        _, results = self._stop_measurement(self._diskio_measurement_proc_wise)
        output = ProcessDiskIOList(
            DiskIOSampleProcessInfo(**p.model_dump(), samples=samples) for p, samples in results.items()
        )
        return output

    def _process_cpu_measurements(
        self, results: List[Sample], processed_results: Dict[Process, List[tuple]]
    ) -> Tuple[List[Sample], Dict[Process, List[tuple]]]:
        processed_results = processed_results or {}
        if len(results) < 2:
            return results, processed_results
        with _handle_parsing_error(results[0].data, results[1].data):
            for p, sample in linux_parsers.parse_cpu_usage_from_proc_files(
                results[0].data, results[1].data, self._nonexistant_separator_file, timestamp=results[1].timestamp
            ).items():
                processed_results.setdefault(p, []).append(LinuxResourceSample(**sample))
        return results[-1:], processed_results

    def _process_mem_measurements(
        self, results: List[Sample], processed_results: Dict[Process, List[tuple]]
    ) -> Tuple[List[Sample], Dict[Process, List[tuple]]]:
        processed_results = processed_results or {}
        for result in results:
            with _handle_parsing_error(result.data):
                for p, sample in linux_parsers.parse_mem_usage_from_proc_files(
                    result.data, self._nonexistant_separator_file, timestamp=result.timestamp
                ).items():
                    processed_results.setdefault(p, []).append(BaseMemorySample(**sample))
        return [], processed_results

    def _process_diskio_measurements(
        self, results: List[Sample], processed_results: Dict[Process, List[tuple]]
    ) -> Tuple[List[Sample], Dict[Process, List[tuple]]]:
        processed_results = processed_results or {}
        for result in results:
            with _handle_parsing_error(result.data):
                for p, sample in linux_parsers.parse_disk_usage_from_proc_files(
                    result.data, self._nonexistant_separator_file, timestamp=result.timestamp
                ).items():
                    processed_results.setdefault(p, []).append(DiskIOProcessSample(**sample))
        return [], processed_results

    def _cpu_measurement(self, **_):
        command = "cat /proc/stat | grep cpu"
        return self._client.run_command(command.strip())

    def _resource_measurement_proc_wise(self, **_) -> Tuple[str, str]:
        # We need a seprator here since the cmdline file has no line ending
        # Turns out an error message is a valid separator so we use that ¯\_(ツ)_/¯
        command = (
            r'getconf PAGESIZE && /bin/cat $(ls /proc | grep "[0-9]" | '
            r'sed "s:\([0-9]*\):' + self._nonexistant_separator_file + r" /proc/\1/stat "
            r'/proc/\1/cmdline:") ' + self._nonexistant_separator_file + r" /proc/stat 2>&1"
        )
        return self._client.run_command(command)

    def _io_measurement_proc_wise(self, **_) -> Tuple[str, str]:
        command = (
            r'/bin/cat $(ls /proc | grep "[0-9]" | '
            r'sed "s:\([0-9]*\):' + self._nonexistant_separator_file + r" /proc/\1/stat "
            r'/proc/\1/io /proc/\1/cmdline:") ' + self._nonexistant_separator_file + r" 2>&1"
        )
        return self._client.run_command(command)

    def _cpu_measurement_proc_wise(self, *args, **kwargs) -> str:
        return self._resource_measurement_proc_wise(*args, **kwargs)

    def _mem_measurement_proc_wise(self, *args, **kwargs) -> str:
        return self._resource_measurement_proc_wise(*args, **kwargs)

    def _diskio_measurement_proc_wise(self, *args, **kwargs) -> str:
        return self._io_measurement_proc_wise(*args, **kwargs)

    def _mem_measurement(self, **_):
        command = "cat /proc/meminfo"
        return self._client.run_command(command)

    def _get_diskstats(self, **_):
        command = "cat /proc/diskstats"
        return self._client.run_command(command)

    def _get_df(self, **_):
        command = "df"
        return self._client.run_command(command)

    def _net_measurement(self, **_) -> dict:
        command = "cat /proc/net/dev && date --iso-8601=ns"
        return linux_parsers.parse_proc_net_dev(self._client.run_command(command))
