Tutorial (Math)
===============

Continuous Measurement Math Utils
---------------------------------

Remoteperf is not a mathematical library nor does it intend to be, so for more complex and/or
large scale computations we advice you to export data first and and do them in a more suitable
environment. However, it does support a few basic operations on all objects returned by
all continuous measurement functions, and if you feel some might be missing you're more than
welcome to contribute by extending the existing list wrappers in  ``src/models/super.py``.

Example 1: Highest average load/usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from src.clients import ADBClient
    from src.handlers import AndroidHandler

    with ADBClient(device_id="emulator-5554") as instance:
        handler = AndroidHandler(instance)
        handler.start_cpu_measurement(0.5)
        time.sleep(3)
        data = handler.stop_cpu_measurement()
        print(data.highest_load_single_core(1).yaml)

.. code-block:: yaml

    - cores:
        '0': 2.13
        '1': 100.0
        '2': 2.08
        '3': 100.0
        '4': 2.13
        '5': 4.17
      load: 34.86
      mode_usage:
        guest: 0.0
        guest_nice: 0.0
        idle: 65.14
        iowait: 0.0
        irq: 0.0
        nice: 0.0
        softirq: 0.0
        steal: 0.35
        system: 10.21
        user: 24.3
      timestamp: '2024-09-11T14:29:15.482848'

.. code-block:: python

        handler.start_mem_measurement(0.5)
        time.sleep(3)
        data = handler.stop_mem_measurement()
        print(data.highest_memory_used(1).yaml)

.. code-block:: yaml

    - mem:
        available: 851072
        buff_cache: 855100
        free: 260616
        shared: 13904
        total: 2020656
        used: 904940
      swap:
        free: 815612
        total: 1515488
        used: 699876
      timestamp: '2024-09-11T14:31:22.146876'

Example 2: Highest average priocess-wise load/usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from src.clients import ADBClient
    from src.handlers import AndroidHandler

    with ADBClient(device_id="emulator-5554") as instance:
        handler = AndroidHandler(instance)
        handler.start_cpu_measurement_proc_wise(0.5)
        time.sleep(3)
        data = handler.stop_cpu_measurement_proc_wise()
        print(data.filter(lambda m: "kworker" not in m.command).highest_average_cpu_load(3).yaml)

.. code-block:: yaml

    - command: com.arachnoid.sshelper
      name: chnoid.sshelper
      pid: 6637
      samples:
      - cpu_load: 33.58
        mem_usage: 70932.0
        timestamp: '2024-09-11T14:32:32.019540'
      - cpu_load: 32.79
        mem_usage: 70932.0
        timestamp: '2024-09-11T14:32:32.532655'
      - cpu_load: 33.1
        mem_usage: 70932.0
        timestamp: '2024-09-11T14:32:33.016975'
      - cpu_load: 33.23
        mem_usage: 70932.0
        timestamp: '2024-09-11T14:32:33.545528'
      - cpu_load: 32.99
        mem_usage: 70932.0
        timestamp: '2024-09-11T14:32:34.038496'
      - cpu_load: 33.22
        mem_usage: 70932.0
        timestamp: '2024-09-11T14:32:34.540022'
      start_time: '35400'
    - command: /apex/com.android.adbd/bin/adbd--root_seclabel=u:r:su:s0
      name: adbd
      pid: 7418
      samples:
      - cpu_load: 0.36
        mem_usage: 10076.0
        timestamp: '2024-09-11T14:32:32.019540'
      - cpu_load: 0.65
        mem_usage: 10076.0
        timestamp: '2024-09-11T14:32:32.532655'
      - cpu_load: 0.34
        mem_usage: 10076.0
        timestamp: '2024-09-11T14:32:33.016975'
      - cpu_load: 0.94
        mem_usage: 10076.0
        timestamp: '2024-09-11T14:32:33.545528'
      - cpu_load: 1.02
        mem_usage: 10076.0
        timestamp: '2024-09-11T14:32:34.038496'
      - cpu_load: 0.66
        mem_usage: 10076.0
        timestamp: '2024-09-11T14:32:34.540022'
      start_time: '179390'
    - command: -/system/bin/sh
      name: sh
      pid: 25276
      samples:
      - cpu_load: 0.36
        mem_usage: 3612.0
        timestamp: '2024-09-11T14:32:32.019540'
      - cpu_load: 0.0
        mem_usage: 3612.0
        timestamp: '2024-09-11T14:32:32.532655'
      - cpu_load: 0.34
        mem_usage: 3612.0
        timestamp: '2024-09-11T14:32:33.016975'
      - cpu_load: 0.31
        mem_usage: 3612.0
        timestamp: '2024-09-11T14:32:33.545528'
      - cpu_load: 0.0
        mem_usage: 3612.0
        timestamp: '2024-09-11T14:32:34.038496'
      - cpu_load: 0.33
        mem_usage: 3612.0
        timestamp: '2024-09-11T14:32:34.540022'
      start_time: '6695195'

.. code-block:: python

    print(data.filter(lambda m: "kworker" not in m.command).highest_average_mem_usage(3).yaml)

