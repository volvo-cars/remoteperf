# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import time
from contextlib import contextmanager
from typing import Dict, List, Tuple

from src._parsers import linux as linux_parsers
from src._parsers.generic import ParsingError
from src.handlers.posix_implementation_handler import PosixHandlerException, PosixImplementationHandler
from src.models.base import BaseMemorySample, Process, Sample, SystemMemory, SystemUptimeInfo
from src.models.linux import LinuxCpuUsageInfo, LinuxResourceSample
from src.models.super import (
    CpuList,
    MemoryList,
    MemorySampleProcessInfo,
    ProcessMemoryList,
    ProcessResourceList,
    ResourceSampleProcessInfo,
)


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


class BaseLinuxHandler(PosixImplementationHandler):
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

    def stop_mem_measurement(self) -> MemoryList:
        results, _ = self._stop_measurement(self._mem_measurement)
        parsed_results = []
        for sample in results:
            with _handle_parsing_error(sample):
                parsed_results.append(
                    SystemMemory(**linux_parsers.parse_proc_meminfo(sample.data, timestamp=sample.timestamp))
                )
        return MemoryList(parsed_results)

    def start_cpu_measurement_proc_wise(self, interval: float) -> None:
        self._start_measurement(self._cpu_measurement_proc_wise, interval, self._process_cpu_measurements)

    def start_mem_measurement_proc_wise(self, interval: float) -> None:
        self._start_measurement(self._mem_measurement_proc_wise, interval, self._process_mem_measurements)

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

    def _cpu_measurement_proc_wise(self, *args, **kwargs) -> str:
        return self._resource_measurement_proc_wise(*args, **kwargs)

    def _mem_measurement_proc_wise(self, *args, **kwargs) -> str:
        return self._resource_measurement_proc_wise(*args, **kwargs)

    def _mem_measurement(self, **_):
        command = "cat /proc/meminfo"
        return self._client.run_command(command)
