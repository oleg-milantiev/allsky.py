#!/usr/bin/python3

from astropy.io import fits
import config
from datetime import datetime, timedelta
import json
import logging
import MySQLdb
import numpy as np
import os
from PIL import Image
from scipy import signal
import sys

logging.basicConfig(filename=config.log['path'], level=config.log['level'])

db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
	 database=config.db['database'], charset='utf8')

cursor = db.cursor()

web = {}
cursor.execute('select id, val from config')
for row in cursor.fetchall():
	web[row[0]] = json.loads(row[1])



print('Start to scan last day fits for hot pixels')
today = datetime.now()
yesterday = today - timedelta(1)
first = True
count = 0

for f in os.listdir('/fits/'):
	if f[-4:] != '.fit':
		continue

	print(f)

	d = datetime.strptime(f[:-4], '%Y-%m-%d_%H-%M')

	if yesterday < d < today:
		try:
			fit = fits.open('/fits/'+ f)
			hdu = fit[0]
		except:
			logging.error('[!] Не могу открыть fit')
			continue

#		print(hdu.header)
		if not 'XBINNING' in hdu.header or int(hdu.header['XBINNING']) != 2 or not 'EXPTIME' in hdu.header or not 'MEDIAN' in hdu.header or float(hdu.header['EXPTIME']) < (web['ccd']['expMax'] / 2) or float(hdu.header['MEDIAN']) > float(web['ccd']['avgMax']):
			continue

#		mask = np.where(hdu.data >= 65535, hdu.data, 0)
#		median = signal.medfilt2d(mask, kernel_size=3)
#		hot = mask - median

		if first:
			first = False
			avg = np.empty(hdu.data.shape)

		for y in range(1, hdu.data.shape[0] - 1):
			for x in range(1, hdu.data.shape[1] - 1):
				if hdu.data[y, x] == 65535 and hdu.data[y-1, x-1] != 65535 and hdu.data[y-1, x] != 65535 and hdu.data[y-1, x+1] != 65535 and hdu.data[y, x-1] != 65535 and hdu.data[y, x+1] != 65535 and hdu.data[y+1, x-1] != 65535 and hdu.data[y+1, x] != 65535 and hdu.data[y+1, x+1] != 65535:
					avg[y, x] += 1

#		count += 1
#		if count == 10:
#			break

#		img = Image.fromarray(mask.astype('uint8'))
#		img.save('/snap/mask.jpg')

#		img = Image.fromarray(median.astype('uint8'))
#		img.save('/snap/median.jpg')

#		img = Image.fromarray(hot.astype('uint8'))
#		img.save('/snap/hot.jpg')

#		sys.exit()

img = Image.fromarray(np.where(avg >= avg.max() * 0.1, 255, 0).astype('uint8'))
img.save('/snap/avg.jpg')
