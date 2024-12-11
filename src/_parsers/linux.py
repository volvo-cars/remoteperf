# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from attrs import fields

from src._parsers.generic import ParsingError
from src.models.base import Process
from src.models.linux import LinuxCpuModeUsageInfo
from src.utils.math import Vector


def parse_proc_stat(raw_cpu_usage_1: str, raw_cpu_usage_2: str, timestamp: Optional[datetime] = None) -> dict:
    timestamp = timestamp or datetime.now()

    pattern = re.compile(r"(cpu\d*)\s+" + r"\s+".join([r"(\d+)"] * 10))

    cpu_dict_1 = {
        matches.groups()[0]: Vector(matches.groups()[1:])
        for line in raw_cpu_usage_1.splitlines()
        if (matches := re.search(pattern, line)) and None not in matches.groups()
    }
    cpu_dict_2 = {
        matches.groups()[0]: Vector(matches.groups()[1:])
        for line in raw_cpu_usage_2.splitlines()
        if (matches := re.search(pattern, line)) and None not in matches.groups()
    }
    if not set(cpu_dict_1) == set(cpu_dict_2):
        raise ParsingError(f"Got incompatible cpu data: {raw_cpu_usage_1}\n{raw_cpu_usage_2}")

    mode_usages = {}
    # /proc/stat order
    labels = [f.name for f in fields(LinuxCpuModeUsageInfo)]
    for cpu in cpu_dict_1:
        diffs = cpu_dict_2.get(cpu) - cpu_dict_1.get(cpu)
        percentages = diffs / sum(diffs) * 100 if sum(diffs) > 0 else diffs
        mode_usages[cpu] = LinuxCpuModeUsageInfo(**dict(zip(labels, percentages)))
    if "cpu" not in mode_usages:
        raise ParsingError(f"Raw data incomplete, missing 'cpu' line: {raw_cpu_usage_1}\n{raw_cpu_usage_2}")
    total = mode_usages.pop("cpu")

    cpu_load = {
        "load": 100 - total.idle,
        "mode_usage": total,
        "cores": {k.replace("cpu", ""): 100 - v.idle for k, v in mode_usages.items()},
        "timestamp": timestamp,
    }

    return cpu_load


def parse_proc_meminfo(raw_memory_usage: str, timestamp: Optional[datetime] = None) -> dict:
    """Parse output from '/proc/meminfo'"""
    timestamp = timestamp or datetime.now()
    mem_dict = {}
    for line in raw_memory_usage.strip().split("\n"):
        if len(line.split()) > 1:
            key, value, *_ = line.split()
            mem_dict[key.strip(":")] = int(value)

    try:
        buff_cache = mem_dict["Cached"] + mem_dict["SReclaimable"] + mem_dict["Buffers"]

        system_memory: Dict[str, Any] = {
            "mem": {
                "total": mem_dict["MemTotal"],
                # Used differs from 'free' if used in docker. This will report the correct host kernel info
                "used": mem_dict["MemTotal"] - mem_dict["MemFree"] - buff_cache,
                "free": mem_dict["MemFree"],
                "shared": mem_dict["Shmem"],
                "buff_cache": buff_cache,
                "available": mem_dict["MemAvailable"],
            },
            "swap": {
                "total": mem_dict["SwapTotal"],
                "free": mem_dict["SwapFree"],
                "used": mem_dict["SwapTotal"] - mem_dict["SwapFree"],
            },
            "timestamp": timestamp,
        }
    except KeyError as e:
        raise ParsingError(f'The raw data did not have the expected fields: "{raw_memory_usage}"') from e

    return system_memory


def _parse_delimiter_and_page_size(raw_data: str, separator_pattern: str) -> Tuple[str, str]:
    header = raw_data.split("\n", 10)[:10]
    page_size = next((line for line in header if line.isnumeric()), None)
    delimiter = next((line for line in header if separator_pattern in line), None)
    if page_size is None or delimiter is None:
        raise ParsingError(
            f"Could not parse page size or separator from header: "
            f"{header}\n page_size: {page_size}, delimiter: {delimiter}"
            f"Raw data: {raw_data}"
        )
    return delimiter, page_size


