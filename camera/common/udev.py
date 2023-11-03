#!/usr/bin/python3

import lib

import os
import re
import sys
import subprocess

devs = []

proc = subprocess.Popen(['/usr/bin/lsusb'],stdout=subprocess.PIPE)
while True:
  line = proc.stdout.readline()
  if not line:
    break

  result = re.match(r'Bus (\d+) Device (\d+): ID (....):(....)', line.decode())

  if result:
    devs.append({
      'path': '/dev/bus/usb/'+ result.group(1) +'/'+ result.group(2),
      'vendor': result.group(3),
      'product': result.group(4),
    })




rules = open('/camera/udev/etc/udev/rules.d/85-qhyccd.rules', 'r')
 
while True:
  line = rules.readline()

  if not line:
    break

  result = re.match(r'ATTRS\{idVendor\}=="(....)", ATTRS\{idProduct\}=="(....)", RUN\+="/sbin/fxload ([^"]+)"', line)

  if result:
    for dev in devs:
      if dev['vendor'] == result.group(1) and dev['product'] == result.group(2):
        print('/camera/'+ lib.getArch() +'/fxload '+ result.group(3).replace('$env{DEVNAME}', dev['path']))
        os.system('/camera/'+ lib.getArch() +'/fxload '+ result.group(3).replace('$env{DEVNAME}', dev['path']))

        break