.. code-block:: yaml

    - command: com.google.android.googlequicksearchbox:search
      name: earchbox:search
      pid: 20693
      samples:
      - cpu_load: 0.0
        mem_usage: 177932.0
        timestamp: '2024-09-11T14:34:39.356575'
      - cpu_load: 0.0
        mem_usage: 177932.0
        timestamp: '2024-09-11T14:34:39.850893'
      - cpu_load: 0.0
        mem_usage: 177932.0
        timestamp: '2024-09-11T14:34:40.359544'
      - cpu_load: 0.0
        mem_usage: 177932.0
        timestamp: '2024-09-11T14:34:40.849346'
      - cpu_load: 0.0
        mem_usage: 177932.0
        timestamp: '2024-09-11T14:34:41.333055'
      - cpu_load: 0.0
        mem_usage: 177932.0
        timestamp: '2024-09-11T14:34:41.838797'
      start_time: '4533992'
    - command: system_server
      name: system_server
      pid: 624
      samples:
      - cpu_load: 0.0
        mem_usage: 176472.0
        timestamp: '2024-09-11T14:34:39.356575'
      - cpu_load: 0.0
        mem_usage: 176472.0
        timestamp: '2024-09-11T14:34:39.850893'
      - cpu_load: 0.0
        mem_usage: 176472.0
        timestamp: '2024-09-11T14:34:40.359544'
      - cpu_load: 0.0
        mem_usage: 176472.0
        timestamp: '2024-09-11T14:34:40.849346'
      - cpu_load: 0.0
        mem_usage: 176472.0
        timestamp: '2024-09-11T14:34:41.333055'
      - cpu_load: 0.0
        mem_usage: 176472.0
        timestamp: '2024-09-11T14:34:41.838797'
      start_time: '2913'
    - command: com.google.android.gms.persistent
      name: .gms.persistent
      pid: 5662
      samples:
      - cpu_load: 0.0
        mem_usage: 156048.0
        timestamp: '2024-09-11T14:34:39.356575'
      - cpu_load: 0.0
        mem_usage: 156048.0
        timestamp: '2024-09-11T14:34:39.850893'
      - cpu_load: 0.0
        mem_usage: 156048.0
        timestamp: '2024-09-11T14:34:40.359544'
      - cpu_load: 0.0
        mem_usage: 156048.0
        timestamp: '2024-09-11T14:34:40.849346'
      - cpu_load: 0.0
        mem_usage: 156048.0
        timestamp: '2024-09-11T14:34:41.333055'
      - cpu_load: 0.0
        mem_usage: 156048.0
        timestamp: '2024-09-11T14:34:41.838797'
      start_time: '18157'

Example 3: Advanced Usage
~~~~~~~~~~~~~~~~~~~~~~~~~

Sorting, filtering, and querying can be combined in an advanced manner as such:

.. code-block:: python

    from src.clients import ADBClient
    from src.handlers import AndroidHandler

    with ADBClient(device_id="emulator-5554") as instance:
        handler = AndroidHandler(instance)
        handler.start_cpu_measurement_proc_wise(0.5)
        time.sleep(3)
        data = handler.stop_cpu_measurement_proc_wise()
        print(
            data.filter(lambda m: "kworker" not in m.command)
            .filter(lambda m: max(s.mem_usage for s in m.samples) > 10000)
            .highest_average_cpu_load(5)
            .sort_by_jsonpath("pid", reverse=True)[:3]
            .yaml
        )

.. code-block:: yaml

    - command: /apex/com.android.adbd/bin/adbd--root_seclabel=u:r:su:s0
      name: adbd
      pid: 7418
      samples:
      - cpu_load: 0.7
        mem_usage: 12360.0
        timestamp: '2024-09-11T14:51:07.690535'
      - cpu_load: 0.35
        mem_usage: 12360.0
        timestamp: '2024-09-11T14:51:08.163705'
      - cpu_load: 0.33
        mem_usage: 12360.0
        timestamp: '2024-09-11T14:51:08.670101'
      - cpu_load: 0.33
        mem_usage: 12360.0
        timestamp: '2024-09-11T14:51:09.161167'
      - cpu_load: 0.33
        mem_usage: 12360.0
        timestamp: '2024-09-11T14:51:09.671461'
      - cpu_load: 0.64
        mem_usage: 12360.0
        timestamp: '2024-09-11T14:51:10.189094'
      start_time: '179390'
    - command: com.arachnoid.sshelper
      name: chnoid.sshelper
      pid: 6637
      samples:
      - cpu_load: 33.1
        mem_usage: 71196.0
        timestamp: '2024-09-11T14:51:07.690535'
      - cpu_load: 33.68
        mem_usage: 71196.0
        timestamp: '2024-09-11T14:51:08.163705'
      - cpu_load: 33.44
        mem_usage: 71196.0
        timestamp: '2024-09-11T14:51:08.670101'
      - cpu_load: 32.44
        mem_usage: 71196.0
        timestamp: '2024-09-11T14:51:09.161167'
      - cpu_load: 33.01
        mem_usage: 71196.0
        timestamp: '2024-09-11T14:51:09.671461'
      - cpu_load: 33.23
        mem_usage: 71196.0
        timestamp: '2024-09-11T14:51:10.189094'
      start_time: '35400'
    - command: com.google.android.as
      name: ogle.android.as
      pid: 2248
      samples:
      - cpu_load: 0.0
        mem_usage: 94272.0
        timestamp: '2024-09-11T14:51:07.690535'
      - cpu_load: 0.0
        mem_usage: 94272.0
        timestamp: '2024-09-11T14:51:08.163705'
      - cpu_load: 0.0
        mem_usage: 94272.0
        timestamp: '2024-09-11T14:51:08.670101'
      - cpu_load: 0.0
        mem_usage: 94272.0
        timestamp: '2024-09-11T14:51:09.161167'
      - cpu_load: 0.0
        mem_usage: 94272.0
        timestamp: '2024-09-11T14:51:09.671461'
      - cpu_load: 0.32
        mem_usage: 94300.0
        timestamp: '2024-09-11T14:51:10.189094'
      start_time: '12207'
