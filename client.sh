docker run --env-file=.env --network=allskypy_appnet --rm -it -v /opt/allsky.py/camera/qhy/udev/etc/udev/rules.d/:/etc/udev/rules.d -v /opt/allsky.py/camera/qhy/udev/lib/firmware/qhy/:/lib/firmware/qhy -v /opt/allsky.py/camera/qhy:/camera -v /dev/bus/usb:/dev/bus/usb --privileged olegmilantiev/allsky bash