import time

import pytest

from remoteperf.handlers.base_linux_handler import BaseLinuxHandlerException
from remoteperf.handlers.linux_handler import LinuxHandler, LinuxHandlerException, MissingLinuxCapabilityException
from remoteperf.models.base import (
    BaseCpuSample,
    BaseCpuUsageInfo,
    BaseMemorySample,
    BaseNetworkTranceiveDeltaSample,
    BootTimeInfo,
    DiskInfo,
    DiskIOInfo,
    ExtendedMemoryInfo,
    LinuxNetworkInterfaceDeltaSampleList,
    LinuxNetworkInterfaceSample,
    LinuxNetworkReceiveDeltaSample,
    LinuxNetworkTransmitDeltaSample,
    LinuxReceivePacketData,
    LinuxTransmitPacketData,
    MemoryInfo,
    ModelList,
    SystemMemory,
    SystemUptimeInfo,
)
from remoteperf.models.linux import LinuxCpuModeUsageInfo, LinuxCpuUsageInfo, LinuxResourceSample
from remoteperf.models.super import (
    DiskInfoList,
    DiskIOList,
    DiskIOProcessSample,
    DiskIOSampleProcessInfo,
    LinuxNetworkInterfaceList,
    MemorySampleProcessInfo,
    ProcessDiskIOList,
    ProcessMemoryList,
    ResourceSampleProcessInfo,
)


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


desired_output_info = DiskInfoList(
    [
        DiskInfo(
            filesystem="/dev/sda",
            size=7654321,
            used=0,
            available=1234567,
            used_percent=11,
            mounted_on="/",
        )
    ]
)


def test_disc_info(linux_handler):
    output = linux_handler.get_diskinfo()
    assert output.model_dump(exclude="timestamp") == desired_output_info.model_dump(exclude="timestamp")


def test_disc_info_cont(linux_handler):
    linux_handler.start_diskinfo_measurement(0.1)
    time.sleep(0.05)
    output = linux_handler.stop_diskinfo_measurement()
    assert output.model_dump(exclude="timestamp") == desired_output_info.model_dump(exclude="timestamp")


desired_output_usage = DiskIOList(
    [
        DiskIOInfo(
            device_major_number=1,
            device_minor_number=0,
            device_name="sda",
            reads_completed=123,
            reads_merged=12,
            sectors_reads=1,
            time_spent_reading=4,
            writes_completed=45,
            writes_merged=456,
            sectors_written=7,
            time_spent_writing=78,
            IOs_currently_in_progress=789,
            time_spent_doing_io=0,
            weighted_time_spent_doing_io=321,
            discards_completed=21,
            discards_merged=654,
            sectors_discarded=54,
            time_spent_discarding=987,
            time_spent_flushing=98,
        )
    ]
)


def test_discio(linux_handler):
    output = linux_handler.get_diskio()
    assert output.model_dump(exclude="timestamp") == desired_output_usage.model_dump(exclude="timestamp")


def test_discio_cont(linux_handler):
    linux_handler.start_diskio_measurement(0.1)
    time.sleep(0.05)
    output = linux_handler.stop_diskio_measurement()
    assert output.model_dump(exclude="timestamp") == desired_output_usage.model_dump(exclude="timestamp")


sample = DiskIOProcessSample(
    rchar=1,
    wchar=2,
    syscr=3,
    syscw=4,
    read_bytes=5,
    write_bytes=6,
    cancelled_write_bytes=7,
)
desired_output_usage_proc_atomic = ProcessDiskIOList(
    [
        DiskIOSampleProcessInfo(
            pid=846,
            name="bash",
            command="/bin/bash",
            samples=[sample],
            start_time="1715",
        )
    ]
)


def test_discio_proc(linux_handler):
    output = linux_handler.get_diskio_proc_wise()
    assert output.model_dump(exclude="timestamp") == desired_output_usage_proc_atomic.model_dump(exclude="timestamp")


desired_output_usage_proc_cont = ProcessDiskIOList(
    [
        DiskIOSampleProcessInfo(
            pid=846,
            name="bash",
            command="/bin/bash",
            samples=[sample, sample],
            start_time="1715",
        )
    ]
)


def test_discio_proc_cont(linux_handler):
    linux_handler.start_diskio_measurement_proc_wise(0.1)
    time.sleep(0.15)
    output = linux_handler.stop_diskio_measurement_proc_wise()
    assert output.model_dump(exclude="timestamp") == desired_output_usage_proc_cont.model_dump(exclude="timestamp")
    assert output[0].avg_read_bytes == 5.0
    assert output[0].avg_write_bytes == 6.0
    assert output[0]._sum_read_bytes == 10
    assert output[0]._sum_write_bytes == 12


