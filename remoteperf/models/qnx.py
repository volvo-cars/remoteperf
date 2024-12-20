# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import time

import attr

from remoteperf.models.base import BaseCpuUsageInfo, DiskInfo
from remoteperf.models.super import DiskInfoList
from remoteperf.utils.attrs_util import attrs_init_replacement


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True)
class QnxCpuUsageInfo(BaseCpuUsageInfo):
    pass


@attrs_init_replacement
@attr.s(auto_attribs=True, kw_only=True, slots=True)
class QnxCpuSample(BaseCpuUsageInfo):
    pass


def test_disc_info(unique_qnx_handler):
    output = unique_qnx_handler.get_diskinfo()
    desired_output = DiskInfoList(
        [
            DiskInfo(
                filesystem="/dev/sda",
                size=7654321,
                used=0,
                available=1234567,
                used_percent=11,
                mounted_on="/",
            ),
            DiskInfo(
                filesystem="/dev/sda",
                size=654321,
                used=0,
                available=123456,
                used_percent=10,
                mounted_on="/",
            ),
        ],
    )
    assert output.model_dump(exclude="timestamp") == desired_output.model_dump(exclude="timestamp")


def test_disc_info_cont(unique_qnx_handler):
    unique_qnx_handler.start_diskinfo_measurement(0.1)
    time.sleep(0.1)
    output = unique_qnx_handler.stop_diskinfo_measurement()
    disc_info_sda = DiskInfo(
        filesystem="/dev/sda",
        size=7654321,
        used=0,
        available=1234567,
        used_percent=11,
        mounted_on="/",
    )
    disc_info_sdb = DiskInfo(
        filesystem="/dev/sda",
        size=654321,
        used=0,
        available=123456,
        used_percent=10,
        mounted_on="/",
    )
    desired_output = DiskInfoList([disc_info_sda, disc_info_sda, disc_info_sdb, disc_info_sdb])
    assert output.model_dump(exclude="timestamp") == desired_output.model_dump(exclude="timestamp")
