# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import re
from contextlib import contextmanager

from remoteperf._parsers.generic import ParsingError
from remoteperf.handlers.base_linux_handler import BaseLinuxHandler, BaseLinuxHandlerException
from remoteperf.handlers.posix_implementation_handler import MissingPosixCapabilityException
from remoteperf.models.base import BootTimeInfo


class AndroidHandlerException(BaseLinuxHandlerException):
    pass


class MissingAndroidCapabilityException(MissingPosixCapabilityException, AndroidHandlerException):
    pass


@contextmanager
def _handle_parsing_error(result):
    try:
        yield
    except ParsingError as e:
        raise AndroidHandlerException(f"Failed to parse data {result}") from e


class AndroidHandler(BaseLinuxHandler):
    """
    Handler for all android-based systems.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, tmp_directory="/data/local/tmp", **kwargs)

    def get_boot_time(self) -> BootTimeInfo:
        """
        Get the system uptime.

        :raises MissingAndroidCapabilityException: If bootstat is unavailable
        """
        binary = "/system/bin/bootstat"
        if not self._has_capability(binary):
            raise MissingAndroidCapabilityException("Cannot measure boot time: bootstat not found on target system")
        command = f"{binary} -p | grep absolute_boot_time"
        output = self._client.run_command(command)
        with _handle_parsing_error(output):
            return self._parse_bootstat(output.strip())

    @staticmethod
    def _parse_bootstat(raw_data: str) -> BootTimeInfo:
        if not (match := re.search(r"\d+", raw_data)):
            raise AndroidHandlerException(f"Could not parse: {raw_data}")
        return BootTimeInfo(total=float(match[0]))
