#!/bin/sh

docker run --network=allskypy_appnet -v /opt/allsky.py:/opt/allsky.py olegmilantiev/indi /opt/allsky.py/list.py