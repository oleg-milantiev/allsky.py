#!/usr/bin/python3

import config
import os
import pika
import re
import requests
import scipy
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
import signal
import sys
import time
import json
import MySQLdb
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from astropy.io import fits
from datetime import datetime
from collections.abc import Iterable


def terminate(signal,frame):
	print("Start Terminating: %s" % datetime.now())
	sys.exit(0)

signal.signal(signal.SIGTERM, terminate)


logging.basicConfig(filename=config.log['path'], level=config.log['level'])

logging.info('[+] Start')

db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
	 database=config.db['database'], charset='utf8')

cursor = db.cursor()

web = {}
cursor.execute('select id, val from config')
for row in cursor.fetchall():
	web[row[0]] = json.loads(row[1])

connection = pika.BlockingConnection(
	pika.ConnectionParameters(
		os.getenv('RABBITMQ_HOST'),
		os.getenv('RABBITMQ_PORT'),
		'/',
		pika.PlainCredentials(
			os.getenv('RABBITMQ_DEFAULT_USER'),
			os.getenv('RABBITMQ_DEFAULT_PASS'))))

channel = connection.channel()

channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_PROCESS'), durable=True)
channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_PROCESS'), durable=True)
print(' [*] Waiting for messages. To exit press CTRL+C')

