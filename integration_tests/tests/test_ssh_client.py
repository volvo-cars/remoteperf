import pathlib
import random
import time

import pytest
from conftest import override_client_config

from remoteperf.clients.base_client import BaseClientException
from remoteperf.clients.ssh_client import SSHClient, SSHClientException
from remoteperf.handlers.linux_handler import LinuxHandler
from remoteperf.models.base import (
    BaseCpuSample,
    BaseCpuUsageInfo,
    BaseMemorySample,
    BootTimeInfo,
    SystemMemory,
    SystemUptimeInfo,
)
from remoteperf.models.linux import LinuxCpuUsageInfo, LinuxPressureInfo, LinuxResourceSample
from remoteperf.models.super import DiskInfoList, DiskIOList, ProcessDiskIOList, ProcessInfo


def close_transport(client: SSHClient):
    try:
        if (transport := client._client.get_transport()) is not None:
            transport.close()
    except Exception:
        pass


def close_connection(client: SSHClient):
    try:
        client._client.close()
    except Exception:
        pass


def test_ssh_client_transport_crash_1(ssh_client):
    handler = LinuxHandler(ssh_client)
    handler.start_mem_measurement_proc_wise(0.1)
    for _ in range(3):
        time.sleep(0.2)
        close_transport(ssh_client)
    for _ in range(3):
        time.sleep(1.5)
        close_connection(ssh_client)
    output = handler.stop_mem_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_ssh_boot_time(ssh_client):
    handler = LinuxHandler(ssh_client)
    output = handler.get_boot_time()
    assert isinstance(output, BootTimeInfo)


def test_ssh_already_connected(ssh_client):
    ssh_client.connect()
    assert ssh_client.connected


def test_ssh_system_uptime(ssh_client):
    handler = LinuxHandler(ssh_client)
    output = handler.get_system_uptime()
    assert isinstance(output, SystemUptimeInfo)


def test_ssh_client_transport_crash_2(ssh_client):
    handler = LinuxHandler(ssh_client)
    handler.start_cpu_measurement(0.1)
    for _ in range(3):
        time.sleep(0.2)
        close_transport(ssh_client)
    for _ in range(3):
        time.sleep(1.5)
        close_connection(ssh_client)
    output = handler.stop_cpu_measurement()
    assert output
    assert all((isinstance(model, BaseCpuUsageInfo) for model in output))


def test_ssh_cpu_usage(ssh_client):
    handler = LinuxHandler(ssh_client)
    output = handler.get_cpu_usage()
    assert isinstance(output, LinuxCpuUsageInfo)


def test_ssh_mem_usage(ssh_client):
    handler = LinuxHandler(ssh_client)
    output = handler.get_mem_usage()
    assert isinstance(output, SystemMemory)


def test_ssh_continuous_cpu_usage(ssh_client):
    handler = LinuxHandler(ssh_client)
    handler.start_cpu_measurement(interval=0.1)
    time.sleep(1)
    output = handler.stop_cpu_measurement()
    assert output
    assert all((isinstance(model, LinuxCpuUsageInfo) for model in output))


def test_ssh_continuous_mem_usage(ssh_client):
    handler = LinuxHandler(ssh_client)
    handler.start_mem_measurement(interval=0.1)
    time.sleep(1)
    output = handler.stop_mem_measurement()
    assert output
    assert all((isinstance(model, SystemMemory) for model in output))


def test_ssh_client_transport_crash_3(ssh_client):
    handler = LinuxHandler(ssh_client)
    handler.start_mem_measurement(0.1)
    for _ in range(3):
        time.sleep(0.2)
        close_transport(ssh_client)
    for _ in range(3):
        time.sleep(1.5)
        close_connection(ssh_client)
    output = handler.stop_mem_measurement()
    assert output
    assert all((isinstance(model, SystemMemory) for model in output))


