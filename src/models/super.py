# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
from collections import namedtuple
from typing import List, TypeVar

import attr

from src.models.base import (
    ArithmeticBaseInfoModel,
    BaseCpuSample,
    BaseCpuUsageInfo,
    BaseMemorySample,
    BaseProcess,
    ModelList,
    SystemMemory,
)
from src.models.linux import LinuxResourceSample
from src.utils.attrs_util import attrs_init_replacement

# Superstructure models that can't reside in base due to circular imports

ArithmeticModelT = TypeVar("ArithmeticModelT", bound=ArithmeticBaseInfoModel)


class ArithmeticModelList(ModelList[ArithmeticModelT]):
    @property
    def avg(self) -> ArithmeticModelT:
        return self._sum / len(self)

    @property
    def _sum(self):
        # Only makes sense internally for calculations, do not expose
        return sum(self[1:], self[0])


class CpuList(ArithmeticModelList[BaseCpuUsageInfo]):
    def highest_load_single_core(self, n: int = 5) -> "CpuList":
        """
        Returns the n models with the highest recorded single-core CPU load.

        Returns:
            BaseCpuUsageInfo
        """
        return self.__class__(sorted(self, key=lambda m: max(m.cores.values()), reverse=True)[:n])


class MemoryList(ArithmeticModelList[SystemMemory]):
    def highest_memory_used(self, n: int = 5):
        """
        Returns the n models with the highest memory usage.

        Returns:
            MemoryList
        """
        return self.__class__(sorted(self, key=lambda m: m.mem.used, reverse=True)[:n])


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class ProcessInfo(BaseProcess):
    samples: List[ArithmeticModelList]

    @property
    def avg(self):
        return self._sum / len(self.samples)

    @property
    def _sum(self):
        # Only makes sense internally for calculations, do not expose
        return sum(self.samples[1:], self.samples[0])


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class CpuSampleProcessInfo(ProcessInfo):
    samples: List[BaseCpuSample]

    @property
    def max_cpu_load(self) -> BaseCpuSample:
        """
        Returns the sample with the highest recorded CPU load.

        Returns:
            BaseCpuSample
        """
        Item = namedtuple("Item", "load model")
        top = Item(-1, None)
        for model in self.samples:
            if model.cpu_load > top.load:
                top = Item(model.cpu_load, model)
        return top.model


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class MemorySampleProcessInfo(ProcessInfo):
    samples: List[BaseMemorySample]

    @property
    def max_mem_usage(self) -> BaseMemorySample:
        """
        Returns the sample with the highest recorded memory usage.

        Returns:
            BaseMemorySample
        """
        Item = namedtuple("Item", "usage model")
        top = Item(-1, None)
        for model in self.samples:
            if model.mem_usage > top.usage:
                top = Item(model.mem_usage, model)
        return top.model


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class ResourceSampleProcessInfo(CpuSampleProcessInfo, MemorySampleProcessInfo):
    samples: List[LinuxResourceSample]


# I know, this is insane, I just can't figure out the typing for this one
class _ProcessCpuList:
    def highest_average_cpu_load(self, n: int = 5):
        """
        Returns the top `n` processes with the highest average CPU load.

        Args:
            n (int, optional): The number of processes to return. Defaults to 5.

        Returns:
            ProcessCpuList: A new instance of ProcessCpuList containing the top `n` processes.
        """
        return self.__class__(sorted(self, key=lambda m: m.avg.cpu_load, reverse=True)[:n])

    def highest_peak_cpu_load(self, n: int = 5):
        """
        Returns the top `n` processes with the highest peak CPU load.

        Args:
            n (int, optional): The number of processes to return. Defaults to 5.

        Returns:
            ProcessCpuList: A new instance of ProcessCpuList containing the top `n` processes.
        """
        return self.__class__(sorted(self, key=lambda m: m.max_cpu_load.cpu_load, reverse=True)[:n])


class _ProcessMemoryList:
    def highest_average_mem_usage(self, n: int = 5):
        """
        Returns the top `n` processes with the highest average memory usage.

        Args:
            n (int, optional): The number of processes to return. Defaults to 5.

        Returns:
            ProcessMemoryList: A new instance of ProcessMemoryList containing the top `n` processes.
        """
        return self.__class__(sorted(self, key=lambda m: m.avg.mem_usage, reverse=True)[:n])

    def highest_peak_mem_usage(self, n: int = 5):
        """
        Returns the top `n` processes with the highest peak memory usage.

        Args:
            n (int, optional): The number of processes to return. Defaults to 5.

        Returns:
            ProcessMemoryList: A new instance of ProcessMemoryList containing the top `n` processes.
        """
        return self.__class__(sorted(self, key=lambda m: m.max_mem_usage.mem_usage, reverse=True)[:n])


class ProcessCpuList(ModelList[CpuSampleProcessInfo], _ProcessCpuList):
    pass


class ProcessMemoryList(ModelList[MemorySampleProcessInfo], _ProcessMemoryList):
    pass


class ProcessResourceList(ModelList[ResourceSampleProcessInfo], _ProcessCpuList, _ProcessMemoryList):
    pass
