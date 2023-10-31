#!/bin/sh

ARCH=arm64
docker run --rm --network=allskypy_appnet -v /opt/allsky.py/camera/common:/camera olegmilantiev/allsky-indi-${ARCH} /camera/indi.list.py
