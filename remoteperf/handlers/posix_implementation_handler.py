# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import logging
import threading
import time
from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from remoteperf.clients.base_client import BaseClient
from remoteperf.handlers.base_handler import BaseHandler, BaseHandlerException
from remoteperf.models.base import Sample
from remoteperf.utils.fs_utils import RemoteFs
from remoteperf.utils.threading import ExceptionThread


class PosixHandlerException(BaseHandlerException):
    pass


class MissingPosixCapabilityException(BaseHandlerException):
    pass


class PosixImplementationHandler(BaseHandler):
    def __init__(self, client: BaseClient, log_path="logs/", tmp_directory="/tmp"):
        self._logger: logging.Logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._client: BaseClient = client
        self._log_path: Path = Path(log_path)
        self._log_path.mkdir(parents=True, exist_ok=True)
        self._threads: dict = {}
        self._results: dict = {}
        self._tmp_directory = tmp_directory
        self.fs_utils = RemoteFs(client=client, tmp_directory=self._tmp_directory)

    def start_mem_measurement(self, interval: float) -> None:
        self._start_measurement(self._mem_measurement, interval)

    @abstractmethod
    def _cpu_measurement(self):
        pass

    @abstractmethod
    def _mem_measurement(self):
        pass

    @abstractmethod
    def _mem_measurement_proc_wise(self):
        pass

    @abstractmethod
    def _cpu_measurement_proc_wise(self):
        pass

    def _has_capability(self, command: str):
        return self._client.run_command(f"command -v {command}")

    # pylint: disable=R0917
    def __sample(self, results, processed_results, take_measurement_function, interval, processing_function, **kwargs):
        results.append(Sample(data=take_measurement_function(interval=interval, **kwargs), timestamp=datetime.now()))
        if processing_function:
            return processing_function(results, processed_results)
        return results, None

    def _thread_loop(
        self,
        take_measurement_function: callable,
        interval: float,
        stop_flag: threading.Event,
        processing_function: Optional[callable] = None,
        **kwargs,
    ) -> None:
        last_run_time = time.time()
        results, processed_results = self.__sample(
            [], {}, take_measurement_function, interval, processing_function, **kwargs
        )
        while not stop_flag.is_set():
            now = time.time()
            elapsed_time = now - last_run_time

            if elapsed_time >= interval:
                last_run_time += interval
                results, processed_results = self.__sample(
                    results, processed_results, take_measurement_function, interval, processing_function, **kwargs
                )

            remaining_time = max(0, interval - elapsed_time)
            timeout = min(remaining_time, interval / 4)
            if timeout:
                stop_flag.wait(timeout=timeout)
        if processing_function and not processed_results:
            results, processed_results = self.__sample(
                results, processed_results, take_measurement_function, interval, processing_function, **kwargs
            )
        self._results[take_measurement_function] = (results, processed_results)

    def _start_measurement(
        self, function: callable, interval: float, processing_function: Optional[callable] = None, **kwargs
    ):
        if function in self._threads:
            raise PosixHandlerException(f"Measurement of type: {function} already in progress")

        flag = threading.Event()
        thread = ExceptionThread(
            target=self._thread_loop, args=(function, interval, flag, processing_function), kwargs=kwargs
        )
        self._threads[function] = (thread, flag)
        flag.clear()
        thread.start()

    def _stop_measurement(self, function: callable) -> List[Sample]:
        if function not in self._threads:
            raise PosixHandlerException(f"No {function} measurement in progress")

        thread, flag = self._threads[function]
        flag.set()
        thread.join()
        del self._threads[function]
        if function not in self._results:
            raise PosixHandlerException("Thread encountered an error during runtime") from thread.exception
        output = self._results[function]
        del self._results[function]
        return output
