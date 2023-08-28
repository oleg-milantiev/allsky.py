#!/usr/bin/python3

# пока на внешнем INDI
# надо, как минимум, запихнуть его в тот же ящик

import pika
import PyIndi
import json
import time
import sys
import io
import os
from astropy.io import fits
from datetime import datetime

cameraName = 'SX CCD SuperStar'

class IndiClient(PyIndi.BaseClient):
	device = None

	def __init__(self):
		super(IndiClient, self).__init__()

	def newDevice(self, d):
		print('newDevice: ' + d.getDeviceName())
		self.device = d
		pass

	def newProperty(self, p):
		pass

	def removeProperty(self, p):
		pass

	def newBLOB(self, bp):
		print(' [x] Getting a frame...')

		fit = fits.open(io.BytesIO(bp.getblobdata()))
		hdu = fit[0]
		hdu.header['TELESCOP'] = 'AllSky'
		hdu.header['INSTRUME'] = cameraName
		hdu.header['GAIN'] = gain
		hdu.header['EXPTIME'] = exposure
		hdu.header['DATE-OBS'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
		hdu.writeto('/fits/current.fit', overwrite=True)

		print(" [x] Done")

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
indi = IndiClient()
indi.setServer('host.docker.internal', 7624)

if not indi.connectServer():
	print('Не найден INDI-сервер камеры')
	sys.exit(1)

print('INDI нашёл')

retries = 10
ccd = indi.getDevice(cameraName)
while not ccd:
	retries -= 1
	if retries == 0:
		print('Не получаю CCD')
		sys.exit(1)
	time.sleep(0.5)
	ccd = indi.getDevice(cameraName)

print('CCD увидел в списке')

retries = 10
ccd_connect = ccd.getSwitch("CONNECTION")
while not ccd_connect:
	retries -= 1
	if retries == 0:
		print('Не получаю CONNECTION')
		sys.exit(1)
	time.sleep(0.5)
	ccd_connect = ccd.getSwitch("CONNECTION")

print('CCD нашёл')

if not ccd.isConnected():
	ccd_connect[0].s = PyIndi.ISS_ON  # the "CONNECT" switch
	ccd_connect[1].s = PyIndi.ISS_OFF  # the "DISCONNECT" switch
	indi.sendNewSwitch(ccd_connect)

print('CCD подключил')

retries = 10
ccd_exposure = ccd.getNumber("CCD_EXPOSURE")
while not ccd_exposure:
	retries -= 1
	if retries == 0:
		print('Похоже, камера зависла')
		# lsusb -> bus 001, dev 005
		# fxload -t fx2 -D /dv/bus/usb/001/005 -I /lib/firmware/qhy/QHY5LOADER.HEX -v
		# os.system('reboot')
		sys.exit(1)
	time.sleep(0.5)
	ccd_exposure = ccd.getNumber("CCD_EXPOSURE")

print('EXPOSURE нашёл')

hasBinning = True
retries = 10
ccd_binning = ccd.getNumber("CCD_BINNING")
while not ccd_binning:
	retries -= 1
	if retries == 0:
		hasBinning = False
		print('Не могу получить CCD_BINNING')
		break
	time.sleep(0.5)
	ccd_binning = ccd.getNumber("CCD_BINNING")

indi.setBLOBMode(PyIndi.B_ALSO, cameraName, 'CCD1')
print('setBLOB отправил')

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
	global bin, gain, exposure, cameraName, indi, ccd_binning

	payload = json.loads(body.decode())
	print(" [x] Received %r" % body.decode())

	if payload['gain'] != gain:
		gain = payload['gain']
		# ignore gain

	if hasBinning and 'bin' in payload and payload['bin'] != bin:
		bin = payload['bin']

		ccd_binning[0].value = bin
		ccd_binning[1].value = bin
		indi.sendNewNumber(ccd_binning)
		print('BINNING {} отправил'.format(bin))

	if payload['exposure'] != exposure:
		exposure = payload['exposure']

	indi.props = props
	indi.ch = ch

	ccd_exposure[0].value = exposure
	indi.sendNewNumber(ccd_exposure)
	print(" [+] Start exposure")

	# wait file
	# @todo thread.lock and timeout
	time.sleep(exposure + 2)

	ch.basic_publish(exchange='',
				 routing_key=props.reply_to,
				 properties=pika.BasicProperties(correlation_id = props.correlation_id),
				 body='Ok')

	ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_CAMERA'), on_message_callback=callback)

channel.start_consuming()
