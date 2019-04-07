#!/usr/bin/python3

import PyIndi
import time
import sys
import numpy as np
import io
import os
import re
import logging
from astropy.io import fits
from PIL import Image
import cv2
from datetime import datetime, timedelta

import config

import mysql.connector

db = mysql.connector.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'], database=config.db['database'], charset='utf8')
cursor = db.cursor()

binning  = config.ccd['binning']
exposure = 1.0 # init exposure
logging.basicConfig(filename=config.log['path'], level=config.log['level'])

minute = datetime.now().strftime("%Y-%m-%d_%H-%M")

'''
def normalize(arr):
	"""
	Linear normalization
	http://en.wikipedia.org/wiki/Normalization_%28image_processing%29
	"""
	arr = arr.astype('float')
	# Do not touch the alpha channel
	for i in range(3):
		minval = arr[...,i].min()
		maxval = arr[...,i].max()
		if minval != maxval:
			arr[...,i] -= minval
			arr[...,i] *= (255.0/(maxval-minval))
	return arr

def demo_normalize():
    img = Image.open(FILENAME).convert('RGBA')
    arr = np.array(img)
    new_img = Image.fromarray(normalize(arr).astype('uint8'),'RGBA')
    new_img.save('/tmp/normalized.png')
'''

class IndiClient(PyIndi.BaseClient):
	device = None

	def __init__(self):
		super(IndiClient, self).__init__()
	def newDevice(self, d):
		logging.debug('Новое устройство: '+ d.getDeviceName());
		self.device = d
		pass
	def newProperty(self, p):
		pass
	def removeProperty(self, p):
		pass
	def newBLOB(self, bp):
		global exposure

		fit = fits.open( io.BytesIO( bp.getblobdata() ) )
		hdu = fit[0]

		# avg only center (30 - 70% for x and y)
		avg = np.mean(hdu.data[int(hdu.header['NAXIS1'] * 0.3):int(hdu.header['NAXIS1'] * .7),
			int(hdu.header['NAXIS2'] * 0.3):int(hdu.header['NAXIS2'] * .7)])

		logging.info('Получил кадр выдержкой {} сек. со средним {}'.format(exposure, avg))

		if (avg > config.ccd['avgMin'] and avg < config.ccd['avgMax']) or ( (exposure == config.ccd['expMin']) and (avg > config.ccd['avgMin']) ) or ( (exposure == config.ccd['expMax']) and (avg < config.ccd['avgMax']) ):
			# запись

			#data = hdu.data.astype('float')
			minval = hdu.data.min()
			maxval = hdu.data.max()
			if minval != maxval:
				hdu.data -= minval
				hdu.data *= int((255.0 if config.ccd['bits'] == 8 else 65535.0) / (maxval - minval))

			if 'cfa' in config.ccd:
				rgb = cv2.cvtColor(hdu.data, config.ccd['cfa'])
				img = Image.fromarray(rgb, 'RGB')
			else:
				img = Image.fromarray(hdu.data)

			global minute

			img.save(config.path['snap'] + minute +'.jpg')
			logging.info('Файл '+ minute +' записан. Жду следующей минуты')

			ts = int(time.time())
			channel = 0 # мультикамеры

			cursor.execute("""INSERT INTO sensor(date, channel, type, val)
				VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
				"""%{"time":ts, "channel":channel, "type": 'ccd-exposure', "val":exposure})

			cursor.execute("""INSERT INTO sensor(date, channel, type, val)
				VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
				"""%{"time":ts, "channel":channel, "type": 'ccd-average', "val":avg})

			db.commit()

			if os.path.exists(config.path['web'] +'current.jpg'):
				os.remove(config.path['web'] +'current.jpg')
			os.symlink(config.path['snap'] + minute +'.jpg', config.path['web'] +'current.jpg')

			# удаление старых жпегов
			old = datetime.now() - timedelta(config.archive['days'])

			for f in os.listdir(config.path['snap']):
				if os.path.isfile(config.path['snap'] + f):
					result = re.match(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2}).jpg', f)

					if result:
						date = datetime(int(result.group(1)), int(result.group(2)), int(result.group(3)), int(result.group(4)), int(result.group(5)))

						if date < old:
							logging.debug('Файл '+ f +' удалён')
							os.remove(config.path['snap'] + f)

			while True:
				now = datetime.now().strftime("%Y-%m-%d_%H-%M")
				if now != minute:
					break;
				time.sleep(1)

			minute = now

		else:
			# подбор выдержки
			if avg > (250.0 if config.ccd['bits'] == 8 else 65000.0):
				exposure = config.ccd['expMin']
			else:
				if avg > config.ccd['avgMax']:
					exposure /= 1.03318
				else:
					exposure *= 1.04321

				if exposure < config.ccd['expMin']:
					exposure = config.ccd['expMin']
				if exposure > config.ccd['expMax']:
					exposure = config.ccd['expMax']

		global ccd_exposure

		ccd_exposure[0].value = exposure
		self.sendNewNumber(ccd_exposure)

		pass
	def newSwitch(self, svp):
		pass
	def newNumber(self, nvp):
