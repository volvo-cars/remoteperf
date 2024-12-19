# serial_image Dockerfile
FROM ubuntu:22.04

#==============================
# Base OS installation
#==============================
RUN apt-get update --fix-missing
RUN apt-get install -y openjdk-18-jdk-headless
RUN apt-get install -y socat screen
RUN apt-get install -y python3.10 python3-venv
RUN apt-get install -y nox pip vim openssh-server curl sudo wget unzip bzip2
RUN apt-get install -y libdrm-dev libxkbcommon-dev libgbm-dev libasound-dev libnss3
RUN apt-get install -y libxcursor1 libpulse-dev libxshmfence-dev libdbus-glib-1-2
RUN apt-get install -y openssl --upgrade

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git

RUN cd /tmp && wget https://www.python.org/ftp/python/3.8.16/Python-3.8.16.tgz

RUN cd /tmp && tar -xf Python-3.8.16.tgz

RUN cd /tmp && rm Python-3.8.16.tgz

RUN cd /tmp/Python-3.8.16 && ./configure --enable-optimizations && make -j$(nproc) && make altinstall

RUN cd /

RUN python3.8 -m ensurepip

RUN python3.8 -m pip install --upgrade pip

RUN python3.8 -m pip install pytest


#==============================
# Android SDK ARGS
#==============================
ARG ARCH="x86_64"
ARG TARGET="google_apis_playstore"
ARG API_LEVEL="34"
ARG BUILD_TOOLS="34.0.0"
ARG ANDROID_ARCH=${ANDROID_ARCH_DEFAULT}
ARG ANDROID_API_LEVEL="android-${API_LEVEL}"
ARG ANDROID_APIS="${TARGET};${ARCH}"
ARG EMULATOR_PACKAGE="system-images;${ANDROID_API_LEVEL};${ANDROID_APIS}"
ARG PLATFORM_VERSION="platforms;${ANDROID_API_LEVEL}"
ARG BUILD_TOOL="build-tools;${BUILD_TOOLS}"
ARG ANDROID_CMD="commandlinetools-linux-11076708_latest.zip"
ARG ANDROID_SDK_PACKAGES="${EMULATOR_PACKAGE} ${PLATFORM_VERSION} ${BUILD_TOOL} platform-tools emulator"

#==============================
# Set JAVA_HOME - SDK
#==============================
ENV ANDROID_SDK_ROOT=/opt/android
ENV PATH "$PATH:$ANDROID_SDK_ROOT/cmdline-tools/tools:$ANDROID_SDK_ROOT/cmdline-tools/tools/bin:$ANDROID_SDK_ROOT/emulator:$ANDROID_SDK_ROOT/tools/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/build-tools/${BUILD_TOOLS}"
ENV DOCKER="true"

#============================================
# Install required Android CMD-line tools
#============================================
RUN wget https://dl.google.com/android/repository/${ANDROID_CMD} -P /tmp && \
              unzip -d $ANDROID_SDK_ROOT /tmp/$ANDROID_CMD && \
              mkdir -p $ANDROID_SDK_ROOT/cmdline-tools/tools && cd $ANDROID_SDK_ROOT/cmdline-tools &&  mv NOTICE.txt source.properties bin lib tools/  && \
              cd $ANDROID_SDK_ROOT/cmdline-tools/tools && ls

#============================================
# Install required package using SDK manager
#============================================
RUN yes Y | sdkmanager --licenses
RUN yes Y | sdkmanager --verbose --no_https ${ANDROID_SDK_PACKAGES}
RUN yes Y | sdkmanager --channel=3 emulator

#============================================
# Create required emulator
#============================================
ARG EMULATOR_NAME="nexus"
ARG EMULATOR_DEVICE="Nexus 6"
ENV EMULATOR_NAME=$EMULATOR_NAME
ENV DEVICE_NAME=$EMULATOR_DEVICE
RUN echo "no" | avdmanager --verbose create avd --force --name "${EMULATOR_NAME}" --device "${EMULATOR_DEVICE}" --package "${EMULATOR_PACKAGE}"

#============================================
# Create a script to provide a shell
#============================================
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
COPY android_emulator_start.sh /usr/local/bin/android_emulator_start.sh
RUN chmod +x /usr/local/bin/android_emulator_start.sh
COPY run_nox /usr/local/bin/run_nox
RUN chmod +x /usr/local/bin/run_nox
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

#============================================
# Setup Testing Mock Script
#============================================
COPY mocks/systemd-analyze /usr/bin/systemd-analyze
RUN chmod +x /usr/bin/systemd-analyze
COPY mocks/nicinfo /usr/bin/nicinfo
RUN chmod +x /usr/bin/nicinfo

#============================================
# Setup ssh server
#============================================
RUN mkdir /var/run/sshd
RUN echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config
RUN echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config
RUN echo 'root:root' | chpasswd || true

#============================================
# Install pytest
#============================================
RUN pip install pytest

#============================================
# Entrypoint in Container
#============================================
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
