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
from PIL import Image, ImageDraw, ImageFont
import cv2
from datetime import datetime, timedelta
import requests

import config

import mysql.connector

db = mysql.connector.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'], database=config.db['database'], charset='utf8')
cursor = db.cursor(dictionary=True)

binning  = config.ccd['binning']
exposure = 1.0 # init exposure
logging.basicConfig(filename=config.log['path'], level=config.log['level'])

minute = datetime.now().strftime("%Y-%m-%d_%H-%M")
savedDate = None

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
		

		logging.debug('Получаю новый кадр...')

		fit = fits.open( io.BytesIO( bp.getblobdata() ) )
		hdu = fit[0]

		if 'ROI' in config.processing:
			roi = config.processing['ROI']
			logging.debug('вырезаю ROI: {}-{}, {}-{}'.format(roi['x0'], roi['x1'], roi['y0'], roi['y1']))
			hdu.data = hdu.data[roi['y0']:roi['y1'],roi['x0']:roi['x1']]

		# avg only center (ccdAvgMin - ccdAvgMax% for x and y)
		avg = np.mean(hdu.data[int(hdu.header['NAXIS1'] * config.processing['ccdAvgMin']):int(hdu.header['NAXIS1'] * config.processing['ccdAvgMax']),
			int(hdu.header['NAXIS2'] * config.processing['ccdAvgMin']):int(hdu.header['NAXIS2'] * config.processing['ccdAvgMax'])])
		# если среднее = 0  -  что-то пошло не так и нужно переснять кадр

		logging.info('Получил кадр выдержкой {} сек. со средним {}'.format(exposure, avg))
		if (avg > config.ccd['avgMin'] and avg < config.ccd['avgMax']) or ( (exposure == config.ccd['expMin']) and (avg > config.ccd['avgMax']) ) or ( (exposure == config.ccd['expMax']) and (avg < config.ccd['avgMin']) ):
			# запись
			global minute

			if 'days' in config.fits:
				logging.info('Сохраняю кадр в файл fits...')
				hdu.writeto(config.path['fits']+minute + '.fits', overwrite=True)

			data = hdu.data.astype('float')
			minval = hdu.data.min()
			maxval = hdu.data.max()
			if minval != maxval:
				logging.debug('Нормализую...')
				hdu.data -= minval
				floatdata = hdu.data * ((255.0 if config.ccd['bits'] == 8 else 65535.0) / (maxval - minval))
				hdu.data = floatdata.astype('int')

			if 'cfa' in config.ccd:
				logging.debug('Дебаейризация...')
				rgb = cv2.cvtColor(
					hdu.data if config.ccd['bits'] == 8 else (hdu.data/256).astype('uint8'),
					config.ccd['cfa']
				)
				#cv2.imwrite('/sdcard/html/lastrgb.jpg', rgb)
				
				img2gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
				ret, mask = cv2.threshold(img2gray, 245, 255, cv2.THRESH_BINARY)
				#cv2.imwrite('/sdcard/html/mask.jpg', mask)
				mask_inv = cv2.bitwise_not(mask)

				img_overexposed = cv2.bitwise_and(rgb, rgb, mask=mask)
				#cv2.imwrite('/sdcard/html/overexposed.jpg', img_overexposed)
				# dst = cv2.add(img1_bg, img2_fg)
				
				if 'wb' in config.processing:
					if config.processing['wb'] == 'gain':
						logging.debug('выравниваю баланс белого гейнами...')
						gains = config.processing['wb_gains']
						rgb = cv2.xphoto.applyChannelGains(rgb, gains['r'], gains['g'], gains['b'])
					elif config.processing['wb']=='simple':
						logging.debug('выравниваю баланс белого через SimpleWB')
						wb = cv2.xphoto.createSimpleWB()
						rgb = wb.balanceWhite(rgb)
					elif config.processing['wb']=='gray':
						logging.debug('выравниваю баланс белого через GrayWorldWB')
						wb = cv2.xphoto.createGrayworldWB()
						wb.setSaturationThreshold(0.95)
						rgb = wb.balanceWhite(rgb)

				img_wb = cv2.bitwise_and(rgb, rgb, mask=mask_inv)
				#cv2.imwrite('/sdcard/html/wb.jpg', img_wb)
				dst = cv2.add(img_wb, img_overexposed)
				#cv2.imwrite('/sdcard/html/res.jpg', dst)

				
				if config.logo:
					logging.debug('Дообавляю лого...')
					logo = cv2.imread(config.logo['logoFileName'])
					img2gray = cv2.cvtColor(logo, cv2.COLOR_BGR2GRAY)
					ret, mask = cv2.threshold(img2gray, 10, 255, cv2.THRESH_BINARY)
					#cv2.imwrite('/sdcard/html/mask.jpg', mask)
					mask_inv = cv2.bitwise_not(mask)

					img_mask = cv2.bitwise_and(dst, dst, mask=mask_inv)
					#cv2.imwrite('/sdcard/html/res_minus.jpg', dst)
					logo_mask = cv2.bitwise_and(logo, logo, mask=mask)
					
					dst = cv2.add(img_mask, logo_mask)


				img = Image.fromarray(dst, 'RGB')
			else:
				img = Image.fromarray(hdu.data if config.ccd['bits'] == 8 else (hdu.data/256).astype('uint8') )

			savedDate = datetime.now()

			if config.timestamp:
				logging.debug('Добавляю таймстемп')
				txt = Image.new('RGBA', img.size, (255,255,255,0))
				d = ImageDraw.Draw(txt)
				fnt = ImageFont.truetype('sans-serif.ttf', 20)
				clr = (255,255,255,255)
				for line in config.timestamp:
					fnt = ImageFont.truetype('sans-serif.ttf', line['size'])
					clr = line['color']
					d.text(
						(line['x'], line['y']),
						savedDate.strftime(line['format']),
						font=fnt, fill=clr)

			if config.picture_acquisition:
				logging.debug('Добавляю данные о снимке')
				line = config.picture_acquisition[0]
				d.text( (line['x'], line['y']), 'EXP:{:.4f}'.format(exposure), font=ImageFont.truetype('sans-serif.ttf', line['size']), fill=line['color'])
				line = config.picture_acquisition[1]
				d.text( (line['x'], line['y']), 'CCD_avg:{:.0f}'.format(avg), font=ImageFont.truetype('sans-serif.ttf', line['size']), fill=line['color'])
				
				img = Image.alpha_composite(img.convert('RGBA'), txt).convert('RGB')

			logging.debug('Записываю jpg в файл...')
			filename = config.path['snap'] + minute
			img.save(filename + '.jpg')
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

			if os.path.islink(config.path['web'] +'current.jpg'):
				os.remove(config.path['web'] +'current.jpg')
			os.symlink(config.path['snap'] + minute +'.jpg', config.path['web'] +'current.jpg')

			# @todo вынести всё сопутствующее в отдельный поток

			# публикация последнего jpg
			if 'jpg' in config.publish:
				try:
					r = requests.post(config.publish['jpg'], files={'file': open(config.path['snap'] + minute +'.jpg', 'rb')}, data={'name': config.name, 'pass': 'kjH3vxzm4G'})
					logging.info('Файл '+ minute +' опубликован: '+ r.text)
				except:
					logging.info('ОШИБКА публикации файла '+ minute)			

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

			# удаление старых фитсов
			old = datetime.now() - timedelta(config.fits['days'])

			for f in os.listdir(config.path['fits']):
				if os.path.isfile(config.path['fits'] + f):
					result = re.match(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2}).fits', f)

					if result:
						date = datetime(int(result.group(1)), int(result.group(2)), int(result.group(3)), int(result.group(4)), int(result.group(5)))

						if date < old:
							logging.debug('Файл '+ f +' удалён')
							os.remove(config.path['fits'] + f)


			while True:
				now = datetime.now().strftime("%Y-%m-%d_%H-%M")
				if now != minute:
					break;
				time.sleep(1)

			minute = now

		else:
			# подбор выдержки
			logging.debug('Подбор выдержки...')
			if avg > (250.0 if config.ccd['bits'] == 8 else 65000.0):
				exposure = config.ccd['expMin']
			elif avg < 0.001:
				exposure = config.ccd['expMin'] + (config.ccd['expMax']-config.ccd['expMin'])/2
			else:
				target = (config.ccd['avgMax'] - config.ccd['avgMin']) / 2 + config.ccd['avgMin']
				exposure = target * exposure / avg
				# @todo защита от зацикливания

				if exposure < config.ccd['expMin']:
					exposure = config.ccd['expMin']
				if exposure > config.ccd['expMax']:
					exposure = config.ccd['expMax']
			logging.info('Новая выдержка {}'.format(exposure))

		global ccd_exposure

		ccd_exposure[0].value = exposure
		self.sendNewNumber(ccd_exposure)

		logging.info('Получение кадра закончено.')

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

#------------------ начало ---------------------

#logging.debug('{}: Реле обогрева {} ({}%)'.format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S")))

indi = IndiClient()
indi.setServer("localhost", 7624)

if (not(indi.connectServer())):
	logging.warning('Не найден INDI-сервер камеры')
	sys.exit(1)

logging.debug('INDI нашёл')

retries = 10
ccd = indi.getDevice(config.ccd['name'])
while not(ccd):
	retries -= 1
	if retries == 0:
		logging.error('INDI завис, пробую перезапустить')
		os.system('/etc/init.d/indi restart')
		sys.exit(1)
	time.sleep(0.5)
	ccd = indi.getDevice(config.ccd['name'])

logging.debug('CCD увидел в списке')

retries = 10
ccd_connect = ccd.getSwitch("CONNECTION")
while not(ccd_connect):
	retries -= 1
	if retries == 0:
		logging.error('Не получаю CONNECTION')
		# @todo и что делать?
		sys.exit(1)
	time.sleep(0.5)
	ccd_connect = ccd.getSwitch("CONNECTION")

logging.debug('CCD нашёл')

if not(ccd.isConnected()):
	ccd_connect[0].s=PyIndi.ISS_ON  # the "CONNECT" switch
	ccd_connect[1].s=PyIndi.ISS_OFF # the "DISCONNECT" switch
	indi.sendNewSwitch(ccd_connect)

logging.debug('CCD подключил')
#ccd_frame = ccd.getNumber("CCD_FRAME")
#while not(ccd_frame):
#	time.sleep(0.5)
#	ccd_frame = ccd.getNumber("CCD_FRAME")
#
#width  = int(ccd_frame[2].value)
#height = int(ccd_frame[3].value)
#print("Нашёл размер кадра: {}x{}".format(width, height))

retries = 10
ccd_exposure = ccd.getNumber("CCD_EXPOSURE")
while not(ccd_exposure):
	retries -= 1
	if retries == 0:
		logging.error('Похоже, камера зависла')
		#lsusb -> bus 001, dev 005
		#fxload -t fx2 -D /dev/bus/usb/001/005 -I /lib/firmware/qhy/QHY5LOADER.HEX -v
		#os.system('reboot')
		sys.exit(1)
	time.sleep(0.5)
	ccd_exposure = ccd.getNumber("CCD_EXPOSURE")

logging.debug('EXPOSURE нашёл')

#ccd_temp = ccd.getNumber("CCD_TEMPERATURE")
#while not(ccd_temp):
#	time.sleep(0.5)
#	ccd_temp = ccd.getNumber("CCD_TEMPERATURE")
#
#logging.debug('TEMPERATURE нашёл')

retries = 10
ccd_binning = ccd.getNumber("CCD_BINNING")
while not(ccd_binning):
	retries -= 1
	if retries == 0:
		logging.error('Не могу получить CCD_BINNING')
		sys.exit(1)
	time.sleep(0.5)
	ccd_binning = ccd.getNumber("CCD_BINNING")

logging.debug('BINNING нашёл')

ccd_binning[0].value = binning
ccd_binning[1].value = binning
indi.sendNewNumber(ccd_binning)

logging.info('BINNING {} отправил'.format(binning))

ccd_exposure[0].value = exposure
indi.sendNewNumber(ccd_exposure)

logging.info('EXPOSURE отправил')

indi.setBLOBMode(PyIndi.B_ALSO, config.ccd['name'], "CCD1")

logging.info('setBLOB отправил')


hotter = None

for relay in config.relay:
	if 'hotter' in relay:
		import json

		hotter = relay
		hotter['stage'] = 0
		hotter['state'] = 0
		hotter['percent'] = 0
		break

def hotterRelay(state):
	global hotter, db, cursor

	hotter['state'] = state

	f = open('/sys/class/gpio/gpio{}/value'.format(hotter['gpio']), 'wt')
	f.write('{}'.format(state))
	f.close()

	ts = int(time.time())
	cursor.execute('replace into relay (id, state, date) values ("{}", {}, {})'.format(hotter['name'], state, ts))
	db.commit()

	logging.debug('Реле обогрева {}'.format('включено' if state == 1 else 'выключено' ) );


while ccd:
	# watchdog не контролирует время начального подбора выдержки - оно может быть значительным
	if (savedDate and (savedDate + timedelta(seconds=600)) < datetime.now()):
		# а потом проверяет давно ли получен кадр
		logging.error('Уже 10 минут камера не записывает кадры. Попытка рестарта allsky.py через supervisord')
		sys.exit(1)


	if hotter:
		if hotter['stage'] == 0:
			cursor.execute('select val from config where id = "hotPercent"')
			row = cursor.fetchone()

			hotter['percent'] = int(json.loads(row['val'])) if row else 0
			if hotter['percent'] > 0:
				hotterRelay(1)

		hotter['stage'] += 1

		if (hotter['stage'] * 10) > hotter['percent'] and hotter['state'] == 1:
			hotterRelay(0)

		if hotter['stage'] == 10:
			hotter['stage'] = 0
	time.sleep(6)
