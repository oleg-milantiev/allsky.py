#!/usr/bin/python3

import os

#os.system('/common/udev.py')

import pika
import time
import json

import zwoasi as asi
from astropy.io import fits
from datetime import datetime

asi.init('/camera/'+ os.getenv('ARCH') +'/libASICamera2.so')

num_cameras = asi.get_num_cameras()
if num_cameras == 0:
    print('No cameras found')
    sys.exit(0)

cameras_found = asi.list_cameras()  # Models names of the connected cameras

if num_cameras == 1:
    print('Found one camera: %s' % cameras_found[0])
else:
    print('Found %d cameras' % num_cameras)
    for n in range(num_cameras):
        print('    %d: %s' % (n, cameras_found[n]))
    print('Using #%d: %s' % (camera_id, cameras_found[0]))

camera = asi.Camera(0)
camera_info = camera.get_camera_property()
controls = camera.get_controls()
camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, controls['BandWidth']['MinValue'])
camera.disable_dark_subtract()
camera.stop_video_capture()
camera.stop_exposure()

camera.set_roi(0, 0, camera_info["MaxWidth"], camera_info["MaxHeight"], 1, asi.ASI_IMG_RAW16)

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

def callback(ch, method, props, body):
    global camera, gain, exposure, cameras_found

    payload = json.loads(body.decode())
    print(" [x] Received %r" % body.decode())

    if payload['gain'] != gain:
        gain = payload['gain']
        camera.set_control_value(asi.ASI_GAIN, gain)

    if payload['exposure'] != exposure:
        exposure = payload['exposure']
        camera.set_control_value(asi.ASI_EXPOSURE, round(exposure * 1000))

    hdr = fits.Header()
    hdr['TELESCOP'] = 'AllSky'
    hdr['INSTRUME'] = cameras_found[0] #.decode("utf-8")
    hdr['GAIN'] = gain
    hdr['EXPTIME'] = exposure
    hdr['DATE-OBS'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    hdu = fits.PrimaryHDU(camera.capture(), header=hdr)
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
