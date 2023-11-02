#!/usr/bin/python3

import os
import glob
import time
import re
import logging
from datetime import datetime, timedelta
import sys
import config
import mysql.connector

db = mysql.connector.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'], database=config.db['database'], charset='utf8')
cursor = db.cursor(dictionary=True)
cursor2 = db.cursor(dictionary=True)

cursor.execute('select * from video where work_begin = 0 order by work_queue')

for row in cursor:
	cursor2.execute('update video set work_begin = {} where id = {}'.format(int(time.time()), row['id']))
	db.commit()

	begin = datetime.utcfromtimestamp( row['video_begin'] + 3*3600 )
	end   = datetime.utcfromtimestamp( row['video_end'] +3*3600 )
	count = 1

	for f in glob.glob(config.path['snap'] +'demand-*.jpg'):
		os.remove(f)

	for f in sorted(glob.glob(config.path['snap'] +'????-??-??_??-??.jpg')):
		result = re.match(config.path['snap'] +r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2}).jpg', f)

		if result:
			date = datetime(int(result.group(1)), int(result.group(2)), int(result.group(3)), int(result.group(4)), int(result.group(5)))

			if date >= begin and date <= end:
				os.symlink(f, config.path['snap'] +'demand-'+ "%06d" % count +'.jpg')
				count += 1

	if count > 5:
		scale = '{}:{}'.format(config.video['width'], config.video['height'])

		if 'cfa' in config.ccd:
			options = '-vf scale='+ scale
		else:
			options = '-pix_fmt yuv420p -vf format=gray,scale='+ scale

		os.system(config.path['ffmpeg'] + ' -f image2 -i '+ config.path['snap'] +'demand-%06d.jpg '+ options +' '+ config.path['video-demand'] + begin.strftime("%Y-%m-%d-%H-%M") +'-{}-{}'.format(row['id'], config.video['height']) +'p.mp4')

	cursor2.execute('update video set work_end = {}, frames = {} where id = {}'.format(int(time.time()), count, row['id']))
	db.commit()


for f in glob.glob(config.path['snap'] +'demand-*.jpg'):
	os.remove(f)
