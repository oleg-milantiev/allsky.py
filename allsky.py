#!/usr/bin/python3

import PyIndi
import time
import sys
import numpy as np
import io
import os
import re
import logging
import json
from astropy.io import fits
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

import config

import mysql.connector

db = mysql.connector.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
							 database=config.db['database'], charset='utf8')
cursor = db.cursor(dictionary=True)

web = {}
cursor.execute('select id, val from config')
for row in cursor.fetchall():
	web[row['id']] = json.loads(row['val'])

exposure = 1.0  # init exposure
logging.basicConfig(filename=config.log['path'], level=config.log['level'])

minute = datetime.now().strftime("%Y-%m-%d_%H-%M")
savedDate = None


class IndiClient(PyIndi.BaseClient):
	device = None

	def __init__(self):
		super(IndiClient, self).__init__()

	def newDevice(self, d):
		logging.debug('Новое устройство: ' + d.getDeviceName())
		self.device = d
		pass

	def newProperty(self, p):
		pass

	def removeProperty(self, p):
		pass

	def newBLOB(self, bp):
		global exposure

		logging.debug('Получаю новый кадр...')

		fit = fits.open(io.BytesIO(bp.getblobdata()))
		hdu = fit[0]

		if 'processing' in web and 'crop' in web['processing']:
			crop = web['processing']['crop']
			logging.debug('Вырезаю CROP: {}-{}, {}-{}'.format(crop['left'], crop['right'], crop['top'], crop['bottom']))
			hdu.data = hdu.data[crop['left']:(hdu.header['NAXIS1'] - crop['right']), crop['top']:(hdu.header['NAXIS2'] - crop['bottom'])]

		# Подсчёт среднего по центру кадра
		center = 50
		if 'ccd' in web and 'center' in web['ccd']:
			center = web['ccd']['center']

		if 0 < center <= 100:
			logging.debug('Среднее по центральным {}%'.format(center))
			avg = np.mean(hdu.data[
				int(hdu.data.shape[0] * (50 - center / 2) / 100):int(hdu.data.shape[0] * (50 + center / 2) / 100),
				int(hdu.data.shape[1] * (50 - center / 2) / 100):int(hdu.data.shape[1] * (50 + center / 2) / 100)])
		# если среднее = 0  -  что-то пошло не так и нужно переснять кадр

		logging.info('Получил кадр выдержкой {} сек. со средним {}'.format(exposure, avg))
		if (web['ccd']['avgMin'] < avg < web['ccd']['avgMax']) or (
				(exposure == web['ccd']['expMin']) and (avg > web['ccd']['avgMax'])) or (
				(exposure == web['ccd']['expMax']) and (avg < web['ccd']['avgMin'])):

			# запись
			global minute

			logging.info('Сохраняю кадр в файл fit...')
			hdu.writeto(config.path['fit'] + minute + '.fit', overwrite=True)

			minval = hdu.data.min()
			maxval = hdu.data.max()
			if minval != maxval:
				logging.debug('Нормализую...')
				hdu.data -= minval
				hdu.data = (hdu.data * ((255.0 if web['ccd']['bits'] == 8 else 65535.0) / (maxval - minval))).astype('int')

			if 'cfa' in web['ccd']:
				import cv2

				logging.debug('Дебаейризую...')
				rgb = cv2.cvtColor(
						hdu.data.astype('uint8') if web['ccd']['bits'] == 8 else (hdu.data / 256).astype('uint8'),
						web['ccd']['cfa']
				)
				# cv2.imwrite('/sdcard/html/lastrgb.jpg', rgb)

				img2gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
				ret, mask = cv2.threshold(img2gray, 245, 255, cv2.THRESH_BINARY)
				# cv2.imwrite('/sdcard/html/mask.jpg', mask)
				maskInv = cv2.bitwise_not(mask)

				imgOverexposed = cv2.bitwise_and(rgb, rgb, mask=mask)
				# cv2.imwrite('/sdcard/html/overexposed.jpg', imgOverexposed)
				# dst = cv2.add(img1_bg, img2_fg)

				if 'wb' in web['processing'] and 'type' in web['processing']['wb']:
					logging.debug('Выравниваю баланс белого методом: ' + web['processing']['wb']['type'])
					if web['processing']['wb']['type'] == 'gain':
						rgb = cv2.xphoto.applyChannelGains(rgb, web['processing']['wb']['r'], web['processing']['wb']['g'], web['processing']['wb']['b'])
					elif web['processing']['wb']['type'] == 'simple':
						wb = cv2.xphoto.createSimpleWB()
						rgb = wb.balanceWhite(rgb)
					elif web['processing']['wb']['type'] == 'gray':
						wb = cv2.xphoto.createGrayworldWB()
						wb.setSaturationThreshold(0.95)
						rgb = wb.balanceWhite(rgb)

				imgWb = cv2.bitwise_and(rgb, rgb, mask=maskInv)
				img = Image.fromarray(cv2.add(imgWb, imgOverexposed), 'RGB')
			else:
				img = Image.fromarray(hdu.data if web['ccd']['bits'] == 8 else (hdu.data / 256).astype('uint8'))

			if 'logo' in web['processing'] and 'file' in web['processing']['logo']:
				logging.debug('Дообавляю лого...')

				watermark = Image.open('/opt/allsky.py/var-www-html/' + web['processing']['logo']['file'])

				img.paste(watermark, (web['processing']['logo']['x'], web['processing']['logo']['y']))

			savedDate = datetime.now()

			if 'annotation' in web['processing']:
				logging.debug('Добавляю аннотации')

				txt = Image.new('RGBA', img.size, (255, 255, 255, 0))
				d = ImageDraw.Draw(txt)

				for annotation in web['processing']['annotation']:
					font = ImageFont.truetype('sans-serif.ttf', int(annotation['size']))

					match annotation['type']:
						case 'text': text = annotation['format']
						case 'datetime': text = savedDate.strftime(annotation['format'])
						case 'avg' | 'average':  text = annotation['format'].format(avg)
						case 'exposure':  text = annotation['format'].format(exposure)
						case _: text = ''

					d.text(
						(int(annotation['x']), int(annotation['y'])),
						text,
						font=font,
						fill=annotation['color']
					)

				img = Image.alpha_composite(img.convert('RGBA'), txt).convert('RGB')

			logging.debug('Записываю jpg в файл...')
			filename = config.path['jpg'] + minute
			img.save(filename + '.jpg')
			logging.info('Файл ' + minute + ' записан. Жду следующей минуты')

			ts = int(time.time())
			channel = 0  # мультикамеры

			cursor.execute("""INSERT INTO sensor(date, channel, type, val)
				VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
				""" % {"time": ts, "channel": channel, "type": 'ccd-exposure', "val": exposure})

			cursor.execute("""INSERT INTO sensor(date, channel, type, val)
				VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
				""" % {"time": ts, "channel": channel, "type": 'ccd-average', "val": avg})

			db.commit()

			if os.path.islink(config.path['web'] + 'current.jpg'):
				os.remove(config.path['web'] + 'current.jpg')
			os.symlink(config.path['jpg'] + minute + '.jpg', config.path['web'] + 'current.jpg')

			# @todo вынести всё сопутствующее в отдельный поток

			# публикация последнего jpg
			if 'jpg' in web['publish']:
				try:
					import requests

					r = requests.post(
						web['publish']['jpg'],
						files={'file': open(config.path['jpg'] + minute + '.jpg', 'rb')},
						data={'name': web['web']['name'], 'pass': 'kjH3vxzm4G'}
					)
					logging.info('Файл ' + minute + ' опубликован: ' + r.text)
				except:
					logging.info('ОШИБКА публикации файла ' + minute)

			# удаление старых жпегов и фитов
			for folder in ['jpg', 'fit']:
				old = datetime.now() - timedelta(web['archive'][folder])

				for f in os.listdir(config.path[folder]):
					if os.path.isfile(config.path[folder] + f):
						result = re.match(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2}).' + folder, f)

						if result:
							date = datetime(int(result.group(1)), int(result.group(2)), int(result.group(3)),
											int(result.group(4)), int(result.group(5)))

							if date < old:
								logging.debug('Файл ' + f + ' удалён')
								os.remove(config.path[folder] + f)

			while True:
				now = datetime.now().strftime("%Y-%m-%d_%H-%M")
				if now != minute:
					break
				time.sleep(1)

			minute = now

		else:
			# подбор выдержки
			logging.debug('Подбор выдержки...')
			if avg > (250.0 if web['ccd']['bits'] == 8 else 65000.0):
				exposure = web['ccd']['expMin']
			elif avg < 0.001:
				exposure = web['ccd']['expMin'] + (web['ccd']['expMax'] - web['ccd']['expMin']) / 2
			else:
				target = (web['ccd']['avgMax'] - web['ccd']['avgMin']) / 2 + web['ccd']['avgMin']
				exposure = target * exposure / avg
				# @todo защита от зацикливания

				if exposure < web['ccd']['expMin']:
					exposure = web['ccd']['expMin']
				if exposure > web['ccd']['expMax']:
					exposure = web['ccd']['expMax']
			logging.info('Новая выдержка {}'.format(exposure))

		global ccd_exposure

		ccd_exposure[0].value = exposure
		self.sendNewNumber(ccd_exposure)

		logging.info('Получение кадра закончено')

		pass

	def newSwitch(self, svp):
		pass

	def newNumber(self, nvp):
		# print("newNumber ", nvp.name)
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


# ------------------ начало ---------------------

# logging.debug('{}: Реле обогрева {} ({}%)'.format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S")))

indi = IndiClient()
indi.setServer("localhost", 7624)

if not indi.connectServer():
	logging.warning('Не найден INDI-сервер камеры')
	sys.exit(1)

logging.debug('INDI нашёл')

retries = 10
ccd = indi.getDevice(web['ccd']['name'])
while not ccd:
	retries -= 1
	if retries == 0:
		logging.error('INDI завис, пробую перезапустить')
		os.system('/etc/init.d/indi restart')
		sys.exit(1)
	time.sleep(0.5)
	ccd = indi.getDevice(web['ccd']['name'])

logging.debug('CCD увидел в списке')

retries = 10
ccd_connect = ccd.getSwitch("CONNECTION")
while not ccd_connect:
	retries -= 1
	if retries == 0:
		logging.error('Не получаю CONNECTION')
		# @todo и что делать?
		sys.exit(1)
	time.sleep(0.5)
	ccd_connect = ccd.getSwitch("CONNECTION")

logging.debug('CCD нашёл')

if not ccd.isConnected():
	ccd_connect[0].s = PyIndi.ISS_ON  # the "CONNECT" switch
	ccd_connect[1].s = PyIndi.ISS_OFF  # the "DISCONNECT" switch
	indi.sendNewSwitch(ccd_connect)

logging.debug('CCD подключил')

retries = 10
ccd_exposure = ccd.getNumber("CCD_EXPOSURE")
while not ccd_exposure:
	retries -= 1
	if retries == 0:
		logging.error('Похоже, камера зависла')
		# lsusb -> bus 001, dev 005
		# fxload -t fx2 -D /dev/bus/usb/001/005 -I /lib/firmware/qhy/QHY5LOADER.HEX -v
		# os.system('reboot')
		sys.exit(1)
	time.sleep(0.5)
	ccd_exposure = ccd.getNumber("CCD_EXPOSURE")

logging.debug('EXPOSURE нашёл')

# ccd_temp = ccd.getNumber("CCD_TEMPERATURE")
# while not(ccd_temp):
#	time.sleep(0.5)
#	ccd_temp = ccd.getNumber("CCD_TEMPERATURE")
#
# logging.debug('TEMPERATURE нашёл')

hasBinning = True
retries = 10
ccd_binning = ccd.getNumber("CCD_BINNING")
while not ccd_binning:
	retries -= 1
	if retries == 0:
		hasBinning = False
		logging.error('Не могу получить CCD_BINNING')
		break
	time.sleep(0.5)
	ccd_binning = ccd.getNumber("CCD_BINNING")

if hasBinning:
	logging.debug('BINNING нашёл')
	ccd_binning[0].value = web['ccd']['binning']
	ccd_binning[1].value = web['ccd']['binning']
	indi.sendNewNumber(ccd_binning)
	logging.info('BINNING {} отправил'.format(web['ccd']['binning']))

ccd_exposure[0].value = exposure
indi.sendNewNumber(ccd_exposure)

logging.info('EXPOSURE отправил')

indi.setBLOBMode(PyIndi.B_ALSO, web['ccd']['name'], "CCD1")

logging.info('setBLOB отправил')

hotter = None

###### TBD перенести в отдельный модуль ######
# for relay in web['relays']:
# 	if relay['hotter']:
# 		hotter = relay
# 		hotter['stage'] = 0
# 		hotter['state'] = 0
# 		hotter['percent'] = 0
# 		break
#
#
# def hotterRelay(state):
# 	global hotter, db, cursor
#
# 	hotter['state'] = state
#
# 	f = open('/sys/class/gpio/gpio{}/value'.format(hotter['gpio']), 'wt')
# 	f.write('{}'.format(state))
# 	f.close()
#
# 	ts = int(time.time())
# 	cursor.execute('replace into relay (id, state, date) values ("{}", {}, {})'.format(hotter['name'], state, ts))
# 	db.commit()
#
# 	logging.debug('Реле обогрева {}'.format('включено' if state == 1 else 'выключено'));
###### / TBD перенести в отдельный модуль ######

while ccd:
	# watchdog не контролирует время начального подбора выдержки - оно может быть значительным
	if savedDate and (savedDate + timedelta(seconds=600)) < datetime.now():
		# а потом проверяет давно ли получен кадр
		logging.error('Уже 10 минут камера не записывает кадры. Попытка рестарта allsky.py через supervisord')
		sys.exit(1)

###### TBD перенести в отдельный модуль ######
###### TBD переделать в температуру, не в процент (по какому датчику?) ######
	# if hotter:
		# if hotter['stage'] == 0:
		# 	cursor.execute('select val from config where id = "hotPercent"')
		# 	row = cursor.fetchone()
		#
		# 	hotter['percent'] = int(json.loads(row['val'])) if row else 0
		# 	if hotter['percent'] > 0:
		# 		hotterRelay(1)
		#
		# hotter['stage'] += 1
		#
		# if (hotter['stage'] * 10) > hotter['percent'] and hotter['state'] == 1:
		# 	hotterRelay(0)
		#
		# if hotter['stage'] == 10:
		# 	hotter['stage'] = 0
###### / TBD перенести в отдельный модуль ######

	time.sleep(6)
