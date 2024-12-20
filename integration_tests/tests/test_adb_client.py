import pathlib
import random
import subprocess
import time

import pytest

from remoteperf.clients.adb_client import ADBClientException
from remoteperf.clients.base_client import BaseClientException
from remoteperf.handlers.android_handler import AndroidHandler
from remoteperf.handlers.qnx_handler import MissingQnxCapabilityException, QNXHandler
from remoteperf.models.base import BaseCpuSample, BaseMemorySample, SystemMemory
from remoteperf.models.linux import LinuxCpuUsageInfo, LinuxResourceSample
from remoteperf.models.super import ProcessInfo


def kill_adb_server():
    try:
        subprocess.check_output(["adb", "kill-server"])
    except Exception:
        pass


def test_adb_client_kill_server_1(adb_client):  # We place these here and there to cause as much havoc as possible
    handler = AndroidHandler(adb_client)
    handler.start_cpu_measurement_proc_wise(0.1)
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    output = handler.stop_cpu_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_adb_cpu_usage(adb_client):
    handler = AndroidHandler(adb_client)
    output = handler.get_cpu_usage()
    assert isinstance(output, LinuxCpuUsageInfo)


def test_adb_mem_usage(adb_client):
    handler = AndroidHandler(adb_client)
    output = handler.get_mem_usage()
    assert isinstance(output, SystemMemory)


def test_adb_continuous_cpu_usage(adb_client):
    handler = AndroidHandler(adb_client)
    handler.start_cpu_measurement(interval=0.1)
    time.sleep(1)
    output = handler.stop_cpu_measurement()
    assert output
    assert all((isinstance(model, LinuxCpuUsageInfo) for model in output))


def test_adb_continuous_mem_usage(adb_client):
    handler = AndroidHandler(adb_client)
    handler.start_mem_measurement(interval=0.1)
    time.sleep(1)
    output = handler.stop_mem_measurement()
    assert output
    assert all((isinstance(model, SystemMemory) for model in output))


def test_adb_continuous_cpu_usage_proc_wise(adb_client):
    handler = AndroidHandler(adb_client)
    handler.start_cpu_measurement_proc_wise(interval=0.1)
    time.sleep(1)
    output = handler.stop_cpu_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_adb_client_kill_server_2(adb_client):
    handler = AndroidHandler(adb_client)
    handler.start_cpu_measurement_proc_wise(0.1)
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    output = handler.stop_cpu_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_adb_continuous_mem_usage_proc_wise(adb_client):
    handler = AndroidHandler(adb_client)
    handler.start_mem_measurement_proc_wise(interval=0.1)
    time.sleep(1)
    output = handler.stop_mem_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_adb_procwise_cpu_usage_len(adb_client):
    handler = AndroidHandler(adb_client)
    usage = handler.get_cpu_usage_proc_wise()
    assert len(usage) > 10  # Arbitrary


def test_adb_procwise_cpu_usage_type(adb_client):
    handler = AndroidHandler(adb_client)
    usage = handler.get_cpu_usage_proc_wise()
    for process in usage:
        assert all(isinstance(s, LinuxResourceSample) and isinstance(s, BaseCpuSample) for s in process.samples)
        assert len(process.samples) == 1


def test_adb_procwise_mem_usage_len(adb_client):
    handler = AndroidHandler(adb_client)
    usage = handler.get_mem_usage_proc_wise()
    assert len(usage) > 10  # Arbitrary


def test_adb_procwise_mem_usage_type(adb_client):
    handler = AndroidHandler(adb_client)
    usage = handler.get_mem_usage_proc_wise()
    for process in usage:
        assert all(isinstance(s, BaseMemorySample) for s in process.samples)
        assert len(process.samples) == 1


def test_adb_get_file_no_dir(adb_client):
    path = f"/tmp/{''.join(random.sample('abcdef0123456789', 10))}/wm"
    with pytest.raises(ADBClientException):
        adb_client.pull_file("/bin/wm", path)


def test_adb_get_file_dir(adb_client, tdir):
    adb_client.pull_file("/bin/wm", tdir)
    assert (pathlib.Path(tdir) / "wm").exists()


def test_adb_client_kill_server_3(adb_client):
    handler = AndroidHandler(adb_client)
    handler.start_cpu_measurement_proc_wise(0.1)
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    output = handler.stop_cpu_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_adb_get_file_filename(adb_client, tdir):
    adb_client.pull_file("/bin/wm", tdir / "wm")
    assert (pathlib.Path(tdir) / "wm").exists()
    assert not (pathlib.Path(tdir) / "wm" / "wm").exists()


def test_adb_get_file_override(adb_client, tdir):
    adb_client.pull_file("/bin/wm", tdir)
    adb_client.pull_file("/bin/wm", tdir)
    assert (pathlib.Path(tdir) / "wm").exists()


def test_adb_push_file_no_dir(adb_client):
    path = f"/tmp/{''.join(random.sample('abcdef0123456789', 10))}/cat"
    with pytest.raises(BaseClientException):
        adb_client.push_file("/usr/bin/cat", path)


def test_adb_push_file_dir(adb_client):
    handler = AndroidHandler(client=adb_client)
    with handler.fs_utils.temporary_directory() as tdir:
        adb_client.push_file("/usr/bin/cat", tdir)
        assert handler.fs_utils.is_file(f"{tdir}/cat")


def test_adb_push_file_filename(adb_client):
    handler = AndroidHandler(adb_client)
    with handler.fs_utils.temporary_directory() as tdir:
        adb_client.push_file("/usr/bin/cat", f"{tdir}/cat")
        assert handler.fs_utils.is_file(f"{tdir}/cat")
        assert not handler.fs_utils.is_file(f"{tdir}/cat/cat")


def test_adb_push_file_override(adb_client):
    handler = AndroidHandler(adb_client)
    with handler.fs_utils.temporary_directory() as tdir:
        adb_client.push_file("/usr/bin/cat", tdir)
        adb_client.push_file("/usr/bin/cat", tdir)
        assert AndroidHandler(adb_client).fs_utils.is_file(f"{tdir}/cat")


def test_adb_push_rename(adb_client):
    adb_client.pull_file("/bin/monkey", "/tmp/bdljfhnsdjkfn")
    assert pathlib.Path("/tmp/bdljfhnsdjkfn").exists()


def test_adb_client_kill_server_4(adb_client):
    handler = AndroidHandler(adb_client)
    handler.start_cpu_measurement_proc_wise(0.1)
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    output = handler.stop_cpu_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_adb_client_kill_server_5(adb_client):
    handler = AndroidHandler(adb_client)
    handler.start_cpu_measurement_proc_wise(0.1)
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    output = handler.stop_cpu_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))


def test_adb_qnx_missing_bmetrics(adb_client):
    handler = QNXHandler(adb_client)
    with pytest.raises(MissingQnxCapabilityException):
        handler.get_boot_time()


def test_adb_qnx_missing_hogs(adb_client):
    handler = QNXHandler(adb_client)
    with pytest.raises(MissingQnxCapabilityException):
        handler.get_cpu_usage_proc_wise()
    with pytest.raises(MissingQnxCapabilityException):
        handler.start_cpu_measurement_proc_wise(1)


def test_adb_client_kill_server_6(adb_client):
    handler = AndroidHandler(adb_client)
    handler.start_cpu_measurement_proc_wise(0.1)
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    time.sleep(0.2)
    kill_adb_server()
    output = handler.stop_cpu_measurement_proc_wise()
    assert output
    assert output[0].samples
    assert all((isinstance(model, ProcessInfo) for model in output))
