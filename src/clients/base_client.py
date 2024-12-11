# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
from abc import ABC, abstractmethod
from typing import Optional


class BaseClientException(Exception):
    pass


class BaseClient(ABC):
    @property
    @abstractmethod
    def connected(self):
        pass

    @abstractmethod
    def __enter__(self) -> "BaseClient":
        pass

    @abstractmethod
    def __exit__(self, *_):
        pass

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def run_command(
        self, command: str, *, retries: Optional[int] = None, timeout: Optional[float] = None, log_path: str = None
    ) -> str:
        """
        Runs a command on the connected client. Specify log_path to log the command and result to file.

        :param command: The command to run (e.g. ls, pwd, cat etc.).
        :param retries: Optional. Number of retries if the command fails.
        :param timeout: Optional. Timeout in seconds for the command to complete.
        :param log_path: Optional. The file to which you want the command and result logged.

        :return: The command output as a string.
        """

    @abstractmethod
    def pull_file(self, path: str, dest: str) -> None:
        """
        Pulls a file from a specified path on the target system to a destination on the local system.

        :param path: The file path on the target system from where the file needs to be pulled.
        :param dest: The local destination directory where the file should be stored after being pulled.

        :example:
        >>> client.pull_file('/remote/path/to/file', '/local/folder/')
        """

    @abstractmethod
    def push_file(self, path: str, dest: str) -> None:
        """
        Pushes a file from a specified path on the local system to a destination on the target system.

        :param path: The file path on the local system from where the file needs to be pushed.
        :param dest: The remote destination directory where the file should be stored after being pushed.

        :example:
        >>> client.push_file('/local/path/to/file', '/remote/folder/')
        """

    @abstractmethod
    def add_cleanup(self, path: str, flags: Optional[str]) -> None:
        """
        Adds a path to be cleaned upon context manager exit.

        :param path: The file path to be removed (with glob matching).
        :param flags: Optional. Direct `rm` flags (e.g. '-r' or '-rf').
        """
