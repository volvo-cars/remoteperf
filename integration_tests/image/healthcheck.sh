#!/bin/bash

# set -x

function is_emulator_running() {
  state=$(adb devices | grep emulator | cut -f2)
  if [ "$state" = "device" ]; then
    echo "emulator is running"
    return 0
  else
    echo "emulator is not running"
    return 1
  fi
}

is_emulator_running