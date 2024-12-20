# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
from datetime import datetime
from typing import Dict

import attr

from remoteperf.models.base import (
    ArithmeticBaseInfoModel,
    BaseCpuSample,
    BaseCpuUsageInfo,
    BaseRemoteperfModel,
    BootTimeInfo,
    ModelList,
)
from remoteperf.utils.attrs_util import attrs_init_replacement


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class LinuxCpuModeUsageInfo(BaseRemoteperfModel):
    user: float
    nice: float
    system: float
    idle: float
    iowait: float
    irq: float
    softirq: float
    steal: float
    guest: float
    guest_nice: float


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class LinuxCpuUsageInfo(BaseCpuUsageInfo):
    mode_usage: LinuxCpuModeUsageInfo


# Multiple inheritance does not work with slotted classes
@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True, slots=True)
class LinuxResourceSample(BaseCpuSample):
    mem_usage: float
    timestamp: datetime = attr.field(factory=datetime.now)


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class LinuxBootTimeInfo(BootTimeInfo):
    extra: Dict[str, float]


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class LinuxPressureModel(ArithmeticBaseInfoModel):
    total: int
    avg10: float
    avg60: float
    avg300: float


class LinuxPressureModelList(ModelList[LinuxPressureModel]):
    def highest_pressure(self, n: int = 5) -> "LinuxPressureModelList":
        return LinuxPressureModelList(sorted(self, key=lambda m: m.avg10, reverse=True)[:n])


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class PressureMetricInfo(BaseRemoteperfModel):
    some: LinuxPressureModel
    full: LinuxPressureModel


class LinuxPressureMetricInfoList(ModelList[PressureMetricInfo]):
    @property
    def some(self) -> LinuxPressureModelList:
        return LinuxPressureModelList((model.some for model in self))

    @property
    def full(self) -> LinuxPressureModelList:
        return LinuxPressureModelList((model.full for model in self))


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class LinuxPressureInfo(BaseRemoteperfModel):
    cpu: PressureMetricInfo
    io: PressureMetricInfo
    memory: PressureMetricInfo


class LinuxPressureInfoList(ModelList[LinuxPressureInfo]):
    @property
    def cpu(self) -> LinuxPressureMetricInfoList:
        return LinuxPressureMetricInfoList((model.cpu for model in self))

    @property
    def io(self) -> LinuxPressureMetricInfoList:
        return LinuxPressureMetricInfoList((model.io for model in self))

    @property
    def memory(self) -> LinuxPressureMetricInfoList:
        return LinuxPressureMetricInfoList((model.memory for model in self))
