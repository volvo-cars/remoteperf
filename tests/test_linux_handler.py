import time

import pytest

from src.handlers.base_linux_handler import BaseLinuxHandlerException
from src.handlers.linux_handler import LinuxHandler, LinuxHandlerException, MissingLinuxCapabilityException
from src.models.base import (
    BaseCpuSample,
    BaseCpuUsageInfo,
    BaseMemorySample,
    BootTimeInfo,
    ExtendedMemoryInfo,
    MemoryInfo,
    ModelList,
    SystemMemory,
    SystemUptimeInfo,
)
from src.models.linux import LinuxCpuModeUsageInfo, LinuxCpuUsageInfo, LinuxResourceSample
from src.models.super import MemorySampleProcessInfo, ProcessMemoryList, ResourceSampleProcessInfo


def get_time_py_pid(lst, pid):
    return next((e.samples[0].timestamp for e in lst if e.pid == pid), None)


@pytest.fixture
def broken_linux_handler(broken_mock_client):
    return LinuxHandler(client=broken_mock_client)


def test_memory(linux_handler):
    output = linux_handler.get_mem_usage()
    assert output.mem == ExtendedMemoryInfo(
        total=32031624, used=6024668, free=18189336, shared=909004, buff_cache=7817620, available=24630432
    )
    assert isinstance(output, SystemMemory)


def test_swap(linux_handler):
    output = linux_handler.get_mem_usage()
    assert output.swap == MemoryInfo(total=2002940, used=0, free=2002940)


def test_boot_total(linux_handler):
    output = linux_handler.get_boot_time()
    assert output.total == 23.132
    assert isinstance(output, BootTimeInfo)


def test_boot_extra(linux_handler):
    output = linux_handler.get_boot_time()
    assert output.extra == {"kernel": 11.406, "userspace": 11.725, "graphical.target": 11.679}


def test_cpu_load(linux_handler):
    output = linux_handler.get_cpu_usage()
    assert output.load == 1.0
    assert isinstance(output, LinuxCpuUsageInfo)
    assert isinstance(output, BaseCpuUsageInfo)


def test_cpu_cores(linux_handler):
    output = linux_handler.get_cpu_usage()
    assert output.cores == {"0": 1.0}


def test_cpu_modes(linux_handler):
    output = linux_handler.get_cpu_usage()
    assert output.mode_usage == LinuxCpuModeUsageInfo(
        user=1.0,
        nice=0,
        system=0,
        idle=99.0,
        iowait=0,
        irq=0,
        softirq=0,
        steal=0,
        guest=0,
        guest_nice=0,
    )


