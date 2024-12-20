Tutorial
========

Installation
------------

To install the package, use pip:

.. code-block:: shell

    pip install remoteperf

Usage Examples
--------------

Here are a few examples of how to use remoteperf:

Example 1: Basic Linux Usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To communicate with a remote host, a handler is needed to specify which operating system the target is running and a client is needed to specify protocol and credentials:

.. code-block:: python

    from remoteperf.clients import SSHClient
    from remoteperf.handlers import LinuxHandler

    with SSHClient("127.0.0.1", port=22, username="root", password="root") as instance:
        handler = LinuxHandler(instance)
        usage = handler.get_cpu_usage()
        print(usage)

Example output:

.. code-block:: python

    LinuxCpuUsageInfo(
        timestamp=datetime.datetime(2024, 7, 9, 7, 45, 5, 827697),
        load=41.58,
        mode_usage=LinuxCpuModeUsageInfo(
            user=36.96,
            nice=0.0,
            system=4.62,
            idle=58.42,
            iowait=0.0,
            irq=0.0,
            softirq=0.0,
            steal=0.0,
            guest=0.0,
            guest_nice=0.0
        ),
        cores={
            '0': 38.46,
            '1': 36.0,
            '2': 36.0,
            '3': 50.0,
            '4': 48.0,
            '5': 64.0,
            '6': 44.0,
            '7': 38.46,
            '8': 37.5,
            '9': 36.0,
            '10': 40.74,
            '11': 34.62
        }
    )

Example 1.1: YAML
"""""""""""""""""

All returned objects can be serialized to YAML through the built-in .yaml

.. code-block:: python

    print(usage.yaml)


.. code-block:: yaml

    cores:
    '0': 38.46
    '1': 36.0
    '10': 40.74
    '11': 34.62
    '2': 36.0
    '3': 50.0
    '4': 48.0
    '5': 64.0
    '6': 44.0
    '7': 38.46
    '8': 37.5
    '9': 36.0
    load: 41.58
    mode_usage:
      guest: 0.0
      guest_nice: 0.0
      idle: 58.42
      iowait: 0.0
      irq: 0.0
      nice: 0.0
      softirq: 0.0
      steal: 0.0
      system: 4.62
      user: 36.96
      timestamp: '2024-07-09T07:45:05.827697'

Example 1.2: SSH Jump-Posting
"""""""""""""""""""""""""""""
The SSH client specifically also supports jump-posting:

.. code-block:: python

    from remoteperf.clients import SSHClient
    from remoteperf.handlers import LinuxHandler

    with SSHClient("127.0.0.1", port=22, username="root", password="root") as jump_client1:
        with SSHClient("host2", port=22, username="root", password="root", jump_client=jump_client1) as jump_client2:
            with SSHClient("host3", port=22, username="root", password="root", jump_client=jump_client2) as client:
                handler = LinuxHandler(client)
                usage = handler.get_cpu_usage()


Example 2: Basic Android Usage:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from remoteperf.clients import ADBClient
    from remoteperf.handlers import AndroidHandler

    with ADBClient(device_id=...) as instance:
        handler = AndroidHandler(instance)
        boot_time = handler.get_boot_time()
        print(boot_time)

Example output:

.. code-block:: python

    BootTimeInfo(
        timestamp=datetime.datetime(1991, 9, 17, 17, 29, 55, 0),
        total=121
    )

Example 3: Basic QNX Usage:
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from remoteperf.clients import SSHClient
    from remoteperf.handlers import QNXHandler

    with SSHClient("127.0.0.1", port=22, username="root", password="root")  as instance:
        handler = QNXHandler(instance)
        usage = handler.get_mem_usage()
        print(usage)

Example output:

.. code-block:: python

    SystemMemory(
    timestamp=datetime.datetime(2024, 5, 16, 11, 27, 12, 795350),
    MemoryInfo(
        total=12345,
        used=12000,
        free=345
        )
    swap=None
    )

Example 4: Continuous background measurement:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from remoteperf.clients import SSHClient
    from remoteperf.handlers import LinuxHandler

    with SSHClient("127.0.0.1", port=22, username="root", password="root") as instance:
        handler = LinuxHandler(instance)
        handler.start_cpu_measurement(0.1)
        time.sleep(0.5)
        result = handler.stop_cpu_measurement()

