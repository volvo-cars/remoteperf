# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import json
import re
from datetime import datetime
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    Optional,
    Set,
    TypeVar,
    Union,
    get_type_hints,
    overload,
)

import attr
import yaml
from typeguard import TypeCheckError, check_type

from remoteperf.utils.attrs_util import attrs_init_replacement, converter


class BaseRemoteperfModelException(Exception):
    pass


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class BaseRemoteperfModel:
    def __new__(cls, **kwargs):
        expected_types = get_type_hints(cls)
        for key, value in kwargs.items():
            try:
                check_type(value, expected_types.get(key, Any))
            except TypeCheckError:
                return converter.structure(kwargs, cls)

        return super().__new__(cls)

    @property
    def yaml(self):
        return yaml.safe_dump(self.model_dump())

    @property
    def json(self):
        return json.dumps(self.model_dump())

    def model_dump(self: Any, exclude: Union[Set[str], None] = None) -> Dict[str, Any]:
        """
        A function to dump the dataclass self into a dictionary, similar to Pydantic's `model_dump`.

        :param self: The dataclass self to be converted to a dictionary.
        :param exclude: A set of field names to exclude from the dump.
        :return: A dictionary representation of the dataclass.
        """
        exclude = exclude or {}
        return self._recursive_exclude(converter.unstructure(self), exclude=exclude)

    @classmethod
    def _recursive_exclude(cls, data: Any, exclude: Set[str]) -> dict:
        if not exclude:
            return data
        if not isinstance(data, dict):
            return data
        to_remove = []
        for key, value in data.items():
            if key in exclude:
                to_remove.append(key)
            elif isinstance(value, dict):
                data[key] = cls._recursive_exclude(value, exclude)
            elif isinstance(value, list):
                data[key] = [cls._recursive_exclude(v, exclude) for v in value]
        for key in to_remove:
            del data[key]
        return data


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class BaseInfoModel(BaseRemoteperfModel):
    timestamp: datetime = attr.field(factory=datetime.now)


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class ArithmeticBaseModel(BaseRemoteperfModel):
    def __add__(self, other):
        if isinstance(other, self.__class__):
            return self.__class__(
                **self._recursive_op(
                    self.model_dump(exclude="timestamp"),
                    other.model_dump(exclude="timestamp"),
                    lambda a, b: a + b,
                )
            )
        raise TypeError(f"Unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'")

    def __div__(self, denominator):
        if isinstance(denominator, (float, int)):
            return self.__class__(
                **self._recursive_op(
                    self.model_dump(exclude="timestamp"),
                    denominator,
                    lambda a, b: a / b,
                )
            )
        raise TypeError(f"Unsupported operand type(s) for /: 'MemoryInfo' and '{type(denominator).__name__}'")

    @classmethod
    def _recursive_op(cls, dict1, other, operation):
        result = {}
        for key, value in dict1.items():
            operand = other
            if isinstance(other, dict):
                if key in other:
                    operand = other[key]
                else:
                    raise KeyError(f"Key '{key}' not found in both dictionaries.")
            if isinstance(value, dict):
                result[key] = cls._recursive_op(value, operand, operation)
            elif isinstance(value, int) and isinstance(operand, (int, float)):
                result[key] = int(operation(value, operand))
            elif isinstance(value, float) and isinstance(operand, (int, float)):
                result[key] = operation(value, operand)
            elif value is None:
                result[key] = None
            else:
                raise TypeError(f"Unsupported value types for key '{key}': {type(value)} and {type(operand)}")
        return result

    __floordiv__ = __div__
    __truediv__ = __div__


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class ArithmeticBaseInfoModel(ArithmeticBaseModel, BaseInfoModel):
    pass


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class BootTimeInfo(BaseInfoModel):
    total: float


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class SystemUptimeInfo(BaseInfoModel):
    total: float


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class MemoryInfo(BaseRemoteperfModel):
    total: int
    used: int
    free: int


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class ExtendedMemoryInfo(MemoryInfo):
    shared: int
    buff_cache: int
    available: int


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class DiskInfo(BaseInfoModel):
    filesystem: str
    size: int
    used: int
    available: int
    used_percent: int
    mounted_on: str


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class DiskIOInfo(BaseInfoModel):
    device_major_number: int
    device_minor_number: int
    device_name: str
    reads_completed: int
    reads_merged: int
    sectors_reads: int
    time_spent_reading: int
    writes_completed: int
    writes_merged: int
    sectors_written: int
    time_spent_writing: int
    IOs_currently_in_progress: int
    time_spent_doing_io: int
    weighted_time_spent_doing_io: int
    discards_completed: int
    discards_merged: int
    sectors_discarded: int
    time_spent_discarding: int
    time_spent_flushing: int


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class BaseProcess(BaseRemoteperfModel):
    pid: int
    name: str
    command: str
    start_time: str


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True, hash=False)
class Process(BaseProcess):
    def __hash__(self):
        return hash((self.pid, self.name, self.command, self.start_time))


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True, slots=True)
class BaseMemorySample(ArithmeticBaseModel):
    mem_usage: float
    timestamp: datetime = attr.field(factory=datetime.now)


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True, slots=True)
class BaseCpuSample(ArithmeticBaseModel):
    cpu_load: float
    timestamp: datetime = attr.field(factory=datetime.now)


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class BaseCpuUsageInfo(ArithmeticBaseInfoModel):
    load: float
    cores: Dict[str, float]


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class SystemMemory(ArithmeticBaseInfoModel):
    """
    Assumes Kb (Kibibytes, 1024 bytes)
    """

    mem: Union[ExtendedMemoryInfo, MemoryInfo]
    swap: Optional[MemoryInfo] = None


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class DiskIOProcess(BaseRemoteperfModel):
    rchar: int
    wchar: int
    syscr: int
    syscw: int
    read_bytes: int
    write_bytes: int
    cancelled_write_bytes: int


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class DiskIOProcessSample(ArithmeticBaseInfoModel, DiskIOProcess):
    pass


@attr.s(auto_attribs=True, kw_only=True)
class Sample(BaseInfoModel):
    def __new__(cls, *_, **__):
        return super().__new__(cls)

    data: Any


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class Command(BaseRemoteperfModel):
    command: str
    stdout: str
    stderr: str


ModelT = TypeVar("ModelT", bound=BaseRemoteperfModel)
ModelListT = TypeVar("ModelListT", bound="ModelList")


class ModelList(Generic[ModelT]):
    def __init__(self, iterable: Iterable):
        self._list = list(iterable)

    def model_dump(self, *args, **kwargs):
        return [m.model_dump(*args, **kwargs) for m in self._list]

    @property
    def yaml(self):
        return yaml.safe_dump(self.model_dump())

    def filter(self, fun: callable):
        return self.__class__(item for item in self._list if fun(item))

    def _get_by_jsonpath(self, obj: Any, jsonpath: str) -> Any:
        """
        Traverse the object using a JSONPath-like query.
        Supports dot notation for attributes and dict keys,
        and list indexing with numbers.
        """
        parts = re.split(r"\.|\[|\]", jsonpath)
        parts = [part for part in parts if part]  # Remove empty strings from splitting
        for part in parts:
            if part.isdigit():  # Handle list indexing
                obj = obj[int(part)]
            else:
                obj = getattr(obj, part, None)
                if obj is None:
                    obj = obj.get(part, None)
        return obj

    def sort_by_jsonpath(self, jsonpath: str, reverse=False):
        """
        Sort the models by a given JSONPath-like field.
        """
        return self.__class__(
            sorted(
                self._list,
                key=lambda model: self._get_by_jsonpath(model, jsonpath),
                reverse=reverse,
            )
        )

    # Should've chosen a better language
    @overload
    def __getitem__(self, item: int) -> ModelT:
        pass

    @overload
    def __getitem__(self: ModelListT, item: slice) -> ModelListT:
        pass

    def __getitem__(self, index):
        result = self._list[index]
        if isinstance(index, slice):
            return self.__class__(result)
        return result

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._list.__repr__()})"

    def __len__(self):
        return len(self._list)

    def __setitem__(self, index, value):
        self._list[index] = value

    def __delitem__(self, index):
        del self._list[index]

    def __iter__(self):
        return iter(self._list)

    def __contains__(self, item):
        return item in self._list

    def __eq__(self, other):
        return self._list == other._list if isinstance(other, ModelList) else False

    def __mul__(self, value):
        return self.__class__(self._list * value)
