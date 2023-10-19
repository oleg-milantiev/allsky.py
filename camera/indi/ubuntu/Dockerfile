FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow

RUN apt-get update && \
    apt-get install -y --no-install-recommends gpg-agent \
    python3 python3-astropy python3-pika python3-pillow python3-mysqldb \
    python3-requests python3-ephem software-properties-common usbutils && \
    apt-get clean

RUN add-apt-repository -y ppa:mutlaqja/ppa && \
    apt-get update && \
    apt-get install -y indi-qhy indi-sx indi-bin python3-indi-client  && \
    apt-get clean
#indi-full

#indi-asi - cant install it on linux/arm/v7 :(
#move to source build? https://github.com/indilib/indi-3rdparty

RUN apt-get remove -y software-properties-common && \
    apt-get autoremove -y && \
    apt-get clean

WORKDIR /camera
