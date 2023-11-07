#!/bin/sh

docker run --rm --network=allskypy_appnet -v /opt/allsky.py/:/opt/allsky.py/:ro -v /sys/class/gpio:/sys/class/gpio olegmilantiev/allsky-php /usr/local/bin/php /opt/allsky.py/rc.local.php
