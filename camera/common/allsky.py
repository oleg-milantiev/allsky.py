#!/usr/bin/python3

from astropy.io import fits
import config
from datetime import datetime
import json
import logging
import MySQLdb
import numpy as np
import pika # rabbitmq client
import sys
import time
import os
import uuid

def reload(ch, method, properties, body):
	print(" [x] Received RELOAD")
	ch.basic_ack(delivery_tag=method.delivery_tag)
	sys.exit(0);

# Класс общения с docker.camera контейнером через rabbitmq в шаблоне RPC-Client
class CameraClient(object):

	def __init__(self):
		self.connection = pika.BlockingConnection(
			pika.ConnectionParameters(
				os.getenv('RABBITMQ_HOST'),
				os.getenv('RABBITMQ_PORT'),
				'/',
				pika.PlainCredentials(
					os.getenv('RABBITMQ_DEFAULT_USER'),
					os.getenv('RABBITMQ_DEFAULT_PASS'))))

		self.channel = self.connection.channel()

		self.channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_PROCESS'), durable=True)
		self.channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_ALLSKY'), durable=True)

		result = self.channel.queue_declare(queue='', exclusive=True)
		self.callback_queue = result.method.queue

		self.channel.basic_consume(
			queue=self.callback_queue,
			on_message_callback=self.on_response,
			auto_ack=True)

		self.response = None
		self.corr_id = None

		self.channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_ALLSKY'), on_message_callback=reload)

	def on_response(self, ch, method, props, body):
		if self.corr_id == props.correlation_id:
			self.response = body

	def call(self, gain, exposure):
		self.response = None
		self.corr_id = str(uuid.uuid4())
		self.channel.basic_publish(
			exchange='',
			routing_key=os.getenv('RABBITMQ_QUEUE_CAMERA'),
			properties=pika.BasicProperties(
				reply_to=self.callback_queue,
				correlation_id=self.corr_id,
			),
			body=json.dumps({'gain': gain, 'exposure': exposure}))
		self.connection.process_data_events(time_limit=exposure + 5)

		return str(self.response)


# Чтение конфига
db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
	 database=config.db['database'], charset='utf8')

cursor = db.cursor()

web = {}
cursor.execute('select id, val from config')
for row in cursor.fetchall():
	web[row[0]] = json.loads(row[1])

# Старт
logging.basicConfig(filename=config.log['path'], level=config.log['level'])

logging.info('[+] Start')

camera = CameraClient()

#set default ROI camera
#if 'processing' in web and 'crop' in web['processing']:
#	crop = web['processing']['crop']
#	logging.debug('Вырезаю CROP: {}-{}, {}-{}'.format(crop['left'], crop['right'], crop['top'], crop['bottom']))
#	hdu.data = hdu.data[crop['left']:(hdu.header['NAXIS1'] - crop['right']), crop['top']:(hdu.header['NAXIS2'] - crop['bottom'])]

minute = datetime.now().strftime("%Y-%m-%d_%H-%M")
gain = 10
exposure = 0.1

while True:
	logging.debug('Получаю новый кадр...')

	# rabbit - получение кадра с начальным exposure / gain / bin
	if camera.call(gain=gain, exposure=exposure) is None:
		logging.error('Не смог отправить запрос к rabbitmq')
		sys.exit(-1)

	try:
		fit = fits.open('/fits/current.fit')
		hdu = fit[0]
	except:
		logging.error('Не получил fit от контейнера камеры')
		sys.exit(-1)

	# Подсчёт среднего по центру кадра
	center = 50

	if 'ccd' in web and 'center' in web['ccd']:
		center = web['ccd']['center']

	if 0 < center <= 100:
		logging.debug('Среднее по центральным {}%'.format(center))
		avg = np.mean(hdu.data[
			int(hdu.data.shape[0] * (50 - center / 2) / 100):int(hdu.data.shape[0] * (50 + center / 2) / 100),
			int(hdu.data.shape[1] * (50 - center / 2) / 100):int(hdu.data.shape[1] * (50 + center / 2) / 100)])

	logging.info('Получил кадр выдержкой {} сек. со средним {}'.format(exposure, avg))

	if (web['ccd']['avgMin'] < avg < web['ccd']['avgMax']) or (
			(exposure == web['ccd']['expMin']) and (avg > web['ccd']['avgMax'])) or (
			(exposure == web['ccd']['expMax']) and (avg < web['ccd']['avgMin'])):
# учёт gainMin, gainMax, maxAttempt
		logging.debug('Жду следующей минуты')
		while True:
			now = datetime.now().strftime("%Y-%m-%d_%H-%M")
			if now != minute:
				break
			time.sleep(1)

		minute = now

		os.system('mv /fits/current.fit /fits/'+ minute +'.fit')
		logging.info('Файл {}.fit сохранён'.format(minute))

		camera.channel.basic_publish(
			exchange='',
			routing_key=os.getenv('RABBITMQ_QUEUE_PROCESS'),
			body=minute,
			properties=pika.BasicProperties(
				delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
				))


	else:
		# подбор выдержки
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





