import json
from datetime import datetime

import pytest
import yaml

from src.models.base import (
    BaseCpuSample,
    BaseMemorySample,
    BootTimeInfo,
    ExtendedMemoryInfo,
    MemoryInfo,
    SystemMemory,
    SystemUptimeInfo,
)
from src.models.linux import LinuxBootTimeInfo, LinuxCpuModeUsageInfo, LinuxCpuUsageInfo, LinuxResourceSample
from src.models.qnx import QnxCpuUsageInfo
from src.models.super import CpuSampleProcessInfo, MemorySampleProcessInfo, ResourceSampleProcessInfo


def reserialize_yaml(object: dict):
    stringified_object = yaml.dump(object)
    return yaml.safe_load(stringified_object)


def reserialize_json(object: dict):
    stringified_object = json.dumps(object)
    return json.loads(stringified_object)


def test_model_cpu_linux():
    model = LinuxCpuUsageInfo(
        load=6,
        cores={"0": 1, "1": 2, "3": 3},
        mode_usage=LinuxCpuModeUsageInfo(
            user=6.0, nice=0, system=0, idle=94.0, iowait=0, irq=0, softirq=0, steal=0, guest=0, guest_nice=0
        ),
    )
    assert (
        model
        == LinuxCpuUsageInfo(**reserialize_yaml(model.model_dump()))
        == LinuxCpuUsageInfo(**reserialize_json(model.model_dump()))
    )


def test_model_cpu_qnx():
    model = QnxCpuUsageInfo(load=25.4, cores={"0": 2.5, "1": 1.1, "2": 1.8, "3": 28.0})
    assert (
        model
        == QnxCpuUsageInfo(**reserialize_yaml(model.model_dump()))
        == QnxCpuUsageInfo(**reserialize_json(model.model_dump()))
    )


def test_model_cpu_proc_wise_qnx():
    model = CpuSampleProcessInfo(
        pid=1005,
        name="classifier@1.0-",
        command="/vendor/bin/hw/android.hardware.input.classifier@1.0-service.default",
        samples=[
            BaseCpuSample(cpu_load=1),
        ],
        start_time="5762",
    )
    assert (
        model
        == CpuSampleProcessInfo(**reserialize_yaml(model.model_dump()))
        == CpuSampleProcessInfo(**reserialize_json(model.model_dump()))
    )


def test_model_cpu_proc_wise_linux():
    model = ResourceSampleProcessInfo(
        pid=1005,
        name="classifier@1.0-",
        command="/vendor/bin/hw/android.hardware.input.classifier@1.0-service.default",
        samples=[
            LinuxResourceSample(mem_usage=4316.0, cpu_load=0.0),
        ],
        start_time="5762",
    )
    assert (
        model
        == ResourceSampleProcessInfo(**reserialize_yaml(model.model_dump()))
        == ResourceSampleProcessInfo(**reserialize_json(model.model_dump()))
    )


def test_model_mem_proc_wise_qnx():
    model = MemorySampleProcessInfo(
        pid=1005,
        name="classifier@1.0-",
        command="/vendor/bin/hw/android.hardware.input.classifier@1.0-service.default",
        samples=[BaseMemorySample(mem_usage=1.0)],
        start_time="5762",
    )
    assert (
        model
        == MemorySampleProcessInfo(**reserialize_yaml(model.model_dump()))
        == MemorySampleProcessInfo(**reserialize_json(model.model_dump()))
    )


def test_model_mem_proc_wise_linux():
    model = MemorySampleProcessInfo(
        pid=1005,
        name="classifier@1.0-",
        command="/vendor/bin/hw/android.hardware.input.classifier@1.0-service.default",
        samples=[
            BaseMemorySample(mem_usage=1),
        ],
        start_time="5762",
    )
    assert (
        model
        == MemorySampleProcessInfo(**reserialize_yaml(model.model_dump()))
        == MemorySampleProcessInfo(**reserialize_json(model.model_dump()))
    )


def test_model_extended_memory():
    model = SystemMemory(
        mem=ExtendedMemoryInfo(
            total=32031624, used=6024668, free=18189336, shared=909004, buff_cache=7817620, available=24630432
        ),
        swap=MemoryInfo(total=32031624, used=6024668, free=18189336),
    )
    assert (
        model
        == SystemMemory(**reserialize_yaml(model.model_dump()))
        == SystemMemory(**reserialize_json(model.model_dump()))
    )


def test_model_boot_time():
    model = BootTimeInfo(total=10)
    assert (
        model
        == BootTimeInfo(**reserialize_yaml(model.model_dump()))
        == BootTimeInfo(**reserialize_json(model.model_dump()))
    )


def test_model_linux_boot_time():
    model = LinuxBootTimeInfo(total=10, extra={"kernel": 11.406, "userspace": 11.725, "graphical.target": 11.679})
    assert (
        model
        == LinuxBootTimeInfo(**reserialize_yaml(model.model_dump()))
        == LinuxBootTimeInfo(**reserialize_json(model.model_dump()))
    )


def test_model_uptime():
    model = SystemUptimeInfo(total=10)
    assert (
        model
        == SystemUptimeInfo(**reserialize_yaml(model.model_dump()))
        == SystemUptimeInfo(**reserialize_json(model.model_dump()))
    )
