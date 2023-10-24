FROM debian:bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 python3-pika python3-astropy python3-pip gcc python3-dev \
    libgl1-mesa-glx libglib2.0-0 imagemagick && \
    apt-get clean && \
    mkdir /yolo

WORKDIR /yolo

RUN env PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --upgrade pip
RUN env PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --upgrade ultralytics
RUN env PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --upgrade imgaug
RUN env PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --upgrade ephem
