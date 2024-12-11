# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import re
from dataclasses import dataclass
from typing import Dict


class ParsingError(Exception):
    pass


@dataclass
class ParsingInfo:
    regex: str
    parse: callable


def parse_table(raw_table_data: str, categories: Dict[str, ParsingInfo], required=tuple()) -> dict:
    try:
        header, *lines = raw_table_data.split("\n")
        while not header.strip() or lines and any(h not in categories for h in header.split()):
            header, *lines = lines
            header = header.replace("start time", "start_time")
        regex_parsers = {}
        for category in header.split():
            if category not in categories:
                raise ParsingError(f"Error, unknonw parse header: {category} in input: {raw_table_data}")
            regex_parsers[category] = categories[category]
        regex = re.compile(r"\s+".join([parsing_info.regex for parsing_info in regex_parsers.values()]))
    except Exception as e:
        raise ParsingError(f"Failed to parse categories ({categories})") from e

    result = {}
    for line in lines:
        if match := re.search(regex, line):
            pid = int(match.group(1))
            result[pid] = {
                category: parsing_info.parse(value)
                for (category, parsing_info), value in zip(regex_parsers.items(), match.groups())
            }
    if not result:
        raise ParsingError(f"Failed to parse table: {raw_table_data}")
    sample = list(result.values())[0]
    if not all(req in sample for req in required):
        raise ParsingError(f"Failed to parse all required categories ({required}) from table: {raw_table_data}")
    return result


def convert_compact_format_to_seconds(time_str: str) -> float:
    """
    Converts a time string into seconds.

    Args:
        time_str (str): A string representing time in the format 'D-HH:MM:SS.SSS'.

    Returns:
        float: The total number of seconds represented by the input time string.

    """
    regex_pattern = r"(\d*\.?\d+)([d|h|m|s])?"

    total_seconds: float = 0
    for match in re.finditer(regex_pattern, time_str):
        value, unit = match.groups()
        if unit:
            multiplier = {"d": 86400, "h": 3600, "m": 60, "s": 1}[unit]
            total_seconds += float(value) * multiplier
        else:
            total_seconds += float(value)

    return total_seconds


def convert_to_int(value):
    try:
        if isinstance(value, str):
            value = "".join([d for d in "value" if d.isnumeric()])
        return int(value)
    except ValueError:
        return 0