def test_ssh_continuous_cpu_usage_proc_wise(ssh_client):
    handler = LinuxHandler(ssh_client)
    handler.start_cpu_measurement_proc_wise(interval=0.1)
    time.sleep(1)
    output = handler.stop_cpu_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_ssh_continuous_cpu_usage_proc_wise_no_delay(ssh_client):
    handler = LinuxHandler(ssh_client)
    handler.start_cpu_measurement_proc_wise(interval=10)
    output = handler.stop_cpu_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_ssh_continuous_mem_usage_proc_wise(ssh_client):
    handler = LinuxHandler(ssh_client)
    handler.start_mem_measurement_proc_wise(interval=0.1)
    time.sleep(1)
    output = handler.stop_mem_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_ssh_continuous_mem_usage_proc_wise_no_delay(ssh_client):
    handler = LinuxHandler(ssh_client)
    handler.start_mem_measurement_proc_wise(interval=10)
    output = handler.stop_mem_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_ssh_client_transport_crash_pull(ssh_client):
    # Should just not crash
    ssh_client.pull_file("/usr/bin/bash", "/tmp/bash")
    close_transport(ssh_client)
    ssh_client.pull_file("/usr/bin/bash", "/tmp/bash")
    close_connection(ssh_client)
    ssh_client.pull_file("/usr/bin/bash", "/tmp/bash")


def test_ssh_procwise_cpu_usage_len(ssh_client, spawned_processes):
    handler = LinuxHandler(ssh_client)
    usage = handler.get_cpu_usage_proc_wise()
    assert len(usage) > 100


def test_ssh_procwise_cpu_usage_type(ssh_client):
    handler = LinuxHandler(ssh_client)
    usage = handler.get_cpu_usage_proc_wise()
    for process in usage:
        assert all(isinstance(s, LinuxResourceSample) and isinstance(s, BaseCpuSample) for s in process.samples)
        assert len(process.samples) == 1


def test_ssh_procwise_mem_usage_len(ssh_client, spawned_processes):
    handler = LinuxHandler(ssh_client)
    usage = handler.get_mem_usage_proc_wise()
    assert len(usage) > 100


def test_ssh_procwise_mem_usage_type(ssh_client):
    handler = LinuxHandler(ssh_client)
    usage = handler.get_mem_usage_proc_wise()
    for process in usage:
        assert all(isinstance(s, BaseMemorySample) for s in process.samples)
        assert len(process.samples) == 1


def test_ssh_client_transport_crash_push(ssh_client):
    # Should just not crash
    ssh_client.push_file("/usr/bin/bash", "/tmp/bash")
    close_transport(ssh_client)
    ssh_client.push_file("/usr/bin/bash", "/tmp/bash")
    close_connection(ssh_client)
    ssh_client.push_file("/usr/bin/bash", "/tmp/bash")


def test_ssh_pull_directory(ssh_client):
    path = f"/tmp/{''.join(random.sample('abcdef0123456789', 10))}/xz"
    with pytest.raises(SSHClientException):
        ssh_client.pull_file("/usr/bin/xz", path)


def test_ssh_pull_dir(ssh_client):
    path = "/tmp"
    with pytest.raises(BaseClientException):
        ssh_client.pull_file("/usr/bin", path)


def test_ssh_pull_imaginary_dir(ssh_client):
    path = "/sdfgsdf/sfgdh"
    with pytest.raises(BaseClientException):
        ssh_client.pull_file("/usr/bin/xz", path)


def test_ssh_pull_imaginary_file(ssh_client):
    with pytest.raises(BaseClientException):
        ssh_client.pull_file("/usr/bin/xz2344", "/tmp")


def test_ssh_push_rename(ssh_client):
    ssh_client.pull_file("/usr/bin/xz", "/tmp/bdljfhnsdjkfn")
    assert pathlib.Path("/tmp/bdljfhnsdjkfn").exists()


def test_ssh_client_transport_crash_6(ssh_client):
    handler = LinuxHandler(ssh_client)
    handler.start_cpu_measurement(0.1)
    handler.start_cpu_measurement_proc_wise(0.1)
    handler.start_mem_measurement(0.1)
    handler.start_mem_measurement_proc_wise(0.1)
    for _ in range(3):
        time.sleep(0.2)
        close_transport(ssh_client)
    for _ in range(3):
        time.sleep(1.5)
        close_connection(ssh_client)
    handler.stop_cpu_measurement()
    handler.stop_mem_measurement()
    handler.stop_mem_measurement_proc_wise()
    output = handler.stop_cpu_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_ssh_push_imaginary_dir(ssh_client):
    with pytest.raises(BaseClientException):
        ssh_client.push_file("/usr/bin/cat", "/tmp/dsjkfh/hsdjgfhj")


