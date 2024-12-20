# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import threading
import time
from datetime import datetime

from remoteperf.clients.base_client import BaseClient


class ThreadException(Exception):
    pass


class ExceptionThread(threading.Thread):
    def __init__(self, *args, timestamp=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._exception = None
        self._output = None
        self._timestamp = timestamp

    def run(self):
        # Overwrites the run() function (which is the exact same, but saves the exception)
        # This is necessary since there is no built-in error handling and run() consumes all errors
        try:
            if self._target:
                self._output = self._target(*self._args, **self._kwargs)
                self._timestamp = self._timestamp or datetime.now()
        # pylint: disable=W0718 # (broad-exception-caught)
        except Exception as e:
            self._exception = e
        finally:
            del self._target, self._args, self._kwargs

    @property
    def exception(self):
        return self._exception

    @property
    def timestamp(self) -> str:
        return self._timestamp

    @property
    def output(self) -> str:
        self.join()
        if self.exception:
            raise self.exception
        return self._output


class DelegatedExecutionThread(ExceptionThread):
    def __init__(
        self,
        client: BaseClient,
        command: str,
        uid: str,
        read_delay: float,
        *args,
        retries: int = 3,
        join=False,
        **kwargs,
    ):
        filename = f"/tmp/remoteperf_delayed_{uid}-{round(datetime.now().timestamp()*100)}"
        # Output from command is streamed into file, so we move the file to avoid race conditions
        command = f"({command}) > {filename}_tmp && mv {filename}_tmp {filename} & echo $!"
        client.add_cleanup("/tmp/remoteperf_delayed_*")
        client.run_command(command)
        super().__init__(
            target=self._delayed_file_read_and_remove,
            args=[read_delay, filename, client],
            kwargs={"retries": retries},
            *args,
            **kwargs,
        )

        self.start()
        if join:
            self.join()

    @staticmethod
    def _delayed_file_read_and_remove(delay: float, filename: str, client: BaseClient, retries: int = 3) -> str:
        _retries = retries
        time.sleep(delay + 0.2)
        command = f"cat {filename}"

        output = client.run_command(command)
        test = []
        while "No such file or directory" in output or not output:
            test.append(output)
            if _retries <= 0:
                raise ThreadException(
                    f"Failed to read file ({filename}) in expected amount of time, with {retries} retries, {test}"
                )
            output = client.run_command(command)
            _retries -= 1
            time.sleep(1)
        client.run_command(f"rm {filename}")

        return output
