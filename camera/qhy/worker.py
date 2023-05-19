#!/usr/bin/python3
import pika
import time
import os
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

def callback(ch, method, properties, body):
    global qc

    payload = json.loads(body.decode())
    print(" [x] Received %r" % body.decode())
    ch.basic_ack(delivery_tag=method.delivery_tag)

    qc.SetGain(payload['gain'])
    qc.SetExposure(payload['exposure'])

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

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE'), on_message_callback=callback)

channel.start_consuming()
