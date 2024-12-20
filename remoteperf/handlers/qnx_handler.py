# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
from contextlib import contextmanager
from typing import Dict, List, Tuple

from more_itertools import partition

from remoteperf._parsers import qnx as qnx_parsers
from remoteperf._parsers.generic import ParsingError
from remoteperf.handlers.posix_implementation_handler import (
    MissingPosixCapabilityException,
    PosixHandlerException,
    PosixImplementationHandler,
)
from remoteperf.models.base import (
    BaseCpuSample,
    BaseMemorySample,
    BootTimeInfo,
    DiskInfo,
    Process,
    Sample,
    SystemMemory,
    SystemUptimeInfo,
)
from remoteperf.models.qnx import QnxCpuUsageInfo
from remoteperf.models.super import (
    CpuList,
    CpuSampleProcessInfo,
    DiskInfoList,
    MemoryList,
    MemorySampleProcessInfo,
    ProcessCpuList,
    ProcessMemoryList,
)
from remoteperf.utils.threading import DelegatedExecutionThread


class QNXHandlerException(PosixHandlerException):
    pass


class MissingQnxCapabilityException(MissingPosixCapabilityException, QNXHandlerException):
    pass


@contextmanager
def _handle_parsing_error(result):
    try:
        yield
    except ParsingError as e:
        raise QNXHandlerException(f"Failed to parse data {result}") from e


class QNXHandler(PosixImplementationHandler):
    def get_cpu_usage(self, interval: float = 1) -> QnxCpuUsageInfo:
        thread = self._cpu_measurement(int(interval))
        with _handle_parsing_error(thread.output):
            return QnxCpuUsageInfo(**qnx_parsers.parse_hogs_cpu_usage(thread.output, timestamp=thread.timestamp))

    def get_cpu_usage_proc_wise(self, interval: int = 1, **kwargs) -> ProcessCpuList:
        """
        Get process-wise cpu usage.

        :raises MissingQnxCapabilityException: If hogs is not present on target
        """
        cpu_sample = self._cpu_measurement_proc_wise(interval=interval, **kwargs)
        with _handle_parsing_error(cpu_sample.output):
            return ProcessCpuList(
                CpuSampleProcessInfo(**p.model_dump(), samples=[sample])
                for p, sample in qnx_parsers.parse_hogs_pidin_proc_wise(cpu_sample.output).items()
            )

    def get_mem_usage(self) -> SystemMemory:
        result = self._mem_measurement()
        with _handle_parsing_error(result):
            return SystemMemory(**qnx_parsers.parse_proc_vm_stat(result))

    def get_diskinfo(self) -> DiskInfoList:
        output = qnx_parsers.parse_df_qnx(self._get_df())
        return DiskInfoList([DiskInfo(**kpis) for _, kpis in output.items()])

    def get_mem_usage_proc_wise(self, **_) -> ProcessMemoryList:
        """
        Get process-wise memory usage

        :raises MissingQnxCapabilityException: If hogs is not present
        """
        mem_sample = self._mem_measurement_proc_wise()
        with _handle_parsing_error(mem_sample):
            return ProcessMemoryList(
                MemorySampleProcessInfo(**p.model_dump(), samples=[sample])
                for p, sample in qnx_parsers.parse_mem_usage_from_proc_files(mem_sample).items()
            )

    def get_system_uptime(self) -> SystemUptimeInfo:
        pidin = self._client.run_command("pidin info")
        date_data = self._client.run_command("date")
        with _handle_parsing_error(f"pidin: ({pidin}) date: ({date_data})"):
            return SystemUptimeInfo(**qnx_parsers.parse_uptime(pidin, date_data))

    def start_diskinfo_measurement(self, interval: float) -> None:
        self._start_measurement(self._get_df, interval)

    def stop_diskinfo_measurement(self) -> DiskInfoList:
        results, _ = self._stop_measurement(self._get_df)
        processed_results = []
        for sample in results:
            with _handle_parsing_error(sample.data):
                output = qnx_parsers.parse_df_qnx(sample.data)
                for _, kpis in output.items():
                    kpis["timestamp"] = sample.timestamp
                    processed_results.append(DiskInfo(**kpis))

        return DiskInfoList(processed_results)

    def get_boot_time(self) -> BootTimeInfo:
        """
        Get the time it took for the system to boot.

        :raises MissingQnxCapabilityException: If /dev/bmetrics is not found
        """
        if not self.fs_utils.exists("/dev/bmetrics"):
            raise MissingQnxCapabilityException("Cannot measure boot time: /dev/bmetrics not found")
        raw_output = self._client.run_command("cat /dev/bmetrics | grep SYS_BOOT_LOADER_END")
        with _handle_parsing_error(raw_output):
            return BootTimeInfo(**qnx_parsers.parse_bmetrics_boot_time(raw_output))

    def start_cpu_measurement(self, interval: int) -> None:
        """
        Start measurement of system cpu usage.

        :raises QNXHandlerException: If interval is below 1s (top limitation)
        """
        if interval < 1:
            raise QNXHandlerException("Cannot measure at intervals below 1 second")
        self._start_measurement(self._cpu_measurement, interval)

    def stop_cpu_measurement(self) -> CpuList:
        results, _ = self._stop_measurement(self._cpu_measurement)
        parsed_results = []
        for sample in results:
            with _handle_parsing_error(sample.data.output):
                parsed_results.append(
                    QnxCpuUsageInfo(**qnx_parsers.parse_hogs_cpu_usage(sample.data.output, timestamp=sample.timestamp))
                )
        return CpuList(parsed_results)

    def stop_mem_measurement(self) -> MemoryList:
        samples, _ = self._stop_measurement(self._mem_measurement)
        parsed_results = []
        for sample in samples:
            with _handle_parsing_error(sample):
                parsed_results.append(
                    SystemMemory(**qnx_parsers.parse_proc_vm_stat(sample.data, timestamp=sample.timestamp))
                )
        return MemoryList(parsed_results)

    def start_cpu_measurement_proc_wise(self, interval: int, **kwargs) -> None:
        """
        Start measurement of process cpu usage.

        :raises MissingQnxCapabilityException: If hogs is not present on target
        """
        if not self._has_capability("hogs"):
            raise MissingQnxCapabilityException("Cannot measure process-wise cpu usage: hogs not found on target")
        self._start_measurement(self._cpu_measurement_proc_wise, interval, self._process_cpu_measurements, **kwargs)

    def start_mem_measurement_proc_wise(self, interval: int, **_) -> None:
        """
        Start measurement of process memory usage.

        :raises MissingQnxCapabilityException: If hogs is not present on target
        """
        self._start_measurement(self._mem_measurement_proc_wise, interval, self._process_mem_measurements)

    def stop_cpu_measurement_proc_wise(self) -> ProcessCpuList:
        threads, results = self._stop_measurement(self._cpu_measurement_proc_wise)
        for thread in threads:
            thread.data.join()
        _, parsed_results = self._process_cpu_measurements(threads, results)
        return ProcessCpuList(
            CpuSampleProcessInfo(**p.model_dump(), samples=samples) for p, samples in parsed_results.items()
        )

    def stop_mem_measurement_proc_wise(self) -> ProcessMemoryList:
        _, results = self._stop_measurement(self._mem_measurement_proc_wise)
        return ProcessMemoryList(
            MemorySampleProcessInfo(**p.model_dump(), samples=samples) for p, samples in results.items()
        )

    def _cpu_measurement(self, interval: int = 1, **_) -> DelegatedExecutionThread:
        command = rf"hogs -i 1 -s {interval} -% 1000"
        return DelegatedExecutionThread(client=self._client, command=command, uid="hogs", read_delay=interval)

    def _cpu_measurement_proc_wise(self, interval: int = 1, **kwargs) -> DelegatedExecutionThread:
        if not self._has_capability("hogs"):
            raise MissingQnxCapabilityException("Cannot measure process-wise cpu usage: hogs not found on target")
        if interval < 1 and not kwargs.get("force"):
            raise QNXHandlerException("Cannot measure at intervals below 1 second")
        command = f'hogs -i 1 -s {int(interval)} && pidin -F "%a %t %n %A"'
        return DelegatedExecutionThread(
            client=self._client,
            command=command,
            uid="hogs_pidin",
            read_delay=kwargs.get("read_delay", int(interval)),
        )

    def _mem_measurement(self, **_) -> str:
        command = r'cat /proc/vm/stats | grep -E "(page_count|pages_free)"'
        return self._client.run_command(command)

    def _mem_measurement_proc_wise(self, **_) -> str:
        command = (
            r"(cat $(ls /proc | grep '[0-9]' "
            r"| sed 's:\([0-9]*\):rss_pid=\1 /proc/\1/vmstat:'))2>&1 "
            r"| grep rss && echo PIDIN_SEPARATOR && pidin -f atnA"
        )
        return self._client.run_command(command)

    def _process_cpu_measurements(
        self, results: List[Sample], processed_results: Dict[Process, List[tuple]]
    ) -> Tuple[List[Sample], Dict[Process, List[tuple]]]:
        processed_results = processed_results or {}
        dead_threads, alive_threads = partition(lambda t: t.data.is_alive(), results)
        dead_threads = list(dead_threads)
        for thread in dead_threads:
            with _handle_parsing_error(thread.data.output):
                for p, sample in qnx_parsers.parse_hogs_pidin_proc_wise(
                    thread.data.output, timestamp=thread.timestamp
                ).items():
                    processed_results.setdefault(p, []).append(BaseCpuSample(**sample))
        return list(alive_threads), processed_results

    def _process_mem_measurements(
        self, results: List[Sample], processed_results: Dict[Process, List[tuple]]
    ) -> Tuple[List[Sample], Dict[Process, List[tuple]]]:
        processed_results = processed_results or {}
        for result in results:
            with _handle_parsing_error(result.data):
                for p, sample in qnx_parsers.parse_mem_usage_from_proc_files(
                    result.data, timestamp=result.timestamp
                ).items():
                    processed_results.setdefault(p, []).append(BaseMemorySample(**sample))
        return [], processed_results

    def _get_df(self, **_):
        command = "df"
        return self._client.run_command(command)
