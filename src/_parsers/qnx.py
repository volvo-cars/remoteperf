# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
from datetime import datetime
from pathlib import PurePosixPath
from typing import Dict, Optional, Tuple

import regex as re

from src._parsers import generic
from src._parsers.generic import ParsingError, ParsingInfo
from src.models.base import Process


def parse_hogs_cpu_usage(
    hogs_output: str, timestamp: Optional[datetime] = None
) -> dict:
    """
    Parses CPU usage data from the output of the 'hogs' command and returns a summary of the CPU load and per-core load.

    :param hogs_output: A string containing CPU load data in the format:
                         'PID NAME MSEC PIDS SYS MEMORY' followed by `pidin` output detailing process information.

                         Example:
                         PID           NAME  MSEC PIDS  SYS        MEMORY
                           0         [idle]   750   0%   75%      0k   0%
                           1         [idle]   750   0%   75%      0k   0%

    :param timestamp: Optional. A `datetime` object representing the current timestamp.
                      If not provided, the current time is used.

    :return: A dictionary containing:
             - "load": The total CPU load percentage.
             - "cores": A dictionary where each key is a core identifier (as a string) and the value is the core's load
               percentage (calculated as 100 minus the idle load percentage).
             - "timestamp": The provided timestamp or the current time if not provided.

             Example output:
             {
                 "load": 25.0,
                 "cores": {
                     "0": 25.0,
                     "1": 25.0,
                 },
                 "timestamp": datetime(2024, 10, 14, 10, 37, 54)
             }

    :raises ParsingError: If the input string cannot be parsed in the expected format.
    """
    col_patterns = [r"(\d+)", r"\[idle\]", r"\d+", r"\d+%", r"(\d+)%"]
    core_pattern = r"\s+".join(col_patterns)
    matches = re.findall(re.compile(core_pattern), hogs_output)
    if not matches:
        raise ParsingError("Could not extract any cpu data")
    total_load = round(100 - sum(float(load) for _, load in matches) / len(matches), 2)

    result = {
        "load": total_load,
        "cores": {core: round(100 - float(load)) for core, load in matches},
        "timestamp": timestamp or datetime.now(),
    }
    return result


def parse_hogs_pidin_proc_wise(
    raw_cpu_data: str, timestamp: Optional[datetime] = None
) -> Dict[Process, dict]:
    """
    Parses CPU usage data and process information from a concatenated string of 'hogs' and `pidin` outputs.

    :param raw_cpu_data: A string containing CPU load data in the format:
                         'PID NAME MSEC PIDS SYS MEMORY' followed by `pidin` output detailing process information.

                         Example:
                         PID           NAME  MSEC PIDS  SYS        MEMORY
                           2    /bin/python   100   0%   10%  12345k   0%
                           1           init   400   0%   40%     N/A  N/A
                           0         [idle]   750   0%   75%      0k   0%
                           1         [idle]   750   0%   75%      0k   0%
                         pid  start time  name Arguments
                           1 Oct 14 08:30 sbin/init /sbin/init -vvv
                           2 Oct 14 08:30 bin/python  python -m remoteperf

    :param timestamp: Optional. A `datetime` object representing the current timestamp.
                      If not provided, `None` is used in the output.

    :return: A dictionary where each key is a `Process` object (containing PID, name, command, and start time),
             and the corresponding value is a dictionary with:
             - "cpu_load": The CPU load percentage for the process.
             - "timestamp": The provided timestamp or `None` if not provided.

             Example output:
             {
                Process(pid=1, name="/sbin/init", command="/sbin/init -vvv", start_time="Oct 14 08:30"): {
                    "cpu_load": 20,
                    "timestamp": datetime(2024, 10, 14, 10, 37, 54)
                },
                Process(pid=2, name="python", command="python -m remoteperf", start_time="Oct 14 08:30"): {
                    "cpu_load": 5,
                    "timestamp": datetime(2024, 10, 14, 10, 37, 54)
                }
             }

    :raises ParsingError: If the input string cannot be parsed in the expected format.
    """
    timestamp = timestamp or datetime.now()
    parsed_hogs_data = parse_hogs(raw_cpu_data, ("SYS", "PID", "NAME"))
    parsed_pidin_data = parse_pidin(
        raw_cpu_data, ("pid", "name", "Arguments", "start_time")
    )

    result = {}

    for pid, process in parsed_pidin_data.items():
        hogs_process = parsed_hogs_data.get(pid)
        if hogs_process and (
            hogs_process["NAME"] in process["name"]
            or hogs_process["NAME"] in process["Arguments"]
        ):
            p = Process(
                pid=process["pid"],
                name=process["name"],
                command=process["Arguments"],
                start_time=process["start_time"],
            )

            cpu_pattern = r" \[idle\] "
            fuzzy_pattern = rf"({cpu_pattern}){{e<=1}}"
            n_cpus = len(re.findall(fuzzy_pattern, raw_cpu_data))
            load = hogs_process["SYS"] / n_cpus
            result[p] = {"cpu_load": load, "timestamp": timestamp}

    return result