# pylint: disable=R0914(too-many-locals)
def parse_cpu_usage_from_proc_files(
    raw_cpu_usage_1: str, raw_cpu_usage_2: str, separator_pattern: str, timestamp: datetime = None
) -> Dict[Process, dict]:
    timestamp = timestamp or datetime.now()
    delimiter, page_size = _parse_delimiter_and_page_size(raw_cpu_usage_1, separator_pattern)
    raw_cpu_list_1 = raw_cpu_usage_1.split(f"{delimiter}")[1:]
    raw_cpu_list_2 = raw_cpu_usage_2.split(f"{delimiter}")[1:]
    if not raw_cpu_list_1 or not raw_cpu_list_2:
        raise ParsingError(
            f"No process data after available in list(s) (delimiter: {delimiter}): {raw_cpu_usage_1}\n{raw_cpu_usage_2}"
        )
    proc_times_1 = parse_times_from_proc_files(raw_cpu_list_1, page_size)
    proc_times_2 = parse_times_from_proc_files(raw_cpu_list_2, page_size)

    cpu_pattern = re.compile(r"cpu\s+" + r"\s+".join([r"(\d+)"] * 10))
    cpu_ticks_1 = match.groups() if (match := re.search(cpu_pattern, raw_cpu_list_1[-1])) is not None else None
    cpu_ticks_2 = match.groups() if (match := re.search(cpu_pattern, raw_cpu_list_2[-1])) is not None else None

    if not cpu_ticks_1 or not cpu_ticks_2:
        raise ParsingError(f"Could not find cpu information in statfile {raw_cpu_list_1[-1:]}\n{raw_cpu_list_2[-1:]}")
    try:
        tick_1 = sum(map(int, cpu_ticks_1))
        tick_2 = sum(map(int, cpu_ticks_2))
    except (ValueError, TypeError) as e:
        raise ParsingError(f"Cpu tick data incomplete: {cpu_ticks_1}\n{cpu_ticks_2}") from e
    tick_delta = tick_2 - tick_1

    result = {
        process: {
            "cpu_load": (cpu_load - proc_times_1.get(process, (0,))[0]) / tick_delta * 100,
            "mem_usage": mem_usage // 1024,
            "timestamp": timestamp,
        }
        for process, (cpu_load, mem_usage) in proc_times_2.items()
        if process in proc_times_1
    }
    return result


# Exists to avoid having to take two measurements, as opposed to the cpu parser
def parse_mem_usage_from_proc_files(
    raw_process_memory_usage: str, separator_pattern: str, timestamp: Optional[datetime] = None
) -> Dict[Process, dict]:
    timestamp = timestamp or datetime.now()
    delimiter, page_size = _parse_delimiter_and_page_size(raw_process_memory_usage, separator_pattern)
    raw_stat_list = raw_process_memory_usage.split(f"{delimiter}")[1:]
    if not raw_stat_list:
        raise ParsingError(f"Could not separate processes (delimiter:{delimiter}): {raw_process_memory_usage}")
    proc_times = parse_times_from_proc_files(raw_stat_list, page_size)
    result = {
        process: {
            "mem_usage": mem_usage // 1024,
            "timestamp": timestamp,
        }
        for process, (_, mem_usage) in proc_times.items()
    }
    return result


def parse_times_from_proc_files(proc_metrics, page_size) -> Dict[Process, int]:
    proc_times = {}
    regex_components = [r"(?P<pid>\d+)", r"\((?P<name>\S+)\)", r"\S", *([r"(-?\d+)"] * 49)]
    proc_regex = r"\s+".join(regex_components) + r"\n(?P<cmdline>.*)"
    for proc in proc_metrics:
        if match := re.search(proc_regex, proc):
            proc = Process(
                pid=int(match.group("pid")),
                name=match.group("name"),
                start_time=match.group(21),
                command=match.group("cmdline") or match.group("name"),
            )
            proc_times[proc] = (int(match.group(13)) + int(match.group(14)), int(page_size) * int(match.group(23)))
    return proc_times


def parse_systemd_analyze(analyze_string: str) -> dict:
    """Parse the systemd-analyze output into a dictionary with all times in seconds."""

    pattern = r"(\d+min)?\s?(\d+\.\d+)s\s\((.*?)\)"
    matches = re.findall(pattern, analyze_string)

    results: Dict[str, Any] = {"extra": {}}
    for match in matches:
        mins, secs, phase = match
        total_seconds = float(secs)
        if mins:
            # Convert '1min' to 60 seconds, for example
            total_seconds += float(mins[:-3]) * 60

        results["extra"][phase] = total_seconds

    # Also extract the total and target reached time
    total_time = re.search(r"=\s(\d+min)?\s?(\d+\.\d+)s", analyze_string)
    if total_time:
        mins, secs = total_time.groups()
        total_secs = float(secs)
        if mins:
            total_secs += float(mins[:-3]) * 60
        results["total"] = total_secs
    else:
        raise ParsingError(f"Unable to parse total time from systemd-analyze: {analyze_string}")

    target_time = re.search(r"after\s(\d+\.\d+)s", analyze_string)
    if target_time:
        results["extra"]["graphical.target"] = float(target_time.group(1))

    return results
