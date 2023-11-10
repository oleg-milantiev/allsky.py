FROM debian:bookworm

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get autoremove -y && \
    apt-get clean

WORKDIR /