def parse_mem_usage_from_proc_files(
    raw_process_memory_usage: str, timestamp: Optional[datetime] = None
) -> Dict[Process, dict]:
    """
    Parses memory usage data and process information from a concatenated
    string of process memory details and `pidin` output.

    :param raw_process_memory_usage: A string containing memory usage data in the format:
                                     'rss_pid=<PID> ...\nas_stats.rss=<hex_value> (<memory_in_MB>MB)' followed by
                                     `pidin` output detailing process information.

                                     Example:
                                     rss_pid=12345 ...
                                     as_stats.rss=0xabc (12.3MB)
                                     rss_pid=12346 ...
                                     as_stats.rss=0xabc (1.234MB)
                                     pid  start time  name Arguments
                                       1 Oct 14 08:30 sbin/init /sbin/init -vvv
                                       2 Oct 14 08:30 bin/python  python -m remoteperf

    :param timestamp: Optional. A `datetime` object representing the current timestamp.
                      If not provided, `None` is used in the output.

    :return: A dictionary where each key is a `Process` object (containing PID, name, command, and start time),
             and the corresponding value is a dictionary with:
             - "mem_usage": The memory usage in kilobytes for the process.
             - "timestamp": The provided timestamp or `None` if not provided.

             Example output:
             {
                Process(pid=1, name="/sbin/init", command="/sbin/init -vvv", start_time="Oct 14 08:30"):{
                    "mem_usage": 12595,
                    "timestamp": datetime(2024, 10, 14, 10, 37, 54)
                },
                Process(pid=2, name="python", command="python -m remoteperf", start_time="Oct 14 08:30"):{
                    "mem_usage": 1263,
                    "timestamp": datetime(2024, 10, 14, 10, 37, 54)
                }
             }

    :raises ParsingError: If the input string cannot be parsed in the expected format.
    """
    timestamp = timestamp or datetime.now()

    parsed_pidin = parse_pidin(
        raw_process_memory_usage, required=("pid", "name", "Arguments", "start_time")
    )
    parsed_procfiles = parse_memory_per_pid(raw_process_memory_usage)
    result = {}
    for pid, process in parsed_pidin.items():
        if pid in parsed_procfiles:
            result[
                Process(
                    pid=process["pid"],
                    name=process["name"],
                    command=process["Arguments"],
                    start_time=process["start_time"],
                )
            ] = {
                "mem_usage": parsed_procfiles.get(pid),
                "timestamp": timestamp,
            }

    return result


