#!/usr/bin/python3

import pika
import PyIndi
import json
import time
import sys
import io
import os
import signal
from astropy.io import fits
from datetime import datetime

os.system('python3 /common/udev.py')

def terminate(signal,frame):
	print("Start Terminating: %s" % datetime.now())
	sys.exit(0)

signal.signal(signal.SIGTERM, terminate)

#cameraName = 'SX CCD SuperStar'
cameraName = None

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
		# в свежем INDI под докером сюда не приходит. Чудеса, блин
		print(' [x] Getting a frame...')

		fit = fits.open(io.BytesIO(bp.getblobdata()))
		hdu = fit[0]
		hdu.header['TELESCOP'] = 'AllSky'
#		hdu.header['INSTRUME'] = cameraName
#		if not 'GAIN' in hdu.header:
#			hdu.header['GAIN'] = gain
#		if hasBinning:
#			hdu.header['XBINNING'] = bin
#			hdu.header['YBINNING'] = bin
#		hdu.header['EXPTIME'] = exposure
		hdu.header['DATE-OBS'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
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
indi.setServer('indi', 7624)

if not indi.connectServer():
	print('Cant connect to INDI server')
	sys.exit(1)

print('Connect to INDI server')

time.sleep(1)

# Find and print all devices. Use first as cameraName
for dev in indi.getDevices():
	print('Found device: '+ dev.getDeviceName())

	if cameraName is None:
		cameraName = dev.getDeviceName()
		print('Using first device as camera: '+ cameraName)

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

if hasBinning:
	print('BINNING нашёл')

hasGain = True
retries = 10
ccd_gain = ccd.getNumber("CCD_GAIN")
while not ccd_gain:
	retries -= 1
	if retries == 0:
		hasGain = False
		print('Не могу получить CCD_GAIN')
		break
	time.sleep(0.5)
	ccd_gain = ccd.getNumber("CCD_GAIN")

if hasGain:
	print('GAIN нашёл')

indi.setBLOBMode(PyIndi.B_ALSO, cameraName, 'CCD1')
print('setBLOB отправил')

ccd_ccd1 = ccd.getBLOB("CCD1")
while not(ccd_ccd1):
	time.sleep(0.5)
	ccd_ccd1 = ccd.getBLOB("CCD1")
print('ccd1 получил')

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
	global bin, gain, exposure, cameraName, indi, ccd_binning, ccd_ccd1

	payload = json.loads(body.decode())
	print(" [x] Received %r" % body.decode())

	if hasGain and 'gain' in payload and payload['gain'] != gain:
		gain = payload['gain']
		ccd_gain[0].value = bin
		indi.sendNewNumber(ccd_gain)
		print('GAIN {} отправил'.format(gain))

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

	fit = None
	for blob in ccd_ccd1:
		print(" [+] Have BLOB: ", blob.name," size: ", blob.size," format: ", blob.format)
		if blob.size > 0:
			fit = fits.open(io.BytesIO(blob.getblobdata()))
			hdu = fit[0]
#			print(hdu.header)
#			sys.exit()
			hdu.header['TELESCOP'] = 'AllSky'
#			hdu.header['INSTRUME'] = cameraName
#			if not 'GAIN' in hdu.header:
#				hdu.header['GAIN'] = gain
#			if hasBinning:
#				hdu.header['XBINNING'] = bin
#				hdu.header['YBINNING'] = bin
#			hdu.header['EXPTIME'] = exposure
			hdu.header['DATE-OBS'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
			hdu.writeto('/fits/current.fit', overwrite=True)

	if fit is None:
		print(' [!] Cant get image')

	print(" [+] End exposure")

	ch.basic_publish(exchange='',
				 routing_key=props.reply_to,
				 properties=pika.BasicProperties(correlation_id = props.correlation_id),
				 body='Ok')

	ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_CAMERA'), on_message_callback=callback)

channel.start_consuming()