# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
from contextlib import contextmanager

from src._parsers import linux as linux_parsers
from src._parsers.generic import ParsingError
from src.handlers.base_linux_handler import BaseLinuxHandler, BaseLinuxHandlerException
from src.handlers.posix_implementation_handler import MissingPosixCapabilityException
from src.models.linux import LinuxBootTimeInfo


class LinuxHandlerException(BaseLinuxHandlerException):
    pass


class MissingLinuxCapabilityException(MissingPosixCapabilityException, LinuxHandlerException):
    pass


@contextmanager
def _handle_parsing_error(result):
    try:
        yield
    except ParsingError as e:
        raise LinuxHandlerException(f"Failed to parse data {result}") from e


class LinuxHandler(BaseLinuxHandler):
    """
    Handler for all linux-based machines.
    """

    def get_boot_time(self) -> LinuxBootTimeInfo:
        """
        Get the system uptime.

        :raises MissingLinuxCapabilityException: If systemd-analyze is unavailable
        """
        command = "systemd-analyze"
        if not self._has_capability(command):
            raise MissingLinuxCapabilityException("Cannot measure boot time: systemd-analyze unavailable")
        output = self._client.run_command(command)
        with _handle_parsing_error(output):
            return LinuxBootTimeInfo(**linux_parsers.parse_systemd_analyze(output.strip()))
