import time

import pytest

from remoteperf.handlers.qnx_handler import MissingQnxCapabilityException, QNXHandler, QNXHandlerException
from remoteperf.models.base import (
    BaseCpuSample,
    BaseCpuUsageInfo,
    BaseMemorySample,
    BootTimeInfo,
    MemoryInfo,
    ModelList,
    SystemMemory,
    SystemUptimeInfo,
)
from remoteperf.models.qnx import QnxCpuUsageInfo
from remoteperf.models.super import CpuSampleProcessInfo, MemorySampleProcessInfo, ProcessInfo, ProcessMemoryList


@pytest.fixture
def broken_qnx_handler(broken_mock_client):
    handler = QNXHandler(client=broken_mock_client)
    yield handler


def test_memory(qnx_handler):
    output = qnx_handler.get_mem_usage()
    assert output.mem == MemoryInfo(total=12944670, used=12818251, free=126418)


def test_exception_memory(broken_qnx_handler):
    with pytest.raises(QNXHandlerException):
        broken_qnx_handler.get_mem_usage()


def test_system_uptime(qnx_handler):
    output = qnx_handler.get_system_uptime()
    assert output.total == 3600.0
    assert isinstance(output, SystemUptimeInfo)


def test_exception_system_uptime(broken_qnx_handler):
    with pytest.raises(QNXHandlerException):
        broken_qnx_handler.get_system_uptime()


def test_cpu_load(qnx_handler):
    output = qnx_handler.get_cpu_usage(interval=1)
    assert output.model_dump(exclude={"timestamp"}) == {
        "cores": {"0": 25, "1": 20, "2": 13, "3": 33, "4": 27, "5": 24},
        "load": 23.67,
    }
    assert isinstance(output, BaseCpuUsageInfo)
    assert isinstance(output, QnxCpuUsageInfo)


def test_get_boot_time(qnx_handler):
    output = qnx_handler.get_boot_time()
    assert output.total == 0.785
    assert isinstance(output, BootTimeInfo)


def test_exception_get_boot_time(broken_qnx_handler):
    with pytest.raises(QNXHandlerException):
        broken_qnx_handler.get_boot_time()


def test_continuous_cpu_load(qnx_handler):
    qnx_handler.start_cpu_measurement(1)
    time.sleep(0.5)
    output = qnx_handler.stop_cpu_measurement()
    for model in output:
        assert model.model_dump(exclude={"timestamp"}) == {
            "cores": {"0": 25, "1": 20, "2": 13, "3": 33, "4": 27, "5": 24},
            "load": 23.67,
        }
        assert isinstance(model, BaseCpuUsageInfo)
        assert isinstance(model, QnxCpuUsageInfo)


def test_continuous_memory(qnx_handler):
    qnx_handler.start_mem_measurement(0.1)
    time.sleep(0.5)
    output = qnx_handler.stop_mem_measurement()
    for model in output:
        assert model.mem.model_dump() == {"free": 126418, "total": 12944670, "used": 12818251}
        assert isinstance(model, SystemMemory)


def test_continuous_cpu_load_proc_wise_count(qnx_handler):
    qnx_handler.start_cpu_measurement_proc_wise(1)
    time.sleep(0.5)
    output = qnx_handler.stop_cpu_measurement_proc_wise()
    # Range to account for flakeyness and potentially overloaded node processor in CI
    assert len(output[0].samples) <= 2


def test_continuous_mem_load_proc_wise_count(qnx_handler):
    qnx_handler.start_mem_measurement_proc_wise(1)
    time.sleep(0.5)
    output = qnx_handler.stop_mem_measurement_proc_wise()
    # Range to account for flakeyness and potentially overloaded node processor in CI
    assert len(output[0].samples) <= 2


def test_continuous_cpu_load_proc_wise_values(qnx_handler):
    qnx_handler.start_cpu_measurement_proc_wise(1)
    time.sleep(0.5)
    output = qnx_handler.stop_cpu_measurement_proc_wise()
    reference = CpuSampleProcessInfo(
        pid=1,
        name="init",
        command="/sbin/init splash",
        start_time="Oct 04 05:27",
        samples=[BaseCpuSample(cpu_load=7.0)],
    )
    assert output[0].model_dump(exclude="samples") == reference.model_dump(exclude="samples")
    assert output[0].samples[0].model_dump(exclude="timestamp") == reference.samples[0].model_dump(exclude="timestamp")


def test_continuous_mem_load_proc_wise_values(qnx_handler):
    qnx_handler.start_mem_measurement_proc_wise(1)
    time.sleep(0.5)
    output = qnx_handler.stop_mem_measurement_proc_wise()
    reference = MemorySampleProcessInfo(
        pid=1,
        command="/sbin/init splash",
        name="init",
        start_time="Oct 04 05:27",
        samples=[
            BaseMemorySample(
                mem_usage=12636,
            )
        ],
    )
    assert output[0].model_dump(exclude="samples") == reference.model_dump(exclude="samples")
    assert output[0].samples[0].model_dump(exclude="timestamp") == reference.samples[0].model_dump(exclude="timestamp")


def test_len_cpu_measurement_proc_wise(qnx_handler):
    data = qnx_handler.get_cpu_usage_proc_wise(read_delay=0.1)
    assert len(data) == 6
    for model in data:
        assert isinstance(model, ProcessInfo)
        assert isinstance(model.samples[0], BaseCpuSample)


def test_valid_cpu_measurement_proc_wise(qnx_handler):
    data = qnx_handler.get_cpu_usage_proc_wise(read_delay=0.1)
    data = data[0].model_dump(exclude={"timestamp"})

    for i, sample in enumerate(data["samples"]):
        tmp = sample
        data["samples"][i] = tmp

    assert data == {
        "pid": 1,
        "command": "/sbin/init splash",
        "name": "init",
        "start_time": "Oct 04 05:27",
        "samples": [{"cpu_load": 7.0}],
    }


def test_length_memory_info_proc_wise(qnx_handler):
    data = qnx_handler.get_mem_usage_proc_wise()
    assert len(data) == 6
    for model in data:
        assert isinstance(model, ProcessInfo)
        assert isinstance(model.samples[0], BaseMemorySample)
        assert isinstance(model.samples[0], BaseMemorySample)


def test_valid_memory_info_proc_wise(qnx_handler):
    data = qnx_handler.get_mem_usage_proc_wise()
    data = data[0].model_dump(exclude={"timestamp"})
    reference = {
        "pid": 1,
        "command": "/sbin/init splash",
        "name": "init",
        "start_time": "Oct 04 05:27",
        "samples": [{"mem_usage": 12636.0}],
    }
    assert data == reference


def test_type_process_qnx(qnx_handler: QNXHandler):
    qnx_handler.start_mem_measurement_proc_wise(0.1)
    time.sleep(0.5)
    output = qnx_handler.stop_mem_measurement_proc_wise()[:2]
    assert isinstance(output, ModelList)
    assert output.__class__ == ProcessMemoryList


def test_type_memory_list_qnx(qnx_handler: QNXHandler):
    qnx_handler.start_mem_measurement_proc_wise(0.1)
    time.sleep(0.5)
    output = qnx_handler.stop_mem_measurement_proc_wise()[:2]
    assert output[0].__class__ == MemorySampleProcessInfo


def test_boot_time_exception(broken_qnx_handler):
    with pytest.raises(MissingQnxCapabilityException):
        broken_qnx_handler.get_boot_time()


def test_get_cpu_proc_exception(broken_qnx_handler):
    with pytest.raises(MissingQnxCapabilityException):
        broken_qnx_handler.get_cpu_usage_proc_wise()


def test_start_cpu_proc_exception(broken_qnx_handler):
    with pytest.raises(MissingQnxCapabilityException):
        broken_qnx_handler.start_cpu_measurement_proc_wise(1)