def parse_memory_per_pid(raw_data: str) -> dict:
    """
    Parses memory usage data for multiple processes from a string and returns a dictionary mapping process IDs (PIDs)
    to their memory usage in kilobytes.

    :param raw_data: A string containing memory usage data in the format:
                     'rss_pid=<PID> ...\nas_stats.rss=<hex_value> (<memory_in_MB>MB)' repeated for each process.
                     Example:
                     rss_pid=12345 ...
                     as_stats.rss=0xabc (12.3MB)
                     rss_pid=12346 ...
                     as_stats.rss=0xabc (1.234MB)

    :return: A dictionary where each key is a PID (as an integer), and the corresponding value is the memory usage
             in kilobytes (as an integer).

             Example output:
             {
                12345: 12595,  # Memory usage in KB
                12346: 1263
             }

    :raises ParsingError: If the input string cannot be parsed in the expected format.
    """
    pattern = re.compile(
        r"pid=(\d+):.*?\n.*?as_stats\.rss=0x([0-9a-f]+).*?\(([\d.]+)(GB|MB|kB|B|b)?\)",
        re.IGNORECASE,
    )
    pid_memory = {}

    for match in pattern.finditer(raw_data):
        pid = int(match.group(1))
        memory_value = float(match.group(3))
        unit = match.group(4).lower() if isinstance(match.group(4), str) else ""

        if unit.lower() == "mb":
            memory_kb = memory_value * 1024
        elif unit.lower() == "gb":
            memory_kb = memory_value * 1024**2
        elif unit.lower() == "kb":
            memory_kb = memory_value
        else:
            memory_kb = memory_value / 1024

        pid_memory[pid] = round(memory_kb)
    if not pid_memory:
        raise ParsingError(f"No matches for pattern: {pattern}")

    return pid_memory


def parse_pidin(raw_pidin_data: str, required: Tuple[str]) -> dict:
    categories = {
        "pid": ParsingInfo(r"(\d+)", int),
        "name": ParsingInfo(r"([\w/.-]+)", lambda s: PurePosixPath(s).name),
        "sid": ParsingInfo(r"(\d+)", int),
        "start_time": ParsingInfo(
            r"([a-zA-Z]{3}\s+\d+\s+\d{2}:\d{2})",
            str,
        ),
        "utime": ParsingInfo(
            r"([\d.smhd]+)", generic.convert_compact_format_to_seconds
        ),
        "stime": ParsingInfo(
            r"([\d.smhd]+)", generic.convert_compact_format_to_seconds
        ),
        "cutime": ParsingInfo(
            r"([\d.smhd]+)", generic.convert_compact_format_to_seconds
        ),
        "cstime": ParsingInfo(
            r"([\d.smhd]+)", generic.convert_compact_format_to_seconds
        ),
        "Arguments": ParsingInfo(r"(.*)", lambda x: x),
    }
    return generic.parse_table(raw_pidin_data, categories, required=required)


def parse_hogs(raw_pidin_data: str, required: Tuple[str]) -> dict:
    categories = {
        "PID": ParsingInfo(r"(\d+)", int),
        "NAME": ParsingInfo(r"([\w/.-]+)", lambda s: PurePosixPath(s).name),
        "MSEC": ParsingInfo(r"(\d+)", int),
        "PIDS": ParsingInfo(r"(\d*\.?\d+)%", float),
        "SYS": ParsingInfo(r"(\d*\.?\d+)%", float),
        "MEMORY": ParsingInfo(r"(\d+k|N/A)[^%]\s+", generic.convert_to_int),
    }
    return generic.parse_table(raw_pidin_data, categories, required=required)


def parse_proc_vm_stat(
    raw_memory_usage: str, timestamp: Optional[datetime] = None
) -> dict:
    """
        Parses memory usage statistics from a string and calculates total, used, and free memory.

    :param raw_memory_usage: A string containing memory usage data in the format:
                             ```
                             getpage_count=12345
                             putpage_count=123
                             page_count=0xabcdef (1.0GB)
                             pages_free=0xabcdef (123.4MB)
                             ```

        :param timestamp: Optional. A `datetime` object representing the current timestamp.
                          If not provided, the timestamp is not included.

        :return: A dictionary containing:
                 - "mem": A dictionary with memory statistics:
                   - "total": Total memory in kilobytes.
                   - "used": Used memory in kilobytes.
                   - "free": Free memory in kilobytes.
                 - "timestamp": The provided timestamp or `None` if not provided.

                 Example output:
                 {
                    "mem": {"total": 1000, "used": 400, "free": 600},
                    "timestamp": datetime(2024, 10, 14, 10, 37, 54)
                 }
    """
    timestamp = timestamp or datetime.now()
    pattern = r"page_count=\S+\s+\(([0-9.]+)([GMKk]B)\).*\n.*pages_free=\S+\s+\(([0-9.]+)([GMKk]B)\)"
    match = re.search(pattern, raw_memory_usage)
    if match:
        conversion = {"GB": 1024**2, "MB": 1024, "KB": 1, "kB": 1}
        total_kb = float(match.group(1)) * conversion.get(match.group(2))
        free_kb = float(match.group(3)) * conversion.get(match.group(4))
        used_kb = total_kb - free_kb

        return {
            "mem": {"total": int(total_kb), "used": int(used_kb), "free": int(free_kb)},
            "timestamp": timestamp,
        }

    raise ParsingError(f"Unable to parse memory, no match found for pattern: {pattern}")


def parse_bmetrics_boot_time(raw_output: str) -> dict:
    """
    Parses a boot time string in the format 'XsYns' or 'Yns', where X is seconds and Y is nanoseconds,
    to calculate the total boot time.

    :param raw_output: A string containing the boot time in the format 'XsYns' (e.g., '1s46224384ns') or
                       'Yns' (e.g., '46224384ns').
                       Example: "1s46224384ns" or "46224384ns"

    :return: A dictionary containing:
             - "total": The total boot time in seconds as a float.

             Example output:
             {"total": 1.046224384}

    :raises ParsingError: If the input string cannot be parsed as boot time in the expected format.
    """
    pattern = r"(\b\d+s)?(\d+ns\b)"
    match = re.search(pattern, raw_output)
    if match:
        if match.group(1):
            seconds = int(match.group(1).replace("s", ""))
        else:
            seconds = 0
        ns = int(match.group(2).replace("ns", ""))
        boot_time = seconds + (ns / (10**9))
    else:
        raise ParsingError(
            f"Unable to extract boot time: no match found for pattern: {pattern}"
        )
    return {"total": boot_time}  # type: ignore[call-arg]


def parse_uptime(
    boot_data: str, date_data: str, timestamp: Optional[datetime] = None
) -> dict:
    """
    Parses boot and date information to calculate system uptime.

    :param boot_data: A string containing the boot time in the format "BootTime:Oct 14 05:27:25 GMT 2024".
                      Example: "... BootTime:Oct 14 05:27:25 GMT 2024 ..."
    :param date_data: A string containing the current time in the format "Mon Oct 14 10:37:54 GMT 2024".
                      Example: "Mon Oct 14 10:37:54 GMT 2024"
    :param timestamp: Optional. A `datetime` object representing the current timestamp. If not provided, the current
                      time is parsed from `date_data`.
                      Example: datetime(2024, 10, 14, 10, 37, 54)

    :raises ParsingError: If provided data does not adhere to qnx datetime format

    :return: A dictionary containing:
             - "total": The system uptime in seconds as a float.
             - "timestamp": The timestamp used for the calculation (either provided or parsed from `date_data`).

             Example output:
             {"total": 18629.0, "timestamp": datetime(2024, 10, 14, 10, 37, 54)}
    """
    timestamp = timestamp or datetime.now()
    boot_time_pattern = r"BootTime:(.*?) GMT (\d{4})"
    boot_time_match = re.search(boot_time_pattern, boot_data)
    if boot_time_match:
        try:
            boot_time_str = boot_time_match.group(1) + " " + boot_time_match.group(2)
            boot_time = datetime.strptime(boot_time_str, "%b %d %H:%M:%S %Y")
            current_time = datetime.strptime(
                date_data.strip(), "%a %b %d %H:%M:%S %Z %Y"
            )
            uptime = current_time - boot_time
        except ValueError as e:
            raise ParsingError("Failed to parse datetime data from data") from e
    else:
        raise ParsingError("Error during extracting data")

    return {"total": uptime.total_seconds(), "timestamp": timestamp}