def test_network_usage_total(linux_handler):
    output = linux_handler.get_network_usage_total()
    desired_output_total = [
        LinuxNetworkInterfaceSample(
            name="lo",
            receive=LinuxReceivePacketData(
                kibibytes=1024 / 1024,
                packets=10,
                errs=0,
                drop=0,
                fifo=0,
                frame=0,
                compressed=0,
                multicast=0,
            ),
            transmit=LinuxTransmitPacketData(
                kibibytes=2048 / 1024,
                packets=20,
                errs=0,
                drop=0,
                fifo=0,
                colls=0,
                carrier=0,
                compressed=0,
            ),
        ),
        LinuxNetworkInterfaceSample(
            name="eth0",
            receive=LinuxReceivePacketData(
                kibibytes=4096 / 1024,
                packets=50,
                errs=0,
                drop=0,
                fifo=0,
                frame=0,
                compressed=0,
                multicast=1,
            ),
            transmit=LinuxTransmitPacketData(
                kibibytes=5120 / 1024,
                packets=60,
                errs=0,
                drop=0,
                fifo=0,
                colls=0,
                carrier=0,
                compressed=0,
            ),
        ),
    ]
    for interface in output:
        assert interface.model_dump(exclude=["timestamp"]) == desired_output_total.pop(0).model_dump(
            exclude=["timestamp"]
        )


desired_output = LinuxNetworkInterfaceList(
    [
        LinuxNetworkInterfaceDeltaSampleList(
            name="lo",
            receive=[
                LinuxNetworkReceiveDeltaSample(
                    kibibytes=1.0,
                    packets=10,
                    errs=0,
                    drop=0,
                    fifo=0,
                    frame=0,
                    compressed=0,
                    multicast=0,
                    rate=1.0,
                    sampletimediff=1.0,
                )
            ],
            transmit=[
                LinuxNetworkTransmitDeltaSample(
                    kibibytes=2.0,
                    packets=10,
                    errs=0,
                    drop=0,
                    fifo=0,
                    colls=0,
                    carrier=0,
                    compressed=0,
                    rate=2.0,
                    sampletimediff=1.0,
                )
            ],
        ),
        LinuxNetworkInterfaceDeltaSampleList(
            name="eth0",
            receive=[
                LinuxNetworkReceiveDeltaSample(
                    kibibytes=4.0,
                    packets=50,
                    errs=0,
                    drop=0,
                    fifo=0,
                    frame=0,
                    compressed=0,
                    multicast=1,
                    rate=4.0,
                    sampletimediff=1.0,
                )
            ],
            transmit=[
                LinuxNetworkTransmitDeltaSample(
                    kibibytes=5.0,
                    packets=20,
                    errs=0,
                    drop=0,
                    fifo=0,
                    colls=0,
                    carrier=0,
                    compressed=0,
                    rate=5.0,
                    sampletimediff=1.0,
                )
            ],
        ),
    ]
)


def test_network_usage(linux_handler):
    output = linux_handler.get_network_usage(interval=0.1)
    for interface in output:
        assert interface.model_dump(exclude="timestamp") in desired_output.model_dump(exclude="timestamp")


def test_network_usage_continuous(linux_handler):
    linux_handler.start_net_interface_measurement(interval=0.1)
    time.sleep(0.1)
    output = linux_handler.stop_net_interface_measurement()
    for interface in output:
        assert interface.model_dump(exclude="timestamp") in desired_output.model_dump(exclude="timestamp")


def test_network_calc_tranceive(linux_handler):
    linux_handler.start_net_interface_measurement(interval=0.1)
    time.sleep(0.1)
    output = linux_handler.stop_net_interface_measurement()
    desired_transceive_output = {
        "lo": BaseNetworkTranceiveDeltaSample(
            kibibytes=3.0,
            packets=20,
            rate=3.0,
        ),
        "eth0": BaseNetworkTranceiveDeltaSample(
            kibibytes=9.0,
            packets=70,
            rate=9.0,
        ),
    }
    for interface in output:
        assert interface.transceive[0].model_dump(exclude="timestamp") == desired_transceive_output[
            interface.name
        ].model_dump(exclude="timestamp")


def test_network_calc_avg_transceive_rate(linux_handler):
    linux_handler.start_net_interface_measurement(interval=0.1)
    time.sleep(0.1)
    output = linux_handler.stop_net_interface_measurement()
    desired_avg_transceive_output = {"lo": 3.0, "eth0": 9.0}
    for interface in output:
        assert interface.avg_transceive_rate == desired_avg_transceive_output[interface.name]


