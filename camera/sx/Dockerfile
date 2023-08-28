FROM debian:bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 python3-astropy python3-pika python3-setuptools swig \
    git cdbs dkms cmake fxload libev-dev libgps-dev libgsl-dev \
    libraw-dev libusb-dev zlib1g-dev libftdi-dev libgsl0-dev \
    libjpeg-dev libkrb5-dev libnova-dev libtiff-dev libfftw3-dev \
    librtlsdr-dev libcfitsio-dev libgphoto2-dev build-essential \
    libusb-1.0-0-dev libdc1394-dev libboost-regex-dev libcurl4-gnutls-dev \
    libtheora-dev python3-dev swig libcfitsio-dev libnova-dev && \
    apt-get clean

RUN apt-get install -y --no-install-recommends \
    libindi-dev indi-sx && \
    apt-get clean

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow

WORKDIR /tmp

RUN env GIT_SSL_NO_VERIFY=true git clone --depth 1 https://github.com/indilib/pyindi-client.git && \
    cd /tmp/pyindi-client && \
    python3 setup.py install && \
    rm -Rf /tmp/pyindi-client

WORKDIR /camera
