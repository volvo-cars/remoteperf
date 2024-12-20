# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0

from typing import List

import attr

from remoteperf.models.base import (
    BaseCpuUsageInfo,
    BaseNetworkInterfaceDeltaSample,
    BaseNetworkInterfaceDeltaSampleList,
    BaseNetworkInterfaceSample,
    BasePacketData,
)
from remoteperf.utils.attrs_util import attrs_init_replacement


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class QnxCpuUsageInfo(BaseCpuUsageInfo):
    pass


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True, slots=True)
class QnxCpuSample(BaseCpuUsageInfo):
    pass


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class QnxPacketData(BasePacketData):
    broadcast: int
    multicast: int


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class QnxNetworkInterfaceSample(BaseNetworkInterfaceSample):
    receive: QnxPacketData
    transmit: QnxPacketData


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class QnxNetworkPacketDeltaSample(BaseNetworkInterfaceDeltaSample, QnxPacketData):
    pass


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class QnxNetworkInterfaceDeltaSamples(BaseNetworkInterfaceDeltaSampleList):
    receive: List[QnxNetworkPacketDeltaSample]
    transmit: List[QnxNetworkPacketDeltaSample]
