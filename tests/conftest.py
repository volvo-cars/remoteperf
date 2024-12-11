import fnmatch
import pathlib
import random
import subprocess
from tempfile import TemporaryDirectory
from typing import Optional

import pytest
import yaml

from src.clients.base_client import BaseClient
from src.clients.ssh_client import SSHClient
from src.handlers.linux_handler import LinuxHandler
from src.handlers.qnx_handler import QNXHandler


class MockClient(BaseClient):
    def __init__(self, queries, default=""):
        super().__init__()
        self._queries = queries
        self._default = default
        self._connected = False
        self._generators = {}
        self._cleanup = {}

    def __enter__(self):
        pass

    def __exit__(self):
        pass

    def run_command(self, request):
        if not (data := self._queries.get(request, self._default)):
            for key in self._queries.keys():
                if fnmatch.fnmatch(request, key):
                    data = self._queries.get(key, self._default)

        if isinstance(data, list):
            if request not in self._generators:
                self._generators[request] = (d for d in data)
            try:
                return next(self._generators[request])
            except StopIteration:
                self._generators[request] = (d for d in data)
                return next(self._generators[request])
        else:
            return data

    def pull_file(self, path: str, dest: str):
        return

    def push_file(self, path: str, dest: str):
        return

    def connect(self):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def add_cleanup(self, path: str, flags=None):
        self._cleanup[path] = flags

    @property
    def connected(self):
        pass


class SubprocessReplacement:
    def _run_command(self, command, *, retries=None, timeout=None):
        """Execute a shell command using subprocess and return the output as a string."""
        if not self._connected:
            raise Exception("Not connected. Please connect before running commands.")

        return subprocess.run(command, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    def _connect(self):
        self._connected = True

    def _disconnect(self):
        self._connected = False


class SubprocessLocalClient(BaseClient):
    def __init__(self):
        self._is_connected = True

    @property
    def connected(self):
        return self._is_connected

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.disconnect()

    def connect(self):
        self._is_connected = True

    def disconnect(self):
        self._is_connected = False

    def run_command(self, command: str, *_, **__) -> str:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        return result.stdout

    def pull_file(self, path: str, dest: str):
        subprocess.run(f"cp {path} {dest}", shell=True, check=True)

    def push_file(self, path: str, dest: str):
        subprocess.run(f"cp {path} {dest}", shell=True, check=True)

    def add_cleanup(self, path: str, flags: Optional[str]) -> None:
        pass


@pytest.fixture
def extractor_data():
    with (pathlib.Path(__file__).parent / "data" / "extractor_data.yaml").open() as file:
        data = yaml.safe_load(file)
    return data


@pytest.fixture
def mock_client():
    with (pathlib.Path(__file__).parent / "data" / "valid_handler_data.yaml").open() as file:
        queries = yaml.safe_load(file)
    return MockClient(queries)


@pytest.fixture
def subprocess_client():
    return SubprocessLocalClient()


@pytest.fixture
def linux_handler(mock_client):
    return LinuxHandler(client=mock_client)


@pytest.fixture
def qnx_handler(mock_client):
    return QNXHandler(client=mock_client)


@pytest.fixture
def broken_mock_client():
    with (pathlib.Path(__file__).parent / "data" / "invalid_handler_data.yaml").open() as file:
        queries = yaml.safe_load(file)
    return MockClient(queries)


@pytest.fixture
def tmp_data_file():
    with TemporaryDirectory() as tdir:
        random.seed(42)
        data = ["".join(random.choices('abcdef-.,_ +1234567890!"#¤%&/()=?', k=1000)) for _ in range(10)]
        test_file = pathlib.Path(tdir) / "file"
        with open(test_file, "w", encoding="utf-8") as file:
            file.writelines(data)
        yield test_file


@pytest.fixture
def tmp_data_file_xl():
    with TemporaryDirectory() as tdir:
        random.seed(42)
        data = ["".join(random.choices('abcdef-.,_ +1234567890!"#¤%&/()=?', k=1000)) for _ in range(1000)]
        test_file = pathlib.Path(tdir) / "file"
        with open(test_file, "w", encoding="utf-8") as file:
            file.writelines(data)
        yield test_file
