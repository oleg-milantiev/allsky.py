#!/bin/sh

docker run --user 0 --rm --network=allskypy_appnet -v /opt/allsky.py/:/opt/allsky.py/:ro -v /sys/class/gpio:/sys/class/gpio --privileged olegmilantiev/allsky-php /usr/local/bin/php /opt/allsky.py/rc.local.php
