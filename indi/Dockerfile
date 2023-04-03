FROM debian:bookworm

RUN apt-get -qq update && apt-get -qqy dist-upgrade

# indi dependencies
RUN apt-get -qqy install \
  git \
  cdbs \
  dkms \
  cmake \
  fxload \
  libev-dev \
  libgps-dev \
  libgsl-dev \
  libraw-dev \
  libusb-dev \
  zlib1g-dev \
  libftdi-dev \
  libgsl0-dev \
  libjpeg-dev \
  libkrb5-dev \
  libnova-dev \
  libtiff-dev \
  libfftw3-dev \
  librtlsdr-dev \
  libcfitsio-dev \
  libgphoto2-dev \
  build-essential \
  libusb-1.0-0-dev \
  libdc1394-dev \
  libboost-regex-dev \
  libcurl4-gnutls-dev \
  libtheora-dev

# Clone sources from github/indilib/*
RUN mkdir -p /home/git
WORKDIR /home/git
RUN git clone https://github.com/indilib/indi.git
RUN git clone https://github.com/indilib/pyindi-client.git
RUN git clone https://github.com/indilib/indi-3rdparty.git
RUN git clone https://github.com/qhyccd-lzr/QHYCCD_Linux.git

# compile & install
RUN mkdir -p /home/build/indi
WORKDIR /home/build/indi
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /home/git/indi
RUN make -j4
RUN make install


######### PYINDI-CLIENT ########
# dependencies
RUN apt-get -qqy install \
        python3-all-dev python3-setuptools swig libcfitsio-dev libnova-dev
# compile & install
WORKDIR /home/git/pyindi-client
RUN python3 setup.py install


########## QHY ##########
# dependencies
RUN apt-get -qqy install \
    libnova-dev libcfitsio-dev libusb-1.0-0-dev zlib1g-dev libgsl-dev \
    build-essential cmake git libjpeg-dev libcurl4-gnutls-dev libtiff-dev \
    libftdi-dev libgps-dev libraw-dev libdc1394-dev libgphoto2-dev \
    libboost-dev libboost-regex-dev librtlsdr-dev liblimesuite-dev \
    libftdi1-dev libgps-dev libavcodec-dev libavdevice-dev

# libqhy
RUN mkdir -p /home/build/libqhy
WORKDIR /home/build/libqhy
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /home/git/indi-3rdparty/libqhy
RUN make -j4 
RUN make install

#indi-qhy
RUN mkdir -p /home/build/qhy
WORKDIR /home/build/qhy
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /home/git/indi-3rdparty/indi-qhy
RUN make -j4
RUN make install

########## ASI ##########
# libqhy
RUN mkdir -p /home/build/libasi
WORKDIR /home/build/libasi
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /home/git/indi-3rdparty/libasi
RUN make -j4 
RUN make install

# indi-asi
RUN mkdir -p /home/build/asi
WORKDIR /home/build/asi
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /home/git/indi-3rdparty/indi-asi
RUN make -j4
RUN make install

# Other Python3 libs
RUN apt-get -qqy install python3-numpy python3-astropy python3-opencv python3-mysqldb

# remove build folders
WORKDIR /opt/allsky.py
RUN rm -rf /home/git
RUN rm -rf /home/build
