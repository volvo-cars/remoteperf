# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0
import uuid

from src.clients.base_client import BaseClient


class RemoteFsException(Exception):
    pass


class RemotePermissionException(RemoteFsException):
    pass


class RemoteFs:
    def __init__(self, client, tmp_directory="/tmp") -> None:
        self._client: BaseClient = client
        self._tmp_directory = tmp_directory

    def is_file(self, path):
        file_check = f'[ -f "{path}" ]'
        return self._conditional_check(file_check)

    def is_directory(self, path):
        file_check = f'[ -d "{path}" ]'
        return self._conditional_check(file_check)

    def exists(self, path):
        file_check = f'[ -e "{path}" ]'
        return self._conditional_check(file_check)

    def has_write_permissions(self, path):
        file_check = f'[ -w "{path}" ]'
        return self._conditional_check(file_check)

    def has_read_permissions(self, path):
        file_check = f'[ -r "{path}" ]'
        return self._conditional_check(file_check)

    def unlink(self, path, force=True):  # Force to prevents prompts
        if not self.exists(path):
            return
        if not self.has_write_permissions(path):
            raise RemotePermissionException(f"Insufficient permissions to remove {path}")
        if self.is_directory(path):
            out = self._client.run_command(f"rm -r{'f' if force else ''} {path} 2>&1")
        else:
            out = self._client.run_command(f"rm {'-f' if force else ''} {path} 2>&1")
        if self.exists(path):
            raise RemoteFsException(f"Could not remove directory: {out}")

    def _conditional_check(self, command):
        check_command = f'{command} && echo "True" || echo "False"'
        result = self._client.run_command(check_command)
        if "True" not in result and "False" not in result:
            raise RemoteFsException(f"Something went wrong during conditional check: {result}")
        return "True" in result

    class RemoteTemporaryDirectory:
        def __init__(self, remote_fs: "RemoteFs"):
            self.remote_fs = remote_fs
            self.path = None

        def __enter__(self):
            if not self.remote_fs._tmp_directory:
                raise RemoteFsException("No temporary directory supplied, cannot create remote tmpdir")
            unique_dir = f"{self.remote_fs._tmp_directory}/{uuid.uuid4()}"
            self.remote_fs._client.run_command(f"mkdir -p {unique_dir}")
            self.remote_fs._client.add_cleanup(unique_dir, "-rf")
            if not self.remote_fs.is_directory(unique_dir):
                raise RemoteFsException(f"Could not create directory: {unique_dir}")
            self.path = unique_dir
            return self.path

        def __exit__(self, *_):
            self.remote_fs._client.run_command(f"rm -rf {self.path}")

    def temporary_directory(self):
        return self.RemoteTemporaryDirectory(self)
