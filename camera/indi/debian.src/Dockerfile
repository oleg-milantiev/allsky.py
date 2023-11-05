FROM debian:bookworm

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow

WORKDIR /tmp

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 python3-setuptools python3-scipy \
    python3-photutils git cdbs dkms cmake fxload libev-dev libgps-dev libgsl-dev \
    libraw-dev libusb-dev zlib1g-dev libftdi-dev libgsl0-dev \
    libjpeg-dev libkrb5-dev libnova-dev libtiff-dev libfftw3-dev \
    librtlsdr-dev libcfitsio-dev libgphoto2-dev build-essential \
    libusb-1.0-0-dev libdc1394-dev libboost-regex-dev libcurl4-gnutls-dev \
    libtheora-dev python3-dev swig libnova-dev \
    python3-astropy python3-pika python3-pillow python3-mysqldb \
    python3-requests python3-pip python3-ephem usbutils && \
    python3 -m pip install --break-system-packages Adafruit-PureIO && \
    python3 -m pip install --break-system-packages zwoasi && \
     env GIT_SSL_NO_VERIFY=true git clone --depth 1 https://github.com/indilib/indi.git && \
    git clone --depth 1 https://github.com/indilib/pyindi-client.git && \
    git clone --depth 1 https://github.com/indilib/indi-3rdparty && \
     mkdir /tmp/build1 && \
    cd /tmp/build1 && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /tmp/indi && \
    make -j4 && \
    make install && \
     cd /tmp/pyindi-client && \
    python3 setup.py install && \
     mkdir /tmp/build && \
    mkdir /tmp/build/indi-sx && \
    mkdir /tmp/build/libqhy && \
    mkdir /tmp/build/libasi && \
    mkdir /tmp/build/indi-qhy && \
    mkdir /tmp/build/indi-asi && \
    cd /tmp/build/indi-sx && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /tmp/indi-3rdparty/indi-sx && \
    make -j4 && \
    make install && \
    cd /tmp/build/libqhy && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /tmp/indi-3rdparty/libqhy && \
    make -j4 && \
    make install && \
    cd /tmp/build/libasi && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /tmp/indi-3rdparty/libasi && \
    make -j4 && \
    make install && \
    cd /tmp/build/indi-qhy && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /tmp/indi-3rdparty/indi-qhy && \
    make -j4 && \
    make install && \
    cd /tmp/build/indi-asi && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /tmp/indi-3rdparty/indi-asi && \
    make -j4 && \
    make install && \
    rm -Rf /tmp/indi && \
     apt-get remove -y \
    python3-setuptools swig python3-pip \
    git cdbs dkms cmake build-essential \
    libev-dev libgps-dev libgsl-dev libraw-dev libusb-dev zlib1g-dev \
    libftdi-dev libgsl0-dev libjpeg-dev libkrb5-dev libnova-dev libtiff-dev \
    libfftw3-dev librtlsdr-dev libcfitsio-dev libgphoto2-dev \
    libusb-1.0-0-dev libdc1394-dev libboost-regex-dev libcurl4-gnutls-dev \
    libtheora-dev python3-dev swig libnova-dev gcc make && \
    apt autoremove -y && \
     apt-get install -y --no-install-recommends \
    python3-scipy python3-photutils python3-astropy python3-pika python3-pillow \
    python3-mysqldb python3-requests python3-ephem usbutils libcfitsio10 python3-smbus2 && \
    apt-get clean && \
    rm -Rf /tmp/*

WORKDIR /camera
