#!/usr/bin/python3

#@todo from allsky.milantiev.com/minute/keo

import ephem
import os
import sys
import glob
import re
import logging
from datetime import datetime, timedelta

yesterday = datetime.now() - timedelta(1)
today     = datetime.now()

observatory = ephem.Observer()
observatory.lat, observatory.lon = '44.791395', '38.583824' # @todo move to web config
observatory.date = yesterday.strftime('%Y-%m-%d %H:%M')
sun = ephem.Sun()
sun.compute(observatory)

begin = datetime(yesterday.year, yesterday.month, yesterday.day, 12)
end   = datetime(today.year, today.month, today.day, 11, 59)

files = []

for f in sorted(glob.glob('/snap/????-??-??_??-??.jpg')):
	result = re.match(r'/snap/(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2}).jpg', f)

	if result:
		date = datetime(int(result.group(1)), int(result.group(2)), int(result.group(3)), int(result.group(4)), int(result.group(5)))

		if date >= begin and date <= end:
			files.append(f)

if len(files) < 5:
	sys.exit(0)

from PIL import Image, ImageDraw, ImageFont

im = Image.open(files[0])
keogram = Image.new('RGB', (len(files), im.size[1]), 'black')

i = 0
columnNo = 349 # @todo move to web config

for f in files:
	im = Image.open(f)
	column = im.crop( (columnNo, 0, columnNo + 1, im.size[1]) )
	keogram.paste(column, (i, 0) )
	i += 1

	#print('{}%'.format(round(i / len(files) * 100)))

keogram.save('/keogram/keogram-'+ begin.strftime("%Y-%m-%d") +'.jpg')
