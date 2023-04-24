FROM ubuntu:23.04

RUN apt-get -qq update && apt-get -qqy dist-upgrade && apt-get -qqy --no-install-recommends install \
  # indi dependencies
  ca-certificates git cdbs dkms cmake fxload libev-dev libgps-dev libgsl-dev libraw-dev \
  libusb-dev zlib1g-dev libftdi-dev libgsl0-dev libjpeg-dev libkrb5-dev \
  libnova-dev libtiff-dev libfftw3-dev librtlsdr-dev libcfitsio-dev \
  libgphoto2-dev build-essential libusb-1.0-0-dev libdc1394-dev \
  libboost-regex-dev libcurl4-gnutls-dev libtheora-dev \
  # pyindi-client deps
  python3-all-dev python3-setuptools swig libcfitsio-dev libnova-dev \
  # qhy deps
  libnova-dev libcfitsio-dev libusb-1.0-0-dev zlib1g-dev libgsl-dev \
  build-essential cmake git libjpeg-dev libcurl4-gnutls-dev libtiff-dev \
  libftdi-dev libgps-dev libraw-dev libdc1394-dev libgphoto2-dev \
  libboost-dev libboost-regex-dev librtlsdr-dev liblimesuite-dev \
  libftdi1-dev libgps-dev libavcodec-dev libavdevice-dev \
  # Other Python3 libs
  python3-numpy python3-astropy python3-opencv python3-mysqldb python3-pil

# Clone sources from github/indilib/*
RUN mkdir -p /home/git
WORKDIR /home/git

RUN git clone https://github.com/indilib/indi.git && mkdir -p /home/build/indi && cd /home/build/indi && cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /home/git/indi && make -j4 && make install && rm -Rf /home/git/indi && rm -Rf /home/build/indi

RUN git clone https://github.com/indilib/pyindi-client.git && cd /home/git/pyindi-client && python3 setup.py install && rm -Rf /home/git/pyindi-client

RUN git clone https://github.com/indilib/indi-3rdparty.git && mkdir -p /home/build/libqhy && cd /home/build/libqhy && cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /home/git/indi-3rdparty/libqhy && make -j4 && make install && mkdir -p /home/build/qhy && cd /home/build/qhy && cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /home/git/indi-3rdparty/indi-qhy && make -j4 && make install && ln -s /usr/lib/arm-linux-gnueabihf/libqhyccd.so /usr/lib/arm-linux-gnueabihf/libqhyccd.so.22 && mkdir -p /home/build/libasi && cd /home/build/libasi && cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /home/git/indi-3rdparty/libasi && make -j4 && make install && mkdir -p /home/build/asi && cd /home/build/asi && cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /home/git/indi-3rdparty/indi-asi && make -j4 && make install && rm -Rf /home/git && rm -Rf /home/build

WORKDIR /opt/allsky.py
