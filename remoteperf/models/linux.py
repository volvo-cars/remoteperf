# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
from datetime import datetime
from typing import Dict

import attr

from remoteperf.models.base import (
    BaseCpuSample,
    BaseCpuUsageInfo,
    BaseRemoteperfModel,
    BootTimeInfo,
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