def callback(ch, method, properties, body):
	print(" [x] Received %r" % body.decode())

	if not re.match(r"\d\d\d\d-\d\d-\d\d_\d\d-\d\d", body.decode()):
		logging.error('[!] Неверный входной формат файла')
		ch.basic_ack(delivery_tag=method.delivery_tag)
		return

	try:
		fit = fits.open('/fits/'+ body.decode() +'.fit', mode='update')
		hdu = fit[0]
	except:
		logging.error('[!] Не могу открыть fit')
		ch.basic_ack(delivery_tag=method.delivery_tag)
		return

	stars = None

	if 'sd' in web['processing'] and 'enable' in web['processing']['sd'] and web['processing']['sd']['enable']:
		logging.info('Считаю звёзды')
		mean, median, std = sigma_clipped_stats(hdu.data, sigma=3.0)
		hdu.header.set('MEAN', mean, 'Mean by whole image')
		hdu.header.set('MEDIAN', median, 'Median by whole image')
		hdu.header.set('STD-DEV', std, 'Std.dev by whole image')

		if float(hdu.header['EXPTIME']) > float(float(web['ccd']['expMin']) + (float(web['ccd']['expMax']) - float(web['ccd']['expMin'])) * 0.75):
			daofind = DAOStarFinder(fwhm=float(web['processing']['sd']['fwhm']), threshold=float(web['processing']['sd']['threshold'])*std)
			stars = daofind(hdu.data - median)
			if stars is not None:
				logging.debug('Посчитал звёзды: mean={}, median={}, std={}, stars={}'.format(mean, median, std, len(stars)))
				hdu.header.set('STAR-CNT', len(stars), 'Stars count by whole image using DAOStarFinder')

	if 'cfa' in web['ccd']:
		import cv2

		logging.warning('Дебаейризую...')
		rgb = cv2.cvtColor(
				hdu.data.astype('uint8') if web['ccd']['bits'] == 8 else (hdu.data / 256).astype('uint8'),
				web['ccd']['cfa']
		)

		img2gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
		ret, mask = cv2.threshold(img2gray, 245, 255, cv2.THRESH_BINARY)
		maskInv = cv2.bitwise_not(mask)

		imgOverexposed = cv2.bitwise_and(rgb, rgb, mask=mask)

		if 'wb' in web['processing'] and 'type' in web['processing']['wb']:
			logging.warning('Выравниваю баланс белого методом: ' + web['processing']['wb']['type'])
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

	# todo полезно. Но нужно ли всем? Цифры точно нужно настраивать
	gamma = 0.5
	img = img.point(lambda x: int(((x/255)**gamma)*255))
	img = ImageOps.autocontrast(img, cutoff=0.1)

	if 'transpose' in web['processing'] and 6 >= web['processing']['transpose'] >= 0:
		logging.debug('Транспонирую (поворот / зеркало)')
		img = img.transpose(web['processing']['transpose'])

	bin = int(hdu.header['XBINNING'] if 'XBINNING' in hdu.header else 1)

	if 'logo' in web['processing'] and 'file' in web['processing']['logo']:
		logging.warning('Дообавляю лого...')

		watermark = Image.open(config['path']['jpg'] +'/'+ web['processing']['logo']['file'])

		img.paste(watermark, (int(web['processing']['logo']['x'] / bin), int(web['processing']['logo']['y'] / bin)))

	dateObs = datetime.strptime(hdu.header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S')

	if 'annotation' in web['processing'] and isinstance(web['processing']['annotation'], Iterable) and len(web['processing']['annotation']) > 0:
		logging.info('Добавляю аннотации')

		txt = Image.new('RGBA', img.size, (255, 255, 255, 0))
		d = ImageDraw.Draw(txt)

		for annotation in web['processing']['annotation']:
			font = ImageFont.truetype('/camera/sans-serif.ttf', int(int(annotation['size']) / bin))

			match annotation['type']:
				case 'stars': text = annotation['format'].format(len(stars) if stars is not None else 'n/a')
				case 'yolo-clear': text = annotation['format'].format('%0.2f' % (float(hdu.header['AI-CLEAR']) * 100) if 'AI-CLEAR' in hdu.header else 'n/a')
				case 'yolo-cloud': text = annotation['format'].format('%0.2f' % (float(hdu.header['AI-CLOUD']) * 100) if 'AI-CLOUD' in hdu.header else 'n/a')
				case 'text': text = annotation['format']
				case 'datetime': text = dateObs.strftime(annotation['format'])
				case 'avg' | 'average':  text = annotation['format'].format(avg)
				case 'exposure':  text = annotation['format'].format(exposure)
				case _: text = ''

			d.text(
				(int(int(annotation['x']) / bin), int(int(annotation['y']) / bin)),
				text,
				font=font,
				fill=annotation['color']
			)

		img = Image.alpha_composite(img.convert('RGBA'), txt).convert('RGB')

	fit.close()

	logging.debug('Записываю jpg в файл...')
	img.save('/snap/'+ body.decode()  +'.jpg')
	logging.info('Файл ' + body.decode() + '.jpg записан.')

	ts = int(dateObs.timestamp())
	channel = 0  # мультикамеры

	if 'EXPTIME' in hdu.header:
		cursor.execute("""INSERT INTO sensor(date, channel, type, val)
			VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
			""" % {"time": ts, "channel": channel, "type": 'ccd-exposure', "val": hdu.header['EXPTIME']})

	if 'AVG' in hdu.header:
		cursor.execute("""INSERT INTO sensor(date, channel, type, val)
			VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
			""" % {"time": ts, "channel": channel, "type": 'ccd-average', "val": hdu.header['AVG']})

	if 'GAIN' in hdu.header:
		cursor.execute("""INSERT INTO sensor(date, channel, type, val)
			VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
			""" % {"time": ts, "channel": channel, "type": 'ccd-gain', "val": hdu.header['GAIN']})

	if 'XBINNING' in hdu.header:
		cursor.execute("""INSERT INTO sensor(date, channel, type, val)
			VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
			""" % {"time": ts, "channel": channel, "type": 'ccd-bin', "val": hdu.header['XBINNING']})

	if 'AI-CLEAR' in hdu.header:
		cursor.execute("""INSERT INTO sensor(date, channel, type, val)
			VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
			""" % {"time": ts, "channel": channel, "type": 'ai-clear', "val": hdu.header['AI-CLEAR']})

	if 'AI-CLOUD' in hdu.header:
		cursor.execute("""INSERT INTO sensor(date, channel, type, val)
			VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
			""" % {"time": ts, "channel": channel, "type": 'ai-cloud', "val": hdu.header['AI-CLOUD']})

	if stars is not None:
		cursor.execute("""INSERT INTO sensor(date, channel, type, val)
			VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
			""" % {"time": ts, "channel": channel, "type": 'stars-count', "val": len(stars)})

	db.commit()

	if os.path.islink('/snap/current.jpg'):
		os.remove('/snap/current.jpg')
	os.symlink(body.decode() +'.jpg', '/snap/current.jpg')

	if 'jpg' in web['publish'] and web['publish']['jpg'] != '':
		try:
			r = requests.post(
				web['publish']['jpg'],
				files={'file': open('/snap/'+ body.decode() +'.jpg', 'rb')},
				data={'name': web['web']['name'], 'pass': 'kjH3vxzm4G'}
			)
			logging.info('Файл ' + body.decode() + ' опубликован: ' + r.text)
		except:
			logging.error('ОШИБКА публикации файла ' + body.decode())

	logging.info('[+] Done')
	ch.basic_ack(delivery_tag=method.delivery_tag)


def reload(ch, method, properties, body):
	print(" [x] Received RELOAD")
	ch.basic_ack(delivery_tag=method.delivery_tag)
	sys.exit(0);


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_PROCESS'), on_message_callback=callback)
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_PROCESS'), on_message_callback=reload)

channel.start_consuming()
