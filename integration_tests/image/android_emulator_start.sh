#!/bin/bash

# set -x

emulator_name=${EMULATOR_NAME}

function check_hardware_acceleration() {
    if [[ "$HW_ACCEL_OVERRIDE" != "" ]]; then
        hw_accel_flag="$HW_ACCEL_OVERRIDE"
    else
        HW_ACCEL_SUPPORT=$(grep -E -c '(vmx|svm)' /proc/cpuinfo)
        if [[ $HW_ACCEL_SUPPORT == 0 ]]; then
            hw_accel_flag="-accel off"
        else
            hw_accel_flag="-accel on"
        fi
    fi

    echo "$hw_accel_flag"
}

hw_accel_flag=$(check_hardware_acceleration)

function is_adb_server_running() {
  state=$(ps -ef | grep adb | grep -v grep)
  if [ -n "$state" ]; then
    echo "adb server is running"
    return 0
  else
    echo "adb server is not running"
    return 1
  fi
}

function is_adb_server_listening_to_all_interfaces() {
  state=$(ps -ef | grep  adb | grep -v grep | grep '\-a')
  if [ -n "$state" ]; then
    echo "adb server is listening to all interfaces"
    return 0
  else
    echo "adb server is not listening to all interfaces"
    return 1
  fi
}

function start_adb_server() {
  if is_adb_server_running; then
    if is_adb_server_listening_to_all_interfaces; then
      return
    fi
    echo "Killing adb server"
    adb kill-server
  fi
  echo "Starting adb server listening to all interfaces"
  adb -a server
}

function launch_emulator () {
  echo "Removing old logs"
  rm /nohup.out
  adb devices | grep emulator | cut -f1 | xargs -I {} adb -s "{}" emu kill
  options="@${emulator_name} -no-window -no-snapshot -noaudio -no-boot-anim -memory 2048 ${hw_accel_flag} -camera-back none"
  echo "${OSTYPE}: emulator ${options} -gpu off"
  nohup emulator $options -gpu off &

  sleep 5

  status=$(grep -F 'Running multiple emulators with the same AVD' /nohup.out)
  if [ -n "$status" ]; then
    echo "Error launching emulator. Due to container recycling. Retrying launch"
    adb devices | grep emulator | cut -f1 | xargs -I {} adb -s "{}" emu kill
    nohup emulator $options -gpu off &
  fi
}


function check_emulator_status () {
  printf "==> Checking emulator booting up status\n"
  start_time=$(date +%s)
  spinner=( "⠹" "⠺" "⠼" "⠶" "⠦" "⠧" "⠇" "⠏" )
  i=0
  timeout=${EMULATOR_TIMEOUT:-90}

  while true; do
    result=$(adb shell getprop sys.boot_completed 2>&1)

    if [ "$result" == "1" ]; then
      printf "==> Emulator is ready : '$result'            \n"
      adb devices -l
      adb shell input keyevent 82
      break
    elif [ "$result" == "" ]; then
      printf "==> Emulator is partially Booted! ${spinner[$i]}\r"
    else
      printf "==> $result, please wait ${spinner[$i]}           \r"
      i=$(( (i+1) % 8 ))
    fi

    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    if [ $elapsed_time -gt $timeout ]; then
      printf "==> Timeout after ${timeout} seconds elapsed .. \n"
      return 1
    fi
    sleep 1
  done
  return 0
};


function disable_animation() {
  adb shell "settings put global window_animation_scale 0.0"
  adb shell "settings put global transition_animation_scale 0.0"
  adb shell "settings put global animator_duration_scale 0.0"
};

function hidden_policy() {
  adb shell "settings put global hidden_api_policy_pre_p_apps 1;settings put global hidden_api_policy_p_apps 1;settings put global hidden_api_policy 1"
};

start_adb_server
sleep 2
launch_emulator
sleep 2
check_emulator_status
sleep 1
disable_animation
sleep 1
hidden_policy
sleep 1