# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import logging
import subprocess
import time
from typing import Union, overload

from adbutils import AdbClient, AdbDevice, AdbError, AdbTimeout

from src.clients.lock_client import LockClient, LockClientException


class ADBClientException(LockClientException):
    pass


class ADBClient(LockClient):

    _session: Union[subprocess.Popen, None]

    @overload
    def __init__(
        self, device_id: str, *, host: str = "127.0.0.1", port: int = 5037, timeout: int = 10, retries: int = 2
    ) -> None:
        ...

    @overload
    def __init__(
        self, transport_id: int, *, host: str = "127.0.0.1", port: int = 5037, timeout: int = 10, retries: int = 2
    ) -> None:
        ...

    def __init__(
        self, *args, host: str = "127.0.0.1", port: int = 5037, timeout: int = 10, retries: int = 2, **kwargs
    ) -> None:
        super().__init__()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._host = host
        self._port = port
        self._adb_session = None
        self._device = None
        self._id = kwargs.get("device_id") or kwargs.get("transport_id") or args[0]
        self._retries = retries
        self._timeout = timeout
        self._exception = ADBClientException

    @property
    def connected(self) -> bool:
        return self._adb_session is not None and self._device is not None

    def _connect(self):
        if self.connected:
            return
        try:
            self._adb_session = AdbClient(host=self._host, port=self._port, socket_timeout=self._timeout)
            device_list = self._adb_session.device_list()
        except AdbTimeout as e:
            raise ADBClientException(f"Timeout while trying to connect to adb daemon: {e}") from e
        except (AdbError, ConnectionResetError) as e:
            raise ADBClientException(
                f"Encountered an unexpected error while trying to connect to adb daemon: {e}"
            ) from e
        self._device: AdbDevice = (
            self._adb_session.device(serial=self._id)
            if isinstance(self._id, str)
            else self._adb_session.device(transport_id=self._id)
        )
        try:
            self._device.get_state()
        except (AdbError, ConnectionResetError) as e:
            raise ADBClientException(f"Could not connect to device: {e}. Available devices: {device_list}") from e

    def _disconnect(self):
        try:
            self._adb_session.disconnect(addr=self._host)
        except Exception:  # Does not really matter what happens here: pylint: disable=W0718
            pass
        finally:
            self._device = None

    def _run_command(self, command, *, retries=None, timeout=None, **_):
        _retries = max(retries or self._retries, 1)
        _timeout = timeout or self._timeout
        if not self.connected:
            raise ADBClientException("Cannot run commands: Not connected")
        for attempt in range(1, _retries + 2):
            try:
                return self._device.shell2(command, timeout=_timeout).output.replace("\x00", "")
            except AdbTimeout as e:
                if attempt >= _retries:
                    raise ADBClientException(
                        (
                            f"Timeout: No response received after {_retries+1} attempts"
                            f"while trying to run '{command}' with a timeout of {_timeout}"
                        )
                    ) from e
                self._logger.error(f"Timeout, retrying {attempt}")
            except Exception as e:  # Package throws generic errors intermittently, so pylint: disable=W0718
                if not self._recover_connection():
                    raise ADBClientException(f"Something went wrong when running command '{command}': {e}") from e
        raise ADBClientException(
            (
                f"Timeout: No response received after {_retries+1} attempts"
                f"while trying to run '{command}' with a timeout of {_timeout}"
            )
        )

    def _pull_file(self, path: str, dest: str):
        for _ in range(1, max(self._retries, 0) + 2):
            try:
                return self._device.sync.pull(path, dest)
            except Exception as e:  # Package throws generic errors intermittently, so pylint: disable=W0718
                if not self._recover_connection():
                    raise ADBClientException(f"Encountered an unexpected error while trying to pull file: {e}") from e
        raise ADBClientException(
            (f"Timeout: No response received after {self._retries+1} attempts" f"while trying to pull file {path}")
        )

    def _push_file(self, path: str, dest: str):
        for _ in range(1, max(self._retries, 0) + 2):
            try:
                return self._device.sync.push(path, dest)
            except Exception as e:  # Package throws generic errors intermittently, so pylint: disable=W0718
                if not self._recover_connection():
                    raise ADBClientException(f"Encountered an unexpected error while trying to push file: {e}") from e
        raise ADBClientException(
            (f"Timeout: No response received after {self._retries+1} attempts" f"while trying to pull file {path}")
        )

    def _recover_connection(self) -> bool:
        state = ""
        error = None
        device_list = None
        t0 = time.time()
        while t0 + self._timeout > time.time():
            try:
                device_list = self._adb_session.device_list()
                if any(device.serial == self._device.serial for device in device_list):
                    if (state := self._device.get_state()) == "device":
                        return True
            except Exception as e:  # Package throws generic errors intermittently, so pylint: disable=W0718
                error = e
        if device_list is None:
            raise ADBClientException(f"Error: Failed to retrieve device list: {error}") from error
        raise ADBClientException(
            f"Error: daemon running but active device {self._device} not present in device list:{device_list}"
            + (f". Device state found but was '{state}'" if state != "device" else "")
        ) from error
