#!/bin/sh

docker run --rm --network=allskypy_appnet -v /opt/allsky.py/camera/common:/camera olegmilantiev/allsky-indi /camera/indi.list.py
