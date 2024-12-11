from unittest.mock import patch

import pytest
from paramiko import AuthenticationException, SSHException

from src.clients.ssh_client import SSHClient, SSHClientException


@pytest.fixture
def ssh_client():
    return SSHClient("host", port=22, username="username", password="password")


def test_connect(ssh_client):
    with patch("paramiko.SSHClient") as mock_ssh:
        mock_ssh.return_value = mock_ssh
        mock_ssh.connect.return_value = None
        ssh_client.connect()
        mock_ssh.connect.assert_called_once_with(
            "host", port=22, username="username", password="password", timeout=10, auth_timeout=10, sock=None
        )


def test_connect_authentification_error(ssh_client):
    with patch("paramiko.SSHClient") as mock_ssh:
        mock_ssh.return_value = mock_ssh
        mock_ssh.connect.side_effect = AuthenticationException
        with pytest.raises(SSHClientException):
            ssh_client.connect()


def test_connect_ssh_exception(ssh_client):
    with patch("paramiko.SSHClient") as mock_ssh:
        mock_ssh.return_value = mock_ssh
        mock_ssh.connect.side_effect = SSHException
        with pytest.raises(SSHClientException):
            ssh_client.connect()


def test_disconnect(ssh_client):
    with patch("paramiko.SSHClient") as mock_ssh:
        mock_ssh.return_value = mock_ssh
        mock_ssh.connect.return_value = None
        ssh_client.connect()
        assert ssh_client._client is not None
        ssh_client.disconnect()
        assert ssh_client._client is None
        mock_ssh.close.assert_called_once()


def test_disconnect_no_connection(ssh_client):
    with patch("paramiko.SSHClient") as mock_ssh:
        mock_ssh.return_value = mock_ssh
        with pytest.raises(SSHClientException):
            ssh_client.disconnect()
