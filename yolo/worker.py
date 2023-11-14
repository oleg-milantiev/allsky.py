#!/usr/bin/python3

from astropy.io import fits
from ultralytics import YOLO
from os.path import isfile
from datetime import datetime

import ephem
import logging
import os
import re
import sys
import pika

import signal

def terminate(signal,frame):
	print("Start Terminating: %s" % datetime.now())
	sys.exit(0)

signal.signal(signal.SIGTERM, terminate)


logging.basicConfig(filename='/dev/stdout', level=logging.DEBUG)

logging.info('[+] Start')

observatory = ephem.Observer()
# todo move GPS to web (with map)
observatory.lat, observatory.lon = '44.791395', '38.583824'
s = ephem.Sun()

version = '5' # x, png, aug(rotate=3, bright=50)
model = {}

for time in ['day', 'morning', 'evening', 'night', 'night/moon']:
	model[time] = YOLO(time +'/runs/classify/train'+ version +'/weights/best.pt')

logging.info('[+] Models are loaded. Ready to work')

connection = pika.BlockingConnection(
	pika.ConnectionParameters(
		os.getenv('RABBITMQ_HOST'),
		os.getenv('RABBITMQ_PORT'),
		'/',
		pika.PlainCredentials(
			os.getenv('RABBITMQ_DEFAULT_USER'),
			os.getenv('RABBITMQ_DEFAULT_PASS'))))

channel = connection.channel()

channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_YOLO'), durable=True)
channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_YOLO'), durable=True)
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

	# fits header datetime prefered
	d = datetime.strptime(hdu.header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S')
	observatory.date = d.strftime('%Y-%m-%d %H:%M')
	s.compute(observatory)

	if s.alt > 0:
		dayPart = 'day'
	elif s.alt > -12 * ephem.degree:
		dayPart = 'morning' if d.hour < 12 else 'evening'
	else:
		dayPart = 'night'
		m = ephem.Moon()
		m.compute(observatory)

		if m.alt > 5 * ephem.degree:
			dayPart += '/moon'

	print(d.strftime('%Y-%m-%d %H:%M') +': '+ dayPart)
	os.system('convert /fits/'+ body.decode() +'.fit -interpolative-resize 224x224! -normalize -colorspace sRGB -type truecolor PNG24:/tmp/fit.png')
	# todo sync=false to disable google.anal
	results = model[dayPart]('/tmp/fit.png')

	print(results[0].names[0])
	print('%0.2f' % (float(results[0].probs.data[0]) * 100))
	print(results[0].names[1])
	print('%0.2f' % (float(results[0].probs.data[1]) * 100))

	hdu.header.set('AI-DPART', dayPart, 'Day part')
	hdu.header.set('AI-CLEAR', float(results[0].probs.data[0]), 'Clear probability')
	hdu.header.set('AI-CLOUD', float(results[0].probs.data[1]), 'Cloud probability')

	fit.close()

	# Передать дальше в process.py
	ch.basic_publish(
		exchange='',
		routing_key=os.getenv('RABBITMQ_QUEUE_PROCESS'),
		body=body.decode(),
		properties=pika.BasicProperties(
			delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
			))

	logging.info('[+] Done')
	ch.basic_ack(delivery_tag=method.delivery_tag)


def reload(ch, method, properties, body):
	print(" [x] Received RELOAD")
	ch.basic_ack(delivery_tag=method.delivery_tag)
	sys.exit(0);


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_YOLO'), on_message_callback=callback)
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_YOLO'), on_message_callback=reload)

channel.start_consuming()
