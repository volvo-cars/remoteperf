# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import logging
import time
from contextlib import contextmanager
from typing import Any, Generator

import paramiko

from src.clients.lock_client import LockClient, LockClientException


class SSHClientException(LockClientException):
    pass


# pylint: disable=R0917
class SSHClient(LockClient):
    def __init__(
        self,
        host,
        *,
        port=22,
        username=None,
        password=None,
        timeout=10,
        retries=2,
        jump_client: "SSHClient" = None,
        host_key_policy=None,
    ):
        super().__init__()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._retries = retries if retries >= 0 else 0
        self._client: paramiko.SSHClient = None
        self._jump_client = jump_client
        self._timeout = timeout
        self._exception = SSHClientException
        self._host_key_policy = host_key_policy or paramiko.AutoAddPolicy

    @property
    def connected(self):
        return self._client is not None

    def _connect(self) -> None:
        if self.connected:
            return
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(self._host_key_policy)
        try:
            client.connect(
                self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                timeout=self._timeout,
                sock=self.socket,
                auth_timeout=self._timeout,
            )
        except paramiko.AuthenticationException as e:
            message = "Authentication failed, please verify your credentials."
            raise SSHClientException(message) from e
        except Exception as e:
            message = f"Could not establish SSH connection: {e}"
            raise SSHClientException(message) from e
        self._client = client
        self._logger.debug("Connected to the server successfully.")

    @property
    def socket(self) -> paramiko.Channel:
        if not self._jump_client:
            if not self.connected or self._client.get_transport() is None:
                return None
            return self._client.get_transport().sock
        try:
            socket = self._jump_client._client.get_transport().open_channel(
                "direct-tcpip",
                (self._host, self._port),
                (self._jump_client._host, self._jump_client._port),
            )
        except paramiko.SSHException as e:
            raise SSHClientException("Failed to open channel on jump host") from e
        return socket

    def _disconnect(self) -> None:
        if not self._client:
            raise SSHClientException(
                "You cannot close a connection that does not exist"
            )
        try:
            self._client.close()
        finally:
            self._client = None

    def _run_command(self, command, *, retries=None, timeout=None, **_):
        _retries = max(retries or self._retries, 0)
        _timeout = timeout or self._timeout
        error = None
        if not self.connected:
            raise self._exception("Not Connected")
        for attempt in range(1, _retries + 2):
            if attempt > 1:
                if isinstance(error, TimeoutError):
                    self._logger.error(f"Timeout received, retrying {attempt}.")
                else:
                    self._logger.error(
                        f"Error occured, retrying {attempt}, (cause: {error})."
                    )
            try:
                with self._create_session() as session:
                    session.exec_command(command)
                    output: str = self._read_and_wait_for_exit_status(session, _timeout)
                    return output.replace("\x00", "")
            except Exception as e:  # Cannot guarantee paramiko errors exclusively: pylint: disable=W0718
                error = e
                self._recover_connection()
        raise SSHClientException(
            f"Timeout exceeded when reading output after {_retries+1} attempts"
        ) from error

    @contextmanager
    def _create_session(self) -> Generator[paramiko.Channel, Any, Any]:
        transport = self._client.get_transport()
        session = transport.open_session()
        try:
            yield session
        finally:
            session.close()

    def _read_and_wait_for_exit_status(self, session: paramiko.Channel, timeout):
        t0 = time.time()
        output = ""
        while time.time() < t0 + timeout:
            output += self._recv_all(session)
            session.status_event.wait(timeout / 10)
            if session.exit_status_ready():
                output += self._recv_all(session)
                if (
                    not session.exit_status_ready()
                    or not self._transport_alive(session.get_transport())
                    or not session.active
                ):
                    raise SSHClientException(
                        f"Error occured after final read. Partial output: {output}"
                    )
                return output
        raise TimeoutError(
            f"Timeout occured reading exit status. Partial output:{output}"
        )

    def _recv_all(self, session: paramiko.Channel) -> str:
        out = ""
        while session.recv_ready():
            out += session.recv(65536).decode("utf-8")
            # We send a keep-alive message to prevent race conditions
            session.get_transport().global_request("keepalive@volvocars.com", wait=True)
        return out

    def _pull_file(self, path: str, dest: str) -> None:
        error = None
        for attempt in range(1, max(self._retries, 0) + 2):
            try:
                with self._client.open_sftp() as sftp:
                    return sftp.get(path, dest)
            except IOError as e:
                raise SSHClientException(
                    f"Pulled file did not match remote: {e}"
                ) from e
            except Exception as e:  # Cannot guarantee paramiko errors exclusively: pylint: disable=W0718
                error = e
                self._recover_connection()
        raise SSHClientException(
            f"Failed to pull file: ({error}) after {attempt} attempt(s)"
        ) from error

    def _push_file(self, path: str, dest: str) -> None:
        error = None
        for attempt in range(1, max(self._retries, 0) + 2):
            try:
                with self._client.open_sftp() as sftp:
                    return sftp.put(path, dest, confirm=True)
            except IOError as e:
                raise SSHClientException(
                    f"Pulled file did not match remote: {e}"
                ) from e
            except Exception as e:  # Cannot guarantee paramiko errors exclusively: pylint: disable=W0718
                error = e
                self._recover_connection()
        raise SSHClientException(
            f"Failed to pull file: ({error}) after {attempt} attempt(s)"
        ) from error

    def _recover_connection(self) -> bool:
        if not self.connected:
            raise SSHClientException("Cannot recover connection, not connected")
        jump_reconnected = False
        if self._jump_client is not None:
            jump_reconnected = (
                self._jump_client._recover_connection()  # pylint: disable=W0212
            )  # Needed for recursive check
        if not self._transport_alive(self._client.get_transport()) or jump_reconnected:
            self._disconnect()
            self._connect()
            return True
        return False

    @classmethod
    def _transport_alive(cls, transport: paramiko.Transport):
        return transport is not None and transport.is_alive() and transport.is_active()
