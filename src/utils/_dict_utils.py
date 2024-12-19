from datetime import datetime


def dict_diff(sample1, sample2) -> dict:
    diff = {}
    for key in sample1.keys() & sample2.keys():
        if isinstance(sample1[key], dict) and isinstance(sample2[key], dict):
            diff[key] = dict_diff(sample1[key], sample2[key])
        elif isinstance(sample1[key], datetime) and isinstance(sample2[key], datetime):
            diff[key] = (sample2[key] - sample1[key]).total_seconds()
        elif isinstance(sample1[key], (int, float)) and isinstance(sample2[key], (int, float)):
            diff[key] = sample2[key] - sample1[key]
        else:
            raise ValueError(f"Unsupported type {type(sample1[key])}")
    if diff:
        return diff
    raise ValueError("No common keys found")