def test_continuous_cpu_load_values(linux_handler):
    linux_handler.start_cpu_measurement(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_cpu_measurement()
    for i, model in enumerate(output):
        assert model.load == i + 1
        assert isinstance(model, LinuxCpuUsageInfo)
        assert isinstance(model, BaseCpuUsageInfo)


def test_continuous_cpu_load_cores(linux_handler):
    linux_handler.start_cpu_measurement(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_cpu_measurement()
    for i, model in enumerate(output):
        assert model.cores["0"] == i + 1


def test_continuous_cpu_load_count(linux_handler):
    linux_handler.start_cpu_measurement(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_cpu_measurement()
    # Range to account for flakeyness and potentially overloaded node processor in CI
    assert len(output) >= 3 and len(output) <= 5


def test_continuous_memory(linux_handler):
    linux_handler.start_mem_measurement(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_mem_measurement()
    for model in output:
        assert isinstance(model, SystemMemory)
    assert {
        "total": 32031624,
        "used": 6024668,
        "free": 18189336,
        "shared": 909004,
        "buff_cache": 7817620,
        "available": 24630432,
    } in [out.mem.model_dump(exclude="timestamp") for out in output]


def test_continuous_cpu_load_proc_wise_count(linux_handler):
    linux_handler.start_cpu_measurement_proc_wise(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_cpu_measurement_proc_wise()
    # Range to account for flakeyness and potentially overloaded node processor in CI
    assert len(output[0].samples) >= 3 and len(output[0].samples) <= 5


def test_continuous_mem_load_proc_wise_count(linux_handler):
    linux_handler.start_mem_measurement_proc_wise(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_mem_measurement_proc_wise()
    # Range to account for flakeyness and potentially overloaded node processor in CI
    assert len(output[0].samples) >= 4 and len(output[0].samples) <= 7


def test_continuous_cpu_load_proc_wise_values(linux_handler):
    linux_handler.start_cpu_measurement_proc_wise(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_cpu_measurement_proc_wise()
    reference = ResourceSampleProcessInfo(
        pid=1,
        name="init",
        command="/system/bin/initsecond_stage",
        start_time="30",
        samples=[LinuxResourceSample(mem_usage=6700.0, cpu_load=10.0)],
    )
    assert output[0].model_dump(exclude="samples") == reference.model_dump(exclude="samples")
    assert output[0].samples[0].model_dump(exclude="timestamp") == reference.samples[0].model_dump(exclude="timestamp")


def test_continuous_mem_load_proc_wise_values(linux_handler):
    linux_handler.start_mem_measurement_proc_wise(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_mem_measurement_proc_wise()
    reference = MemorySampleProcessInfo(
        pid=1,
        name="init",
        command="/system/bin/initsecond_stage",
        start_time="30",
        samples=[BaseMemorySample(mem_usage=6700.0)],
    )
    assert output[0].model_dump(exclude="samples") == reference.model_dump(exclude="samples")
    assert output[0].samples[0].model_dump(exclude="timestamp") == reference.samples[0].model_dump(exclude="timestamp")


def test_system_uptime(linux_handler):
    output = linux_handler.get_system_uptime()
    assert output.total == 10978.92
    assert isinstance(output, SystemUptimeInfo)


# If, for whatever reason, partial/wrongly formatted data is returned
def test_exception_memory(broken_linux_handler):
    with pytest.raises(BaseLinuxHandlerException):
        broken_linux_handler.get_mem_usage()


def test_exception_boot(broken_linux_handler):
    with pytest.raises(LinuxHandlerException):
        broken_linux_handler.get_boot_time()


def test_mem_usage_proc_wise(linux_handler):
    output = linux_handler.get_mem_usage_proc_wise()

    process = MemorySampleProcessInfo(
        pid=1005,
        name="classifier@1.0-",
        command="/vendor/bin/hw/android.hardware.input.classifier@1.0-service.default",
        samples=[BaseMemorySample(timestamp=get_time_py_pid(output, 1005), mem_usage=4316.0)],
        start_time="5762",
    )
    assert process in output
    for process in output:
        assert isinstance(process, MemorySampleProcessInfo)
        assert all(isinstance(sample, BaseMemorySample) for sample in process.samples)


def test_cpu_modes_proc_wise(linux_handler):
    output = linux_handler.get_cpu_usage_proc_wise()

    processes = [
        ResourceSampleProcessInfo(
            pid=1,
            name="init",
            command="/system/bin/initsecond_stage",
            samples=[LinuxResourceSample(timestamp=get_time_py_pid(output, 1), mem_usage=6700.0, cpu_load=10.0)],
            start_time="30",
        ),
        ResourceSampleProcessInfo(
            pid=10,
            name="rcu_tasks_kthre",
            command="rcu_tasks_kthre",
            samples=[LinuxResourceSample(timestamp=get_time_py_pid(output, 10), mem_usage=8000.0, cpu_load=1.0)],
            start_time="30",
        ),
        ResourceSampleProcessInfo(
            pid=1005,
            name="classifier@1.0-",
            command="/vendor/bin/hw/android.hardware.input.classifier@1.0-service.default",
            samples=[LinuxResourceSample(timestamp=get_time_py_pid(output, 1005), mem_usage=4316.0, cpu_load=0.0)],
            start_time="5762",
        ),
    ]
    for process in processes:
        assert process in output
        assert all(isinstance(sample, BaseCpuSample) for sample in process.samples)


def test_type_process(linux_handler: LinuxHandler):
    linux_handler.start_mem_measurement_proc_wise(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_mem_measurement_proc_wise()[:2]
    assert isinstance(output, ModelList)
    assert output.__class__ == ProcessMemoryList


def test_missing_boot_time_exception(broken_linux_handler):
    with pytest.raises(MissingLinuxCapabilityException):
        broken_linux_handler.get_boot_time()
