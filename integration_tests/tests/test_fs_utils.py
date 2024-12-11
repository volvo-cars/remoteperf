from src.handlers.linux_handler import LinuxHandler


def test_remove_file(ssh_client, random_name):
    handler = LinuxHandler(ssh_client)
    tfile = f"/tmp/{random_name}"
    ssh_client.run_command(f"touch {tfile}")
    handler.fs_utils.unlink(tfile)


def test_remove_directory(ssh_client, random_name):
    handler = LinuxHandler(ssh_client)
    tdir = f"/tmp/{random_name}"
    ssh_client.run_command(f"mkdir {tdir}")
    handler.fs_utils.unlink(tdir)
