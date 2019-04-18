#!/usr/bin/python3

import os
import sys
import glob
import re
import logging
from datetime import datetime, timedelta

import config

yesterday = datetime.now() - timedelta(1)
today     = datetime.now()

begin = datetime(yesterday.year, yesterday.month, yesterday.day, 12)
end   = datetime(today.year, today.month, today.day, 11, 59)

files = []

for f in sorted(glob.glob(config.path['snap'] +'????-??-??_??-??.jpg')):
	result = re.match(config.path['snap'] +r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2}).jpg', f)

	if result:
		date = datetime(int(result.group(1)), int(result.group(2)), int(result.group(3)), int(result.group(4)), int(result.group(5)))

		if date >= begin and date <= end:
			files.append(f)

if len(files) < 5:
	sys.exit(0)

from PIL import Image, ImageDraw, ImageFont

keogram = Image.new('RGB', (len(files), config.keogram['height']), 'black')

i = 0

for f in files:
	im = Image.open(f)
	column = im.crop( (config.keogram['column'], 0, config.keogram['column'] + 1, im.size[1]) )
	keogram.paste(column, (i, 0) )
	i += 1

	#print('{}%'.format(round(i / len(files) * 100)))

keogram.save(config.path['keogram'] +'keogram-'+ begin.strftime("%Y-%m-%d") +'.jpg')





