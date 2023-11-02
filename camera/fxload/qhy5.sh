#!/bin/sh

#lsusb | grep "16c0:0901"
#Bus 005 Device 004: ID 16c0:0901
#bus = 005, значит /dev/bus/usb/005
#device = 004, значит /dev/bus/usb/005/004
#@todo доделать скрипт

fxload -t fx2 -D /dev/bus/usb/005/004 -I /lib/firmware/qhy/QHY5.HEX -s /lib/firmware/qhy/QHY5LOADER.HEX

#Bus 005 Device 005: ID 16c0:296d Van Ooijen Technische Informatica

Для USB3 нужна другая fxload, которая понимает -t fx3. Есть в архиве
Ну и вызов, соответственно:
/root/fxload/fx3load/fxload -t fx3 -I /lib/firmware/qhy/QHY5III290.img -D /dev/bus/usb/004/018
