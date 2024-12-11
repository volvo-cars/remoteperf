# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import attr

from src.models.base import BaseCpuUsageInfo
from src.utils.attrs_util import attrs_init_replacement


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class QnxCpuUsageInfo(BaseCpuUsageInfo):
    pass


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True, slots=True)
class QnxCpuSample(BaseCpuUsageInfo):
    pass
