#FROM debian:bullseye
FROM debian:bookworm

RUN apt-get -qq update && apt-get -qqy dist-upgrade

# indi dependencies
RUN apt-get -qqy install \
        cdbs dpkg-dev debhelper cmake curl dcraw fakeroot wget git ssh \
        libcurl4-gnutls-dev libboost-dev libboost-regex-dev libcfitsio-dev \
        libftdi-dev libgphoto2-dev libgps-dev libgsl-dev libjpeg-dev libtiff5-dev \
        libnova-dev libopenal-dev libraw-dev libusb-1.0-0-dev librtlsdr-dev \
        libfftw3-dev libev-dev zlib1g-dev libconfuse-dev python3-all-dev doxygen \
        libboost-test-dev swig g++ libftdi1-dev \
        googletest clang lsb-release dirmngr vim \
        libavcodec-dev libavdevice-dev libavformat-dev libavutil-dev

RUN apt-get -qqy install libdc1394-dev apt-utils

# pyindi-client dependencies
RUN apt-get -qqy install \
        python3-setuptools swig libcfitsio-dev libnova-dev

RUN apt-get -qqy install \
        python3-pip

# Build and install gtest and gmock libraries
WORKDIR /usr/src/googletest
RUN cmake .
RUN make install


#ADD https://raw.githubusercontent.com/jochym/indi/master/docker/run-build.sh /home/
#RUN chmod a+x /home/run-build.sh

#RUN /home/run-build.sh indilib master

WORKDIR /home

RUN git clone https://github.com/indilib/indi.git
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug /home/indi
RUN make -j4
RUN make install

RUN git clone https://github.com/indilib/pyindi-client.git
WORKDIR /home/pyindi-client
RUN python3 setup.py install

RUN apt-get -qqy install python3-numpy python3-astropy python3-opencv

RUN apt-get -qqy install python3-mysqldb

#COPY requirements.txt requirements.txt
#RUN pip3 install -r requirements.txt
