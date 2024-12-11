import textwrap
import time

from src.handlers.linux_handler import LinuxHandler
from src.models.base import ExtendedMemoryInfo, MemoryInfo, SystemMemory
from src.models.linux import LinuxCpuUsageInfo


def test_avg_cpu(linux_handler: LinuxHandler):
    linux_handler.start_cpu_measurement(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_cpu_measurement()[:3]
    assert output.avg.model_dump(exclude="timestamp") == LinuxCpuUsageInfo(
        **{
            "cores": {"0": 2.0},
            "load": 2.0,
            "mode_usage": {
                "guest": 0.0,
                "guest_nice": 0.0,
                "idle": 98.0,
                "iowait": 0.0,
                "irq": 0.0,
                "nice": 0.0,
                "softirq": 0.0,
                "steal": 0.0,
                "system": 0.0,
                "user": 2.0,
            },
        }
    ).model_dump(exclude="timestamp")


def test_avg_memory(linux_handler: LinuxHandler):
    linux_handler.start_mem_measurement(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_mem_measurement()[:2]
    assert output.avg.model_dump(exclude="timestamp") == SystemMemory(
        mem=ExtendedMemoryInfo(
            total=32031624, used=6024669, free=18189335, shared=909004, buff_cache=7817620, available=24630431
        ),
        swap=MemoryInfo(total=2002940, used=0, free=2002940),
    ).model_dump(exclude="timestamp")


def test_max_cpu_core(linux_handler: LinuxHandler):
    linux_handler.start_cpu_measurement(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_cpu_measurement()[:3]
    assert output.highest_load_single_core(1)[0].model_dump(exclude="timestamp") == LinuxCpuUsageInfo(
        **{
            "cores": {"0": 3.0},
            "load": 3.0,
            "mode_usage": {
                "guest": 0.0,
                "guest_nice": 0.0,
                "idle": 97.0,
                "iowait": 0.0,
                "irq": 0.0,
                "nice": 0.0,
                "softirq": 0.0,
                "steal": 0.0,
                "system": 0.0,
                "user": 3.0,
            },
        }
    ).model_dump(exclude="timestamp")


def test_max_memory(linux_handler: LinuxHandler):
    linux_handler.start_mem_measurement(0.1)
    time.sleep(0.5)
    output = linux_handler.stop_mem_measurement()[:2]
    assert output.highest_memory_used(1)[0].model_dump(exclude="timestamp") == SystemMemory(
        mem=ExtendedMemoryInfo(
            total=32031624, used=6024670, free=18189334, shared=909004, buff_cache=7817620, available=24630430
        ),
        swap=MemoryInfo(total=2002940, used=0, free=2002940),
    ).model_dump(exclude="timestamp")


def test_highest_average_usage_proc_wise(linux_handler: LinuxHandler):
    linux_handler.start_mem_measurement_proc_wise(0.1)
    time.sleep(0.6)
    output = linux_handler.stop_mem_measurement_proc_wise()
    for i, model in enumerate(output):
        model.samples = model.samples[:3]
        output[i] = model
    top_2 = output.highest_average_mem_usage(2)
    values = [v.avg.mem_usage for v in top_2]
    assert values == [6700.0, 4316.0]


def test_highest_peak_usage_proc_wise(linux_handler: LinuxHandler):
    linux_handler.start_mem_measurement_proc_wise(0.1)
    time.sleep(0.6)
    output = linux_handler.stop_mem_measurement_proc_wise()
    for i, model in enumerate(output):
        model.samples = model.samples[:3]
        output[i] = model
    top_2 = output.highest_peak_mem_usage(2)
    values = [v.max_mem_usage.mem_usage for v in top_2]

    assert values == [8000.0, 6700.0]


def test_highest_average_load_proc_wise(linux_handler: LinuxHandler):
    linux_handler.start_cpu_measurement_proc_wise(0.1)
    time.sleep(0.8)
    output = linux_handler.stop_cpu_measurement_proc_wise()
    for i, model in enumerate(output):
        model.samples = model.samples[:3]
        output[i] = model
    top_2 = output.highest_average_cpu_load(2)
    values = [v.avg.cpu_load for v in top_2]
    assert values == [11.0, 6.333]


def test_highest_peak_load_proc_wise(linux_handler: LinuxHandler):
    linux_handler.start_cpu_measurement_proc_wise(0.1)
    time.sleep(0.6)
    output = linux_handler.stop_cpu_measurement_proc_wise()
    for i, model in enumerate(output):
        model.samples = model.samples[:3]
        output[i] = model
    top_2 = output.highest_peak_cpu_load(2)
    values = [v.max_cpu_load.cpu_load for v in top_2]
    assert values == [17.0, 12.0]


def test_filter_by_command(linux_handler: LinuxHandler):
    linux_handler.start_cpu_measurement_proc_wise(0.1)
    time.sleep(1)
    output = linux_handler.stop_cpu_measurement_proc_wise()
    assert any(["android.hardware" in process.command for process in output])
    assert all(
        [
            "android.hardware" not in process.command
            for process in output.filter(lambda m: "android.hardware" not in m.command)
        ]
    )


def test_sort_by_jsonpath(linux_handler: LinuxHandler):
    linux_handler.start_mem_measurement(0.1)
    time.sleep(1)
    output = linux_handler.stop_mem_measurement()
    prev_free = 0
    for model in output.sort_by_jsonpath("mem.free"):
        assert prev_free <= model.mem.free
        prev_free = model.mem.free


def test_yaml_property(linux_handler: LinuxHandler):
    result = linux_handler.get_mem_usage()
    assert (
        result.yaml.strip()
        == textwrap.dedent(
            f"""
            mem:
              available: 24630432
              buff_cache: 7817620
              free: 18189336
              shared: 909004
              total: 32031624
              used: 6024668
            swap:
              free: 2002940
              total: 2002940
              used: 0
            timestamp: '{result.timestamp.isoformat()}'
            """
        ).strip()
    )
