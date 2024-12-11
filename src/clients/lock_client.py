# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import pathlib
from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

from src.clients.base_client import BaseClient, BaseClientException
from src.utils.fs_utils import RemoteFs


class LockClientException(BaseClientException):
    pass


class LockClient(BaseClient):
    """
    Base class for handlers with a global lock on their session
    """

    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._call_lock = Lock()
        self._fs_utils = RemoteFs(client=self, tmp_directory=None)
        self._exception = LockClientException
        self._cleanup = {}

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, *_):
        if self._cleanup and exc_type is not LockClientException:
            for path, flags in self._cleanup.items():
                self.run_command(f"rm {flags if flags else ''} {path}")
        self.disconnect()

    def connect(self):
        self._log_lock("connect")
        with self._call_lock:
            return self._connect()

    def run_command(self, command: str, *, retries=None, timeout=None, log_path: str = None, **kwargs) -> str:
        self._log_lock(f"run_command with command: {command}")
        with self._call_lock:
            result = self._run_command(command, retries=retries, timeout=timeout, **kwargs)
        if log_path:
            self._log_command(command, result, log_path)
        return result

    def disconnect(self):
        self._log_lock("disconnect")
        with self._call_lock:
            return self._disconnect()

    def pull_file(self, path: str, dest: str) -> None:  # noqa: C901
        self._log_lock("pull_file")
        _path = pathlib.Path(path)
        _dest = pathlib.Path(dest)

        if not _dest.is_dir():
            if not _dest.parent.exists():
                raise self._exception(f"Local directory {_dest.parent} not found")
        else:
            if not _dest.exists():
                raise self._exception(f"Local directory '{_dest}' not found")
            if not _dest.is_dir():
                raise self._exception(f"Local destination path {_dest} is not a directory")
            _dest = _dest / _path.name
        if _dest.exists():
            if not os.access(str(_dest), os.W_OK):
                raise self._exception(f"Local file {_dest} found, but permissions are insufficient to override")

        if not self._fs_utils.is_file(path):
            if self._fs_utils.is_directory(path):
                raise self._exception(f"Remote path {path} is a directory")
            raise self._exception(f"File path {path} not found on remote")
        if not self._fs_utils.has_read_permissions(path):
            raise self._exception(f"Canot pull {path}, insufficient permissions")

        with self._call_lock:
            return self._pull_file(str(_path), str(_dest))

    def push_file(self, path: str, dest: str) -> None:  # noqa: C901
        self._log_lock("push_file")
        _path = pathlib.Path(path)
        _dest = pathlib.Path(dest)

        if not self._fs_utils.is_directory(_dest):
            if not self._fs_utils.exists(_dest.parent):
                raise self._exception(f"Directory {_dest.parent} not found on remote")
        else:
            if not self._fs_utils.exists(_dest):
                raise self._exception(f"Directory '{_dest}' not found on remote")
            if not self._fs_utils.is_directory(_dest):
                raise self._exception(f"Remote destination path {_dest} is not a directory")
            _dest = _dest / _path.name
        if self._fs_utils.exists(_dest):
            if not self._fs_utils.has_write_permissions(_dest):
                raise self._exception(f"Remote file {_dest} found, but permissions are insufficient to override")

        if not _path.is_file():
            if _path.is_dir():
                raise self._exception(f"Local path {path} is a directory")
            raise self._exception(f"Local file {path} not found.")
        if not os.access(str(_path), os.R_OK):
            raise self._exception(f"Local file {_path} found, but permissions are insufficient to read")
        with self._call_lock:
            return self._push_file(str(_path), str(_dest))

    def add_cleanup(self, path: str, flags: Optional[str] = None):
        self._cleanup[path] = flags

    @abstractmethod
    def _connect(self):
        pass

    @abstractmethod
    def _pull_file(self, path: str, dest: str):
        pass

    @abstractmethod
    def _push_file(self, path: str, dest: str):
        pass

    @abstractmethod
    def _disconnect(self):
        pass

    @abstractmethod
    def _run_command(self, command, *, retries=None, timeout=None):
        pass

    def _log_lock(self, source):
        if self._call_lock.locked():
            self._logger.debug(f"{source} called when lock was already acquired")

    @staticmethod
    def _log_command(command, result, dest: str):
        dest = Path(dest)
        if dest.is_dir():
            dest = dest / "command_log"
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "a", encoding="utf-8") as log_file:
            log_file.write(f"Command: {command}\n")
            log_file.write(f"Timestamp: {datetime.now().timestamp()}\n")
            log_file.write(f"{result}\n")
