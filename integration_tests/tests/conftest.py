import pathlib
import random
import subprocess
import time
from contextlib import contextmanager
from tempfile import TemporaryDirectory

import pytest

from src.clients.adb_client import ADBClient
from src.clients.ssh_client import SSHClient


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


@singleton
class ConfiguredAdbClient:
    def __init__(self):
        self.client = ADBClient("emulator-5554", retries=20)


@pytest.fixture(scope="session")
def ssh_client():
    client = SSHClient(host="127.0.0.1", username="root", password="root", retries=10)
    client.connect()
    yield client
    client.disconnect()


@pytest.fixture(scope="session")
def adb_client():
    client = ConfiguredAdbClient().client
    client.connect()
    yield client
    client.disconnect()


@pytest.fixture
def tdir():
    with TemporaryDirectory() as tdir:
        yield pathlib.Path(tdir)


@pytest.fixture
def random_name():
    return "".join(random.choices("abcdef1234567890", k=20))


@pytest.fixture
def spawned_processes():
    current_process_count = int(subprocess.check_output(["bash", "-c", "ps -aux | wc -l"]).strip())
    if current_process_count < 100:
        subprocess.Popen(["bash", "-c", "for i in {1..100}; do sleep 600 & done"])
    time.sleep(1)


@contextmanager
def override_client_config(ssh_client, retries=None, timeout=None):
    # Store the original values
    original_retries = ssh_client._retries
    original_timeout = ssh_client._timeout

    # Set the new values if provided
    if retries is not None:
        ssh_client._retries = retries
    if timeout is not None:
        ssh_client._timeout = timeout

    try:
        # Yield control back to the calling function
        yield ssh_client
    finally:
        # Restore the original values
        ssh_client._retries = original_retries
        ssh_client._timeout = original_timeout
