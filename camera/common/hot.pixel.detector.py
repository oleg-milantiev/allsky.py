#!/usr/bin/python3

import lib

from astropy.io import fits
from astropy.stats import sigma_clipped_stats
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


web = lib.getWebConfig()

print('Start to scan last day fits for hot pixels')
first = True
bin = None

for f in os.listdir('./hot'):
	if f[-4:] != '.fit':
		continue

	print(f)

	try:
		fit = fits.open('./hot/'+ f)
		hdu = fit[0]
	except:
		logging.error('[!] Не могу открыть fit')
		continue

	if first:
		first = False
		bin = hdu.header['XBINNING']
		avg = np.zeros(hdu.data.shape)

	if hdu.header['XBINNING'] != bin:
		logging.error('[!] Не соответствует binning')
		continue

	mean, median, std = sigma_clipped_stats(hdu.data, sigma=3.0)

	print('Sigma-clipped stat: mean={}, median={}, std={}'.format(mean, median, std))

	'''
	mask = np.where(hdu.data >= median + std, hdu.data, 0)
	median = signal.medfilt2d(mask, kernel_size=3)
	hot = mask - median

	img = Image.fromarray(mask.astype('uint8'))
	img.save('/snap/mask.jpg')

	img = Image.fromarray(median.astype('uint8'))
	img.save('/snap/median.jpg')

	img = Image.fromarray(hot.astype('uint8'))
	img.save('/snap/hot.jpg')

	sys.exit()
	'''

	min = median + std/2

	count = 0

	for y in range(1, hdu.data.shape[0] - 1):
		for x in range(1, hdu.data.shape[1] - 1):
			if hdu.data[y, x] > (median + std) and hdu.data[y-1, x-1] < min and hdu.data[y-1, x] < min and hdu.data[y-1, x+1] < min and hdu.data[y, x-1] < min and hdu.data[y, x+1] < min and hdu.data[y+1, x-1] < min and hdu.data[y+1, x] < min and hdu.data[y+1, x+1] < min:
				count += 1
				avg[y, x] += 1

	print('Found hot pixels: '+ str(count))

img = Image.fromarray(np.where(avg >= avg.max() * 0.1, 255, 0).astype('uint8'))
#img.save('/snap/avg.png')
img.save('/opt/allsky.py/camera/common/hot-{}.png'.format(bin))
