FROM ubuntu

#FROM alpine
#RUN apk add --no-cache python3 py3-numpy py3-pillow

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    usbutils python3-requests libusb-1.0-0 python3 python3-numpy python3-astropy \
    swig git python3-setuptools python3-pika python3-pil python3-mysqldb && \
    apt-get clean

WORKDIR /tmp
RUN env GIT_SSL_NO_VERIFY=true git clone https://github.com/python-zwoasi/python-zwoasi.git && \
    cd /tmp/python-zwoasi && \
    python3 setup.py install && \
    rm -Rf /tmp/python-zwoasi

WORKDIR /camera

#udevadm control --reload-rules && udevadm trigger 
#/lib/systemd/systemd-udevd --daemon
