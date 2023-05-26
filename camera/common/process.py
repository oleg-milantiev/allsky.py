#!/usr/bin/python3

import config
import os
import pika
import time
import json
import MySQLdb
import logging
from PIL import Image, ImageDraw, ImageFont
from astropy.io import fits
from datetime import datetime

logging.basicConfig(filename=config.log['path'], level=config.log['level'])

logging.debug('[+] Start')

# Чтение конфига
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
print(' [*] Waiting for messages. To exit press CTRL+C')

def callback(ch, method, properties, body):
	print(" [x] Received %r" % body.decode())

	#todo check input via re.match

	try:
		fit = fits.open('/fits/'+ body.decode() +'.fit')
		hdu = fit[0]
	except:
		logging.info('Не получил fit от контейнера камеры')
		sys.exit(-1)

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

		img2gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
		ret, mask = cv2.threshold(img2gray, 245, 255, cv2.THRESH_BINARY)
		maskInv = cv2.bitwise_not(mask)

		imgOverexposed = cv2.bitwise_and(rgb, rgb, mask=mask)

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

		watermark = Image.open(config['path']['jpg'] +'/'+ web['processing']['logo']['file'])

		img.paste(watermark, (web['processing']['logo']['x'], web['processing']['logo']['y']))

	if 'annotation' in web['processing']:
		logging.debug('Добавляю аннотации')

		txt = Image.new('RGBA', img.size, (255, 255, 255, 0))
		d = ImageDraw.Draw(txt)

		dateObs = datetime.strptime(hdu.header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S')

		for annotation in web['processing']['annotation']:
			font = ImageFont.truetype('sans-serif.ttf', int(annotation['size']))

			match annotation['type']:
				case 'text': text = annotation['format']
				case 'datetime': text = dateObs.strftime(annotation['format'])
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

	logging.debug('[+] Done')
	ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_PROCESS'), on_message_callback=callback)

channel.start_consuming()
