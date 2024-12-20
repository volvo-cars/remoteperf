# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import re
from dataclasses import dataclass
from typing import Dict, Optional


class ParsingError(Exception):
    pass


@dataclass
class ParsingInfo:
    regex: str
    parse: callable
    key: Optional[int] = (
        None  # The index of the parsed value that should be used as the key in the resulting dictionary.
    )
    # It can still be used to define multiple keys, that will then return them as a concatenated string.
    # But this at the moment breaks to many uses down the line. To Do for maybe later.
    rename: Optional[str] = None


def parse_table(raw_table_data: str, categories: Dict[str, ParsingInfo], required=tuple(), header: bool = True) -> dict:
    if header:
        _, lines, regex_parsers = get_table_header(raw_table_data, categories)
    else:
        lines = raw_table_data.split("\n")
        regex_parsers = {}
        for category in categories:
            regex_parsers[categories[category].rename if categories[category].rename else category] = categories[
                category
            ]

    result = parse_table_lines(lines, regex_parsers)

    if not result:
        raise ParsingError(f"Failed to parse table: {raw_table_data}")
    sample = list(result.values())[0]
    if not all(req in sample for req in required):
        raise ParsingError(f"Failed to parse all required categories ({required}) from table: {raw_table_data}")
    return result


def get_table_header(raw_table_data: str, categories: Dict[str, ParsingInfo]) -> str:
    replacements = {c: categories[c].rename for c in categories if categories[c].rename}
    try:
        header, *lines = raw_table_data.split("\n")
        for orig, repl in replacements.items():
            header = header.replace(orig, repl)
            categories[repl] = categories.pop(orig)

        while any(h not in categories for h in header.split()) and lines:
            header, *lines = lines
            for orig, repl in replacements.items():
                header = header.replace(orig, repl)

        regex_parsers = {}
        for category in header.split():
            if category not in categories:
                raise ParsingError(f"Error, unknown parse header: {category} in input: {raw_table_data}")
            regex_parsers[categories[category].rename if categories[category].rename else category] = categories[
                category
            ]
    except Exception as e:
        raise ParsingError(f"Failed to parse categories ({categories})") from e

    return header, lines, regex_parsers


def parse_table_lines(lines: str, regex_parsers: Dict[str, ParsingInfo]) -> dict:
    regex = re.compile(r"\s+".join([parsing_info.regex for parsing_info in regex_parsers.values()]))
    result = {}
    for line in lines:
        if match := re.search(regex, line):
            parsed_key = {
                parsing_info.key: parsing_info.parse(value)
                for (_, parsing_info), value in zip(regex_parsers.items(), match.groups())
                if parsing_info.key
            }
            if not parsed_key:
                raise ValueError(f"Failed to specify a key for the parsed data: {regex_parsers}")

            # Other part of using multiple column as keys. See aboves ToDo.
            # result[".".join(str(i) for _, i in sorted(parsed_key.items()))] = {
            result[parsed_key[1]] = {
                category: parsing_info.parse(value)
                for (category, parsing_info), value in zip(regex_parsers.items(), match.groups())
            }

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