The result is then a list of handler-specific cpu information models, with timestamps at intervals closely matching the input to the start function

Example result:

.. code-block:: python

    CpuList([
        LinuxCpuUsageInfo(timestamp=datetime.datetime(2024, 5, 24, 11, 19, 38, 28535), load=38.02, mode_usage=LinuxCpuModeUsageInfo(user=33.88, nice=0.0, system=4.13, idle=61.98, iowait=0.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0), cores={"cpu0":38.02}),
        LinuxCpuUsageInfo(timestamp=datetime.datetime(2024, 5, 24, 11, 19, 38, 129524), load=18.80, mode_usage=LinuxCpuModeUsageInfo(user=14.53, nice=0.0, system=3.42, idle=81.20, iowait=0.0, irq=0.0, softirq=0.85, steal=0.0, guest=0.0, guest_nice=0.0), cores={"cpu0":18.80}),
        LinuxCpuUsageInfo(timestamp=datetime.datetime(2024, 5, 24, 11, 19, 38, 229259), load=10.08, mode_usage=LinuxCpuModeUsageInfo(user=5.88, nice=0.0, system=4.20, idle=89.92, iowait=0.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0), cores={"cpu0":10.08}),
        LinuxCpuUsageInfo(timestamp=datetime.datetime(2024, 5, 24, 11, 19, 38, 328250), load=10.26, mode_usage=LinuxCpuModeUsageInfo(user=6.84, nice=0.0, system=3.42, idle=89.74, iowait=0.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0), cores={"cpu0":10.26}),
    ])

This returs a list wrapper called CpuList which also allows for some mathematical operations:

.. code-block:: python

    print(result.max_load_single_core)
    >>> Item(core='cpu0', load=38.02, model=LinuxCpuUsageInfo(timestamp=datetime.datetime(2024, 5, 24, 11, 19, 38, 28535), load=38.02, cores={'cpu0': 38.02}, mode_usage=LinuxCpuModeUsageInfo(user=33.88, nice=0.0, system=4.13, idle=61.98, iowait=0.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0)))

    print(result.avg)
    >>> LinuxCpuUsageInfo(timestamp=datetime.datetime(2024, 9, 2, 15, 24, 20, 590217), load=19.29, cores={'cpu0': 19.29} mode_usage=LinuxCpuModeUsageInfo(user=15.28, nice=0.0, system=3.79, idle=80.71, iowait=0.0, irq=0.0, softirq=0.21, steal=0.0, guest=0.0, guest_nice=0.0))

Example 5: Processwise Resource Measurement:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from remoteperf.clients import SSHClient
    from remoteperf.handlers import LinuxHandler

    with SSHClient("127.0.0.1", port=22, username="root", password="root") as client:
        handler = LinuxHandler(client)
        result1 = handler.handler.get_mem_usage_proc_wise()
        result2 = handler.handler.get_cpu_usage_proc_wise()

The result is then a list of handler-specific cpu information models.
Note: for Linux and Android, memory information comes for free with a cpu measurement.

Example result (for a docker container running only sshd):

.. code-block:: python

    result1 = [
        ProcessInfo(pid=1 name='sshd' command='sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups\x00' start_time='2376762' samples=[BaseMemorySample(timestamp=datetime.datetime(2024, 6, 27, 14, 1, 1, 808775), mem_usage=7680.0)]),
        ProcessInfo(pid=47 name='sshd' command='sshd: root@notty\x00\x00' start_time='2420062' samples=[BaseMemorySample(timestamp=datetime.datetime(2024, 6, 27, 14, 1, 1, 808775), mem_usage=8204.0)])
    ]
    result2 = [
        ProcessInfo(pid=1 name='sshd' command='sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups\x00' start_time='2376762' samples=[LinuxResourceSample(timestamp=datetime.datetime(2024, 6, 27, 14, 1, 1, 808775), cpu_load=0.01 ,mem_usage=7680.0)]),
        ProcessInfo(pid=47 name='sshd' command='sshd: root@notty\x00\x00' start_time='2420062' samples=[LinuxResourceSample(timestamp=datetime.datetime(2024, 6, 27, 14, 1, 1, 808775), cpu_load=0.10, mem_usage=8204.0)])
    ]

Example 6: Continuous Processwise Resource Measurement:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from remoteperf.clients import SSHClient
    from remoteperf.handlers import LinuxHandler

    with SSHClient("127.0.0.1", port=22, username="root", password="root") as client:
        handler = LinuxHandler(client)
        handler.start_cpu_measurement_proc_wise(0.2)
        time.sleep(1)
        result = handler.stop_cpu_measurement_proc_wise()

The result is then a list of handler-specific cpu information models.
Note: for Linux and Android, memory information comes for free with a cpu measurement.

Example result (for a docker container running only sshd):

.. code-block:: python

    [
        ProcessInfo(pid=1 name='sshd' command='sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups' start_time='758567' samples=[LinuxResourceSample(timestamp=datetime.datetime(2024, 8, 29, 15, 55, 57, 465394), mem_usage=7040.0, cpu_load=0.0), LinuxResourceSample(timestamp=datetime.datetime(2024, 8, 29, 15, 55, 58, 760324), mem_usage=7040.0, cpu_load=0.0), LinuxResourceSample(timestamp=datetime.datetime(2024, 8, 29, 15, 55, 59, 459172), mem_usage=7040.0, cpu_load=0.0)]),
        ProcessInfo(pid=2769 name='sshd' command='sshd: root@notty' start_time='2507319' samples=[LinuxResourceSample(timestamp=datetime.datetime(2024, 8, 29, 15, 55, 57, 465394), mem_usage=8116.0, cpu_load=0.0), LinuxResourceSample(timestamp=datetime.datetime(2024, 8, 29, 15, 55, 58, 760324), mem_usage=8116.0, cpu_load=0.08), LinuxResourceSample(timestamp=datetime.datetime(2024, 8, 29, 15, 55, 59, 459172), mem_usage=8116.0, cpu_load=0.0)])
    ]



Example 7: Disk Info and IO:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

    from remoteperf.clients import SSHClient
    from remoteperf.handlers import LinuxHandler

    with SSHClient("127.0.0.1", port=22, username="root", password="root") as client:
        handler = LinuxHandler(client)
        handler.get_diskinfo()
        handler.get_diskio()
        handler.get_diskio_proc_wise()

The result is then a list of handler-specific disk information models. Info pulls the current available storage, usage pulls the current io on the disks and usage_proc_wise pulls pulls read and write access by each process.
All these measures can also be pulled continuously.

.. code-block:: python

    handler.start_disk_info_measurement(0.1)
    time.sleep(1)
    result = handler.stop_disk_info_measurement()

    handler.start_diskio_measurement(0.1)
    time.sleep(1)
    result = handler.stop_diskio_measurement()

    handler.start_diskio_measurement_proc_wise(0.1)
    time.sleep(1)
    result = handler.stop_diskio_measurement_proc_wise()


Example 8: Network Usage Measurements, both individual and continuous:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Network measurements are setup similar to other KPIs. They can be pulled as a single measurement or continuously.
For a single measurement, the following code can be used:

 .. code-block:: python

    from remoteperf.clients import SSHClient
    from remoteperf.handlers import LinuxHandler

    with SSHClient("127.0.0.1", port=22, username="root", password="root") as client:
        handler = LinuxHandler(client)
        current_network_usage = handler.get_network_usage()
        total_network_usage = handler.get_network_usage_total()

The result is then a list of handler-specific network information models. Current network usage is the current usage of the network interfaces, while total network usage is the total usage since the last reboot.

The following is showing a continuous measurement:

.. code-block:: python

    from remoteperf.clients import SSHClient
    from remoteperf.handlers import LinuxHandler

    with SSHClient("127.0.0.1", port=22, username="root", password="root") as client:
        handler = LinuxHandler(client)
        handler.start_net_interface_measurement(0.1)
        time.sleep(1)
        result = handler.stop_net_interface_measurement()

The result is then a list of handler-specific network information models. It is the same as the single measurement, except that it is a list of measurement.
