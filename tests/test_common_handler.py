from tempfile import TemporaryDirectory

import pytest

from src.handlers.linux_handler import LinuxHandler


@pytest.fixture
def subprocess_linux_handler(subprocess_client):
    subprocess_client.connect()
    return LinuxHandler(client=subprocess_client)


def test_exists(subprocess_linux_handler):
    assert subprocess_linux_handler.fs_utils.exists("/dev")


def test_does_not_exists(subprocess_linux_handler):
    assert not subprocess_linux_handler.fs_utils.exists("/will_to_live")


def test_is_directory(subprocess_linux_handler):
    with TemporaryDirectory() as tdir:
        assert subprocess_linux_handler.fs_utils.is_directory(tdir)


def test_is_not_directory(subprocess_linux_handler, tmp_data_file):
    assert not subprocess_linux_handler.fs_utils.is_directory(tmp_data_file)


def test_is_file(subprocess_linux_handler, tmp_data_file):
    assert subprocess_linux_handler.fs_utils.is_file(tmp_data_file)


def test_is_not_file(subprocess_linux_handler):
    assert not subprocess_linux_handler.fs_utils.is_file("/dev")
