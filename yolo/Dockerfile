FROM debian:bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 python3-pika python3-astropy python3-pip gcc python3-dev \
    python3-mysqldb python3-ephem libgl1-mesa-glx libglib2.0-0 imagemagick && \
    apt-get clean && \
    mkdir /yolo

WORKDIR /yolo

ARG TARGETPLATFORM
RUN if [ "$TARGETPLATFORM" = "linux/arm64" ]; then env PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install torch==2.1.0; else env PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install torch==2.1.0+cpu -f https://download.pytorch.org/whl/torch_stable.html; fi

#hm... Странно, есть пакеты тут https://download.pytorch.org/whl/torch_stable.html
#cpu/torch-2.1.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
#cpu/torch-2.1.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
RUN env PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install ultralytics
RUN env PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install imgaug

COPY settings.yaml /root/.config/Ultralytics/settings.yaml
