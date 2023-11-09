#!/opt/yolo/bin/python3

import os
import sys
from astropy.io import fits

hot = []
hot[0] = Image.open('/opt/allsky.py/camera/common/hot-1.png')
hot[1] = Image.open('/opt/allsky.py/camera/common/hot-2.png')

for f in os.listdir('./'):
	if f[-3:0] == 'fit':
		fit = fits.open(f, mode='update')
		hdu = fit[0]
		print(f +': bin'+ hdu.header['XBINNING'])

		hotCount = 0
		for y in range(1, hdu.data.shape[0] - 1):
			for x in range(1, hdu.data.shape[1] - 1):
				if hot[int(hdu.header['XBINNING']) - 1].getpixel((x, y)) == 255:
					hotCount += 1
					hdu.data[y, x] = round((float(hdu.data[y-1, x-1]) + float(hdu.data[y-1, x]) + float(hdu.data[y-1, x+1]) + float(hdu.data[y, x-1]) + float(hdu.data[y, x+1]) + float(hdu.data[y+1, x-1]) + float(hdu.data[y+1, x]) + float(hdu.data[y+1, x+1])) / 8)
		fit.close()
		sys.exit()