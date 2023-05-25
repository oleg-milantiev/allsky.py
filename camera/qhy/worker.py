#!/usr/bin/python3

import os

os.system('/common/udev.py')

import pika
import time
import json

import qhyccd
from astropy.io import fits
from datetime import datetime

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

channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE'), durable=True)
print(' [*] Waiting for messages. To exit press CTRL+C')

exposure = 100
gain = None

def callback(ch, method, props, body):
    global qc, gain, exposure

    payload = json.loads(body.decode())
    print(" [x] Received %r" % body.decode())

    if payload['gain'] != gain:
        qc.SetGain(payload['gain'])
        gain = payload['gain']

    if payload['exposure'] != exposure:
        qc.SetExposure(round(payload['exposure'] * 1000))
        exposure = payload['exposure']

    hdr = fits.Header()
    hdr['TELESCOP'] = 'AllSky'
    hdr['INSTRUME'] = qc.id.value.decode("utf-8")
    hdr['GAIN'] = payload['gain']
    hdr['EXPTIME'] = payload['exposure']
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
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE'), on_message_callback=callback)

channel.start_consuming()
