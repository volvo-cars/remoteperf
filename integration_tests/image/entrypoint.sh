#!/bin/bash

/usr/sbin/sshd -D &
source /usr/local/bin/android_emulator_start.sh

exec /bin/bash