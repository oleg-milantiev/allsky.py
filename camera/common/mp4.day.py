#!/usr/bin/python3

#@todo from allsky.milantiev.com/minute/keo

import ephem
import glob
import json
import logging
import MySQLdb
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.append('camera/common')
import config


logging.basicConfig(filename=config.log['path'], level=config.log['level'])
logging.info('[+] Start')

db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
	database=config.db['database'], charset='utf8')
cursor = db.cursor()

web = {}
cursor.execute('select id, val from config')
for row in cursor.fetchall():
	web[row[0]] = json.loads(row[1])

yesterday = datetime.now() - timedelta(1)

observatory = ephem.Observer()
observatory.lat, observatory.lon = '44.791395', '38.583824' # @todo move to web config
observatory.date = yesterday.strftime('%Y-%m-%d %H:%M')

sun = ephem.Sun()
sun.compute(observatory)

print(sun.sunset())
exit



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

		stat = os.stat(f)
		if stat.st_size == 0:
			os.remove(f)

		else:
			if date >= begin and date <= end:
				os.symlink(f, config.path['snap'] +'day-'+ "%06d" % count +'.jpg')
				count += 1

if count > 5:
	scale = '{}:{}'.format(config.video['width'], config.video['height'])

	if 'cfa' in config.ccd:
		options = '-vf scale='+ scale
	else:
		options = '-pix_fmt yuv420p -vf format=gray,scale='+ scale

	os.system('docker run -v /opt/allsky.py/web:/web jrottenberg/ffmpeg:4.1-alpine -f image2 -i /web/snap/day-%06d.jpg '+ options +' /web/video/'+ begin.strftime("%Y-%m-%d") +'-{}'.format(config.video['height']) +'p.mp4')


for f in glob.glob(config.path['snap'] +'day-*.jpg'):
	os.remove(f)


# удаление старых mp4
old = datetime.now() - timedelta(config.video['days'])

for f in os.listdir(config.path['video']):
	if os.path.isfile(config.path['video'] + f):
		result = re.match(r'(\d{4})-(\d{2})-(\d{2})-(\d+)p.mp4', f)

		if result:
			date = datetime(int(result.group(1)), int(result.group(2)), int(result.group(3)), 12, 0)

			if date < old:
				logging.debug('Файл '+ f +' удалён')
				os.remove(config.path['video'] + f)


# Удаление старых данных таблицы sensors
if 'sensors' in config.archive:
#	print("""delete from sensor where date < UNIX_TIMESTAMP( date_sub(now(), interval %(day)i day) )"""%{"day":config.archive['sensors']})
	cursor.execute("""delete from sensor where date < UNIX_TIMESTAMP( date_sub(now(), interval %(day)i day) )"""%{"day":config.archive['sensors']})

	db.commit()
