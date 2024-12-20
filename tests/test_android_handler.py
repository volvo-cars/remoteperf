import pytest

from remoteperf.handlers.android_handler import (
    AndroidHandler,
    AndroidHandlerException,
    MissingAndroidCapabilityException,
)


@pytest.fixture
def broken_android_handler(broken_mock_client):
    return AndroidHandler(client=broken_mock_client)


@pytest.fixture
def android_handler(mock_client):
    return AndroidHandler(client=mock_client)


def test_boot_total(android_handler):
    output = android_handler.get_boot_time()
    assert output.total == 121


def test_exception_boot(broken_android_handler):
    with pytest.raises(AndroidHandlerException):
        broken_android_handler.get_boot_time()


def test_boot_time_exception(broken_android_handler):
    with pytest.raises(MissingAndroidCapabilityException):
        broken_android_handler.get_boot_time()