def test_ssh_push_dir(ssh_client):
    with pytest.raises(BaseClientException):
        ssh_client.push_file("/usr/bin", "/tmp")


def test_ssh_push_imaginary_file(ssh_client):
    with pytest.raises(BaseClientException):
        ssh_client.push_file("/usr/bin/xz2344", "/tmp")


def test_ssh_get_file_dir(ssh_client, tdir):
    ssh_client.pull_file("/usr/bin/xz", tdir)
    assert (pathlib.Path(tdir) / "xz").exists()


def test_ssh_get_file_filename(ssh_client, tdir):
    ssh_client.pull_file("/usr/bin/xz", tdir / "xz")
    assert (pathlib.Path(tdir) / "xz").exists()
    assert not (pathlib.Path(tdir) / "xz" / "xz").exists()


def test_ssh_get_file_override(ssh_client, tdir):
    ssh_client.pull_file("/usr/bin/xz", tdir)
    ssh_client.pull_file("/usr/bin/xz", tdir)
    assert (pathlib.Path(tdir) / "xz").exists()


def test_ssh_push_file_no_dir(ssh_client):
    path = f"/tmp/{''.join(random.sample('abcdef0123456789', 10))}/cat"
    with pytest.raises(BaseClientException):
        ssh_client.push_file("/usr/bin/cat", path)


def test_ssh_push_file_dir(ssh_client):
    handler = LinuxHandler(ssh_client)
    with handler.fs_utils.temporary_directory() as tdir:
        ssh_client.push_file("/usr/bin/cat", tdir)
        assert handler.fs_utils.is_file(f"{tdir}/cat")


def test_ssh_push_file_filename(ssh_client):
    handler = LinuxHandler(ssh_client)
    with handler.fs_utils.temporary_directory() as tdir:
        ssh_client.push_file("/usr/bin/cat", tdir)
        assert handler.fs_utils.is_file(f"{tdir}/cat")
        assert not handler.fs_utils.is_file(f"{tdir}/cat/cat")


def test_ssh_push_file_override(ssh_client):
    handler = LinuxHandler(ssh_client)
    with handler.fs_utils.temporary_directory() as tdir:
        ssh_client.push_file("/usr/bin/cat", tdir)
        ssh_client.push_file("/usr/bin/cat", tdir)
        assert LinuxHandler(ssh_client).fs_utils.is_file(f"{tdir}/cat")


def test_ssh_client_timeout(ssh_client):
    with override_client_config(ssh_client, 0, 1) as client:
        t0 = time.time()
        with pytest.raises(SSHClientException):
            client.run_command("sleep 1.5")
        assert time.time() - t0 < 2


def test_ssh_client_retry(ssh_client):
    with override_client_config(ssh_client, 3, 1) as client:
        t0 = time.time()
        with pytest.raises(SSHClientException):
            client.run_command("sleep 1.5")
        assert time.time() - t0 > 3 and time.time() - t0 < 7


def test_diskinfo(ssh_client):
    handler = LinuxHandler(ssh_client)
    output = handler.get_diskinfo()
    assert output
    assert isinstance(output, DiskInfoList)


def test_diskio(ssh_client):
    handler = LinuxHandler(ssh_client)
    output = handler.get_diskio()
    assert output
    assert isinstance(output, DiskIOList)


def test_diskio_proc_wise(ssh_client):
    handler = LinuxHandler(ssh_client)
    output = handler.get_diskio_proc_wise()
    assert output
    assert isinstance(output, ProcessDiskIOList)
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_ssh_get_pressure(ssh_client):
    handler = LinuxHandler(ssh_client)
    output = handler.get_pressure()
    assert output
    assert isinstance(output, LinuxPressureInfo)


def test_ssh_continuous_get_pressure(ssh_client):
    handler = LinuxHandler(ssh_client)
    handler.start_pressure_measurement(interval=0.1)
    time.sleep(1)
    output = handler.stop_pressure_measurement()
    assert output
    assert output.cpu.full[0]
    assert all((isinstance(model, LinuxPressureInfo) for model in output))
