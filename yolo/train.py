#!/usr/bin/python3

from ultralytics import YOLO
import math
import os
import sys
import random
import shutil
import imgaug as ia
from imgaug import augmenters as iaa
import numpy as np
import imageio
from datetime import datetime, timedelta
import pathlib
import ephem

# todo check input
# argv[1] = network size [n, s, m, l, x]
# argv[2] = epochs count
# argv[3] = version

'''
Copy fits to small jpgs:
- from /yolo/cloud and /yolo/clean folders
- sort images by dayPart [day, morning, evening, night, night/moon]
- resize to 224x224
- convert to f with imagick normalize
'''

observatory = ephem.Observer()
# todo move GPS to web
observatory.lat, observatory.lon = '44.791395', '38.583824'

for cond in ['clear', 'cloud']:
	for f in os.listdir('/yolo/'+ cond):
		if f[-4:] == '.fit' and os.path.isfile('/yolo/'+ cond +'/'+ f):
			# todo get datetime from fits header DATE-OBS
			# todo timezone to web config

			# convert time to GMT
			d = datetime.strptime(f[:-4], '%Y-%m-%d_%H-%M') - timedelta(hours=3)
			observatory.date = d.strftime('%Y-%m-%d %H:%M') 

			s = ephem.Sun()
			s.compute(observatory)
			twilight = -12 * ephem.degree
			if s.alt > 0:
				dayPart = 'day'
			elif s.alt > twilight:
				dayPart = 'morning' if d.hour < 12 else 'evening'
			else:
				dayPart = 'night'
				m = ephem.Moon()
				m.compute(observatory)

				if m.alt > 5 * ephem.degree:
					dayPart += '/moon' 

			#print(cond +'/'+ f +' is '+ dayPart)
			pathlib.Path('/yolo/'+ dayPart +'/'+ cond).mkdir(parents=True, exist_ok=True)

			dst = '/yolo/'+ dayPart +'/'+ cond +'/'+ f[0:-3] +'jpg'

			if not os.path.isfile(dst):
				print(dst)
				os.system('convert /yolo/'+ cond +'/'+ f +' -resize 224x224! -normalize -colorspace sRGB -type truecolor '+ dst)

'''
Prepare version:
- for every dayPart, for every condition [cloud|clean]
- make verison-X folder
- devide images into train (70%), valid (20%) and test (10%) pools
- copy jpg as is
- augment it to extra 8 images by random change of brightness, blur and gamma
'''

version = sys.argv[3]

for dayPart in ['day', 'evening', 'morning', 'night', 'night/moon']:

	for cond in ['clear', 'cloud']:
		src = '/yolo/'+ dayPart +'/'+ cond

		files = os.listdir(src)

		rest = count = len(files)
		train = math.ceil(rest * 0.7)
		rest -= train

		valid = 0;

		if rest > 0:
			valid = math.ceil(rest * 0.66)
			rest -= valid

		test = rest

		print(src +"\ttotal="+ str(count) +"\ttrain="+ str(train) +"\tvalid="+ str(valid) +"\ttest="+ str(test))

		random.shuffle(files)

		dst = '/yolo/'+ dayPart +'/version-'+ version +'/'

		for file in files:
			print(str(count) +'/'+ str(len(files)))
			count -= 1

			if train > 0:
				train -= 1
				set = 'train'
			elif valid > 0:
				valid -= 1
				set = 'valid'
			elif test > 0:
				test -= 1
				set = 'test'
			else:
				set = ''

			pathlib.Path(dst +'/'+ set +'/'+ cond +'/').mkdir(parents=True, exist_ok=True)
			shutil.copy2(src +'/'+ file, dst +'/'+ set +'/'+ cond +'/'+ file)

			img = imageio.v2.imread(src +'/'+ file)
			images = np.array(
				[img for _ in range(16)], dtype=np.uint8)

			seq = iaa.Sequential(
				[
					iaa.Sometimes(0.2, iaa.MedianBlur(3, 4)),
					iaa.Sometimes(0.5, iaa.GammaContrast((0.5, 2.0))),
					iaa.Sometimes(0.5, iaa.AddToBrightness((-30, 30))),
					iaa.Fliplr(0.3),
					iaa.Flipud(0.3),
				],
				random_order=True) 

			images_aug = seq.augment_images(images)

			for i in range(16):
				imageio.imwrite(dst +'/'+ set +'/'+ cond +'/'+ str(i) +'-'+ file, images_aug[i])


##### Train
model = YOLO('yolov8'+ sys.argv[1] +'-cls.pt')

for folder in ['day', 'evening', 'morning', 'night', 'night/moon']:

	os.chdir('/yolo/'+ folder)
	model.train(data='version-'+ version, epochs=int(sys.argv[2]), device=0, batch=150, imgsz=224, augment=False)
