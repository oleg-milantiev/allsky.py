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
from datetime import datetime, timedelta

import config

import MySQLdb
db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
							 database=config.db['database'], charset='utf8')
db.autocommit(True)
cursor = db.cursor()

binning = config.ccd['binning']
exposure = 5.0  # init exposure
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

		if 'ROI' in config.processing:
			roi = config.processing['ROI']
			logging.debug('Вырезаю ROI: {}-{}, {}-{}'.format(roi['xLeft'], roi['xRight'], roi['yTop'], roi['yBottom']))
			hdu.data = hdu.data[roi['yTop']:roi['yBottom'], roi['xLeft']:roi['xRight']]

		# Подсчёт среднего по центру кадра (ccdAvgMin - ccdAvgMax% for x and y)
		avg = np.mean(hdu.data[int(hdu.header['NAXIS1'] * config.processing['ccdAvgMin']):int(
				hdu.header['NAXIS1'] * config.processing['ccdAvgMax']),
					int(hdu.header['NAXIS2'] * config.processing['ccdAvgMin']):int(
						hdu.header['NAXIS2'] * config.processing['ccdAvgMax'])])
		# если среднее = 0  -  что-то пошло не так и нужно переснять кадр

		logging.info('Получил кадр выдержкой {} сек. со средним {}'.format(exposure, avg))
		if (config.ccd['avgMin'] < avg < config.ccd['avgMax']) or (
				(exposure == config.ccd['expMin']) and (avg > config.ccd['avgMax'])) or (
				(exposure == config.ccd['expMax']) and (avg < config.ccd['avgMin'])):

			# запись
			global minute

			logging.info('Сохраняю кадр в файл fit...')
			hdu.writeto(config.path['fit'] + minute + '.fit', overwrite=True)

			minval = hdu.data.min()
			maxval = hdu.data.max()
			if minval != maxval:
				logging.debug('Нормализую...')
				hdu.data -= minval
				hdu.data = (hdu.data * ((255.0 if config.ccd['bits'] == 8 else 65535.0) / (maxval - minval))).astype('int')

			if 'cfa' in config.ccd:
				import cv2

				logging.debug('Дебаейризую...')
				rgb = cv2.cvtColor(
						hdu.data.astype('uint8') if config.ccd['bits'] == 8 else (hdu.data / 256).astype('uint8'),
						config.ccd['cfa']
				)
				# cv2.imwrite('/sdcard/html/lastrgb.jpg', rgb)

				img2gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
				ret, mask = cv2.threshold(img2gray, 245, 255, cv2.THRESH_BINARY)
				# cv2.imwrite('/sdcard/html/mask.jpg', mask)
				maskInv = cv2.bitwise_not(mask)

				imgOverexposed = cv2.bitwise_and(rgb, rgb, mask=mask)
				# cv2.imwrite('/sdcard/html/overexposed.jpg', imgOverexposed)
				# dst = cv2.add(img1_bg, img2_fg)

				if 'wb' in config.processing:
					logging.debug('Выравниваю баланс белого методом: ' + config.processing['wb'])
					if config.processing['wb'] == 'gain':
						gains = config.processing['wbGains']
						rgb = cv2.xphoto.applyChannelGains(rgb, gains['r'], gains['g'], gains['b'])
					elif config.processing['wb'] == 'simple':
						wb = cv2.xphoto.createSimpleWB()
						rgb = wb.balanceWhite(rgb)
					elif config.processing['wb'] == 'gray':
						wb = cv2.xphoto.createGrayworldWB()
						wb.setSaturationThreshold(0.95)
						rgb = wb.balanceWhite(rgb)

				imgWb = cv2.bitwise_and(rgb, rgb, mask=maskInv)
				img = Image.fromarray(cv2.add(imgWb, imgOverexposed), 'RGB')
			else:
				img = Image.fromarray(hdu.data if config.ccd['bits'] == 8 else (hdu.data / 256).astype('uint8'))

			if 'logo' in config.processing:
				logging.debug('Дообавляю лого...')

				watermark = Image.open(config.processing['logo']['fileName'])

				img.paste(watermark, (config.processing['logo']['x'], config.processing['logo']['y']), watermark)

			savedDate = datetime.now()

			if config.annotations:
				logging.debug('Добавляю аннотации')

				txt = Image.new('RGBA', img.size, (255, 255, 255, 0))
				d = ImageDraw.Draw(txt)

				for annotation in config.annotations:
					font = ImageFont.truetype('sans-serif.ttf', annotation['size'])

					match annotation['type']:
						case 'text': text = annotation['text']
						case 'datetime': text = savedDate.strftime(annotation['format'])
						case 'avg' | 'average':  text = annotation['format'].format(avg)
						case 'exposure':  text = annotation['format'].format(exposure)
						case _: text = ''

					d.text(
							(annotation['x'], annotation['y']),
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

			if os.path.islink(config.path['web'] + 'current.jpg'):
				os.remove(config.path['web'] + 'current.jpg')
			os.symlink(config.path['jpg'] + minute + '.jpg', config.path['web'] + 'current.jpg')

			# @todo вынести всё сопутствующее в отдельный поток

			# публикация последнего jpg
			if 'jpg' in config.publish:
				try:
					import requests

					r = requests.post(
						config.publish['jpg'],
						files={'file': open(config.path['jpg'] + minute + '.jpg', 'rb')},
						data={'name': config.name, 'pass': 'kjH3vxzm4G'}
					)
					logging.info('Файл ' + minute + ' опубликован: ' + r.text)
				except:
					logging.info('ОШИБКА публикации файла ' + minute)

			# удаление старых жпегов и фитов
			for folder in ['jpg', 'fit']:
				old = datetime.now() - timedelta(config.archive[folder])

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
			if avg > (250.0 if config.ccd['bits'] == 8 else 65000.0):
				exposure = config.ccd['expMin']
			elif avg < 0.001:
				exposure = config.ccd['expMin'] + (config.ccd['expMax'] - config.ccd['expMin']) / 2
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
indi.setServer(config.indi['host'], config.indi['port'])

if not indi.connectServer():
	logging.warning('Не найден INDI-сервер камеры')
	sys.exit(1)

logging.debug('INDI нашёл')

retries = 10
ccd = indi.getDevice(config.ccd['name'])
while not ccd:
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

retries = 10
ccd_binning = ccd.getNumber("CCD_BINNING")
while not ccd_binning:
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

	logging.debug('Реле обогрева {}'.format('включено' if state == 1 else 'выключено'));


while ccd:
	# watchdog не контролирует время начального подбора выдержки - оно может быть значительным
	if savedDate and (savedDate + timedelta(seconds=600)) < datetime.now():
		# а потом проверяет давно ли получен кадр
		logging.error('Уже 10 минут камера не записывает кадры. Попытка рестарта allsky.py через supervisord')
		sys.exit(1)

	if hotter:
		if hotter['stage'] == 0:
			import json

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