def test_network_calc_avg_receive_rate(linux_handler):
    linux_handler.start_net_interface_measurement(interval=0.1)
    time.sleep(0.1)
    output = linux_handler.stop_net_interface_measurement()
    desired_avg_receive_output = {"lo": 1.0, "eth0": 4.0}
    for interface in output:
        assert interface.avg_receive_rate == desired_avg_receive_output[interface.name]


def test_network_calc_avg_transmit_rate(linux_handler):
    linux_handler.start_net_interface_measurement(interval=0.1)
    time.sleep(0.1)
    output = linux_handler.stop_net_interface_measurement()
    desired_avg_transmit_output = {"lo": 2.0, "eth0": 5.0}
    for interface in output:
        assert interface.avg_transmit_rate == desired_avg_transmit_output[interface.name]


def test_get_pressure(linux_handler):
    result = linux_handler.get_pressure()
    desired_cpu = {
        "full": {"avg10": 0.0, "avg300": 0.0, "avg60": 0.0, "total": 0},
        "some": {"avg10": 0.13, "avg300": 0.13, "avg60": 0.13, "total": 205171290},
    }

    desired_io = {
        "full": {"avg10": 0.0, "avg300": 0.0, "avg60": 0.0, "total": 18933747},
        "some": {"avg10": 0.0, "avg300": 0.0, "avg60": 0.0, "total": 22426415},
    }
    desired_memory = {
        "full": {"avg10": 0.0, "avg300": 0.0, "avg60": 0.0, "total": 898585},
        "some": {"avg10": 0.0, "avg300": 0.0, "avg60": 0.0, "total": 923912},
    }
    assert result.cpu.model_dump(exclude="timestamp") == desired_cpu
    assert result.io.model_dump(exclude="timestamp") == desired_io
    assert result.memory.model_dump(exclude="timestamp") == desired_memory


def test_get_continuous_pressure(linux_handler):
    linux_handler.start_pressure_measurement(0.1)
    time.sleep(0.3)
    result = linux_handler.stop_pressure_measurement()
    desired_cpu = [
        {
            "some": {"total": 205171290, "avg10": 0.13, "avg60": 0.13, "avg300": 0.13},
            "full": {"total": 0, "avg10": 0.0, "avg60": 0.0, "avg300": 0.0},
        },
        {
            "some": {"total": 205817451, "avg10": 0.0, "avg60": 0.04, "avg300": 0.1},
            "full": {"total": 0, "avg10": 0.0, "avg60": 0.0, "avg300": 0.0},
        },
    ]

    desired_io = [
        {
            "some": {"total": 22426415, "avg10": 0.0, "avg60": 0.0, "avg300": 0.0},
            "full": {"total": 18933747, "avg10": 0.0, "avg60": 0.0, "avg300": 0.0},
        },
        {
            "some": {"total": 22484643, "avg10": 0.0, "avg60": 0.0, "avg300": 0.0},
            "full": {"total": 18986463, "avg10": 0.0, "avg60": 0.0, "avg300": 0.0},
        },
    ]
    desired_memory = [
        {
            "some": {"total": 923912, "avg10": 0.0, "avg60": 0.0, "avg300": 0.0},
            "full": {"total": 898585, "avg10": 0.0, "avg60": 0.0, "avg300": 0.0},
        },
        {
            "some": {"total": 923912, "avg10": 0.0, "avg60": 0.0, "avg300": 0.0},
            "full": {"total": 898585, "avg10": 0.0, "avg60": 0.0, "avg300": 0.0},
        },
    ]

    assert result.cpu.model_dump(exclude="timestamp")[:2] == desired_cpu
    assert result.io.model_dump(exclude="timestamp")[:2] == desired_io
    assert result.memory.model_dump(exclude="timestamp")[:2] == desired_memory


def test_get_highest_continuous_pressure(linux_handler):
    linux_handler.start_pressure_measurement(0.1)
    time.sleep(0.3)
    result = linux_handler.stop_pressure_measurement()

    desired_cpu = {"total": 0, "avg10": 1.0, "avg60": 0.0, "avg300": 0.0}
    desired_io = {"total": 18992689, "avg10": 1.0, "avg60": 0.0, "avg300": 0.0}
    desired_memory = {"total": 898585, "avg10": 1.0, "avg60": 0.0, "avg300": 0.0}

    assert result.cpu.full.highest_pressure(1)[0].model_dump(exclude="timestamp") == desired_cpu
    assert result.io.full.highest_pressure(1)[0].model_dump(exclude="timestamp") == desired_io
    assert result.memory.full.highest_pressure(1)[0].model_dump(exclude="timestamp") == desired_memory
