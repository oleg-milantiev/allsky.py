#!/usr/bin/python3

import os

os.system('python3 /common/udev.py')

import pika
import signal
import sys
import time
import json

from astropy.io import fits
from datetime import datetime

def terminate(signal,frame):
	print("Start Terminating: %s" % datetime.now())
	sys.exit(0)

signal.signal(signal.SIGTERM, terminate)

import qhyccd
qc = qhyccd.qhyccd()

print(' [*] Start')

connection = pika.BlockingConnection(
	pika.ConnectionParameters(
		os.getenv('RABBITMQ_HOST'),
		os.getenv('RABBITMQ_PORT'),
		'/',
		pika.PlainCredentials(
			os.getenv('RABBITMQ_DEFAULT_USER'),
			os.getenv('RABBITMQ_DEFAULT_PASS'))))

channel = connection.channel()

channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_CAMERA'), durable=True)
print(' [*] Waiting for messages. To exit press CTRL+C')

exposure = None
gain = None
bin = None

def callback(ch, method, props, body):
	global gain, exposure, bin, qc

	payload = json.loads(body.decode())
	print(" [x] Received %r" % body.decode())

	if payload['bin'] != bin:
		bin = payload['bin']

	if payload['gain'] != gain:
		gain = payload['gain']
		qc.SetGain(gain)

	if payload['exposure'] != exposure:
		exposure = payload['exposure']
		qc.SetExposure(round(exposure * 1000))

	hdr = fits.Header()
	hdr['TELESCOP'] = 'AllSky'
	hdr['INSTRUME'] = qc.id.value.decode("utf-8")
	hdr['GAIN'] = gain
	hdr['XBINNING'] = bin
	hdr['YBINNING'] = bin
	hdr['EXPTIME'] = exposure
	hdr['DATE-OBS'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
	hdu = fits.PrimaryHDU(qc.GetSingleFrame(), header=hdr)
	hdul = fits.HDUList([hdu])
	hdul.writeto('/fits/current.fit', overwrite=True)

	print(" [x] Done")

	ch.basic_publish(exchange='',
		routing_key=props.reply_to,
		properties=pika.BasicProperties(correlation_id = props.correlation_id),
		body='Ok')

	ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_CAMERA'), on_message_callback=callback)

channel.start_consuming()
