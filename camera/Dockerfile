FROM ubuntu

#FROM alpine
#RUN apk add --no-cache python3 py3-numpy py3-pillow

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    usbutils libusb-1.0-0 python3 python3-numpy python3-astropy python3-pika && \
    apt-get clean

WORKDIR /camera

#udevadm control --reload-rules && udevadm trigger 
#/lib/systemd/systemd-udevd --daemon
