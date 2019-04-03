#!/usr/bin/python3

import os
import glob
import re
import logging
from datetime import datetime, timedelta

import config

yesterday = datetime.now() - timedelta(1)
today     = datetime.now()

begin = datetime(yesterday.year, yesterday.month, yesterday.day, 12)
end   = datetime(today.year, today.month, today.day, 11, 59)
count = 1

for f in glob.glob(config.path['snap'] +'day-*.jpg'):
	os.remove(f)

for f in sorted(glob.glob(config.path['snap'] +'????-??-??_??-??.jpg')):
	result = re.match(config.path['snap'] +r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2}).jpg', f)

	if result:
		date = datetime(int(result.group(1)), int(result.group(2)), int(result.group(3)), int(result.group(4)), int(result.group(5)))

		if date >= begin and date <= end:
			os.symlink(f, config.path['snap'] +'day-'+ "%06d" % count +'.jpg')
			count += 1

if count > 5:
	scale = '{}:{}'.format(config.video['width'], config.video['height'])

	if 'cfa' in config.ccd:
		options = '-vf scale='+ scale
	else:
		options = '-pix_fmt yuv420p -vf format=gray,scale='+ scale

	os.system(config.path['ffmpeg'] + ' -f image2 -i '+ config.path['snap'] +'day-%06d.jpg '+ options +' '+ config.path['video'] + begin.strftime("%Y-%m-%d") +'-{}'.format(config.video['height']) +'p.mp4')


for f in glob.glob(config.path['snap'] +'day-*.jpg'):
	os.remove(f)

