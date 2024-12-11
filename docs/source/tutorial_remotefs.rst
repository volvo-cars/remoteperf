Tutorial (RemoteFS)
===================

RemoteFs Utils
--------------

Remoteperf includes some utilities for managing remote systems, such as a remote filesystem tool, which can be used
both independently and as a component of each handler.

Example 1: Precense checks
~~~~~~~~~~~~~~~~~~~~~~~~~~

To check wheteher a file exists, the following functions can be used:

.. code-block:: python

    from src.clients import SSHClient
    from src.handlers import QNXHandler

    with SSHClient("127.0.0.1", port=22, username="root", password="root") as instance:
        handler = QNXHandler(instance, log_path="/tmp/core")
        handler.fs_utils.exists("/path/to/anything")
        handler.fs_utils.is_file("/path/to/file")
        handler.fs_utils.is_dir("/path/to/directory")

Example 2: Remove file
~~~~~~~~~~~~~~~~~~~~~~

In addition, it also allows for removal of files and directory:

.. code-block:: python

    from src.clients import SSHClient
    from src.utils.fs_utils import RemoteFS

    with SSHClient("127.0.0.1", port=22, username="root", password="root") as instance:
        fs = RemoteFS(instance)
        fs.unlink("/path/to/anything")


This will throw an exception if it fails to remove the given path or if the path does not exist

Example 3: Temporary Directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is also support for remote temporary directories:

.. code-block:: python

    from src.clients import SSHClient
    from src.handlers import LinuxHandler

    with SSHClient("127.0.0.1", port=22, username="root", password="root") as instance:
        handler = LinuxHandler(instance)
        with handler.fs_utils.temporary_directory() as tdir:
        serial_client.push_file("README.md", tdir)

These are deleted upon context manager exit using an rm -rf call