#		print("newNumber ", nvp.name)
		pass
	def newText(self, tvp):
		pass
	def newLight(self, lvp):
		pass
	def newMessage(self, d, m):
		pass
	def serverConnected(self):
		pass
	def serverDisconnected(self, code):
		pass

# connect the server
indiclient = IndiClient()
indiclient.setServer("localhost", 7624)

if (not(indiclient.connectServer())):
	logging.warning('Не найден INDI-сервер камеры')
	sys.exit(1)

logging.debug('INDI нашёл')

ccd = indiclient.getDevice(config.ccd['name'])
while not(ccd):
	time.sleep(0.5)
	ccd = indiclient.getDevice(config.ccd['name'])

logging.debug('CCD нашёл')

ccd_connect = ccd.getSwitch("CONNECTION")
while not(ccd_connect):
	time.sleep(0.5)
	ccd_connect = ccd.getSwitch("CONNECTION")

logging.debug('CCD подключил')

if not(ccd.isConnected()):
	ccd_connect[0].s=PyIndi.ISS_ON  # the "CONNECT" switch
	ccd_connect[1].s=PyIndi.ISS_OFF # the "DISCONNECT" switch
	indiclient.sendNewSwitch(ccd_connect)

#ccd_frame = ccd.getNumber("CCD_FRAME")
#while not(ccd_frame):
#	time.sleep(0.5)
#	ccd_frame = ccd.getNumber("CCD_FRAME")
#
#width  = int(ccd_frame[2].value)
#height = int(ccd_frame[3].value)
#print("Нашёл размер кадра: {}x{}".format(width, height))

ccd_exposure = ccd.getNumber("CCD_EXPOSURE")
while not(ccd_exposure):
	time.sleep(0.5)
	ccd_exposure = ccd.getNumber("CCD_EXPOSURE")

logging.debug('EXPOSURE нашёл')

#ccd_temp = ccd.getNumber("CCD_TEMPERATURE")
#while not(ccd_temp):
#	time.sleep(0.5)
#	ccd_temp = ccd.getNumber("CCD_TEMPERATURE")
#
#logging.debug('TEMPERATURE нашёл')

ccd_binning = ccd.getNumber("CCD_BINNING")
while not(ccd_binning):
	time.sleep(0.5)
	ccd_binning = ccd.getNumber("CCD_BINNING")

logging.debug('BINNING нашёл')

ccd_binning[0].value = binning
ccd_binning[1].value = binning
indiclient.sendNewNumber(ccd_binning)

logging.info('BINNING {} отправил'.format(binning))

ccd_exposure[0].value = exposure
indiclient.sendNewNumber(ccd_exposure)

logging.info('EXPOSURE отправил')

indiclient.setBLOBMode(PyIndi.B_ALSO, config.ccd['name'], "CCD1")

while ccd:
	time.sleep(10)