#!/usr/bin/python3

import pika
import PyIndi
import json
import time
import sys
import io
import os
import signal
import logging
from astropy.io import fits
from datetime import datetime

# Configure logging
def setup_logging():
	"""Configure logging with proper format and level for Docker environment"""
	log_format = '%(asctime)s - %(levelname)s - %(message)s'
	logging.basicConfig(
		level=logging.INFO,
		format=log_format,
		handlers=[
			logging.StreamHandler(sys.stdout)
		]
	)
	return logging.getLogger('indi_worker')

logger = setup_logging()

os.system('python3 /common/udev.py')

def cleanup_resources():
	"""Cleanup camera and connection resources properly"""
	global ccd, connection, indi
	
	try:
		if 'ccd' in globals() and ccd is not None:
			logger.info("Disconnecting camera...")
			if ccd.isConnected():
				# Get CONNECTION switch to disconnect camera
				ccd_connect = ccd.getSwitch("CONNECTION")
				if ccd_connect:
					ccd_connect[0].s = PyIndi.ISS_OFF  # CONNECT
					ccd_connect[1].s = PyIndi.ISS_ON   # DISCONNECT
					indi.sendNewSwitch(ccd_connect)
					logger.info("Camera disconnected")
	except Exception as e:
		logger.error("Error disconnecting camera: %s", str(e))

	try:
		if 'connection' in globals() and connection is not None:
			logger.info("Closing RabbitMQ connection...")
			connection.close()
			logger.info("RabbitMQ connection closed")
	except Exception as e:
		logger.error("Error closing RabbitMQ connection: %s", str(e))

	try:
		if 'indi' in globals() and indi is not None:
			logger.info("Disconnecting from INDI server...")
			indi.disconnectServer()
			logger.info("INDI server disconnected")
	except Exception as e:
		logger.error("Error disconnecting from INDI server: %s", str(e))

def terminate(signal, frame):
	"""Handle termination signals and cleanup resources"""
	logger.info("Received termination signal")
	cleanup_resources()
	logger.info("Cleanup completed, exiting")
	sys.exit(0)

# Register signal handlers for proper cleanup
signal.signal(signal.SIGTERM, terminate)
signal.signal(signal.SIGINT, terminate)

# Camera selection configuration
# Priority: 1. Environment variable 2. Known camera models 3. First available device
KNOWN_CAMERA_MODELS = [
	'SX CCD SuperStar',
	'ZWO CCD ASI120MM',
	'QHY CCD QHY5',
	'ASI Camera'
]

def find_camera_device():
	"""
	Find and select the appropriate camera device based on configuration priority:
	1. Environment variable INDI_CAMERA_NAME if set
	2. First matching known camera model from KNOWN_CAMERA_MODELS
	3. First available device as fallback
	
	Returns:
		tuple: (camera_name, camera_type) or (None, None) if no camera found
	"""
	# Check environment variable first
	env_camera = os.getenv('INDI_CAMERA_NAME')
	if env_camera:
		return env_camera, "Environment configured camera"
	
	# Get list of all devices
	devices = indi.getDevices()
	if not devices:
		return None, "No INDI devices found"
		
	# Try to find a known camera model
	for device in devices:
		device_name = device.getDeviceName()
		if any(model.lower() in device_name.lower() for model in KNOWN_CAMERA_MODELS):
			return device_name, "Known camera model"
			
	# Fallback to first device
	if devices:
		return devices[0].getDeviceName(), "First available device"
		
	return None, "No suitable camera found"

class IndiClient(PyIndi.BaseClient):
	device = None

	def __init__(self):
		super(IndiClient, self).__init__()

	def newDevice(self, d):
		logger.info('newDevice: ' + d.getDeviceName())
		self.device = d
		pass

	def newProperty(self, p):
		pass

	def removeProperty(self, p):
		pass

	def newBLOB(self, bp):
		# в свежем INDI под докером сюда не приходит. Чудеса, блин
		logger.info(' [x] Getting a frame...')

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

		logger.info(" [x] Done")

		pass

	def newSwitch(self, svp):
		pass

	def newNumber(self, nvp):
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
try:
	indi = IndiClient()
	indi.setServer('indi', 7624)

	if not indi.connectServer():
		logger.error('Cannot connect to INDI server')
		sys.exit(1)

	logger.info('Connected to INDI server')

	time.sleep(1)

	# Find and select camera
	cameraName, selection_method = find_camera_device()
	if not cameraName:
		logger.error(f'Error: {selection_method}')
		cleanup_resources()
		sys.exit(1)

	logger.info(f'Selected camera: {cameraName} (Selection method: {selection_method})')

	retries = 10
	ccd = indi.getDevice(cameraName)
	while not ccd:
		retries -= 1
		if retries == 0:
			logger.error('Cannot get CCD device')
			cleanup_resources()
			sys.exit(1)
		time.sleep(0.5)
		ccd = indi.getDevice(cameraName)

	logger.info('CCD device found')

	retries = 10
	ccd_connect = ccd.getSwitch("CONNECTION")
	while not ccd_connect:
		retries -= 1
		if retries == 0:
			logger.error('Cannot get CONNECTION switch')
			cleanup_resources()
			sys.exit(1)
		time.sleep(0.5)
		ccd_connect = ccd.getSwitch("CONNECTION")

	logger.info('CCD connection switch found')

	if not ccd.isConnected():
		ccd_connect[0].s = PyIndi.ISS_ON  # the "CONNECT" switch
		ccd_connect[1].s = PyIndi.ISS_OFF  # the "DISCONNECT" switch
		indi.sendNewSwitch(ccd_connect)

	logger.info('CCD connected')

	retries = 10
	ccd_exposure = ccd.getNumber("CCD_EXPOSURE")
	while not ccd_exposure:
		retries -= 1
		if retries == 0:
			logger.error('Cannot get CCD_EXPOSURE property')
			cleanup_resources()
			sys.exit(1)
		time.sleep(0.5)
		ccd_exposure = ccd.getNumber("CCD_EXPOSURE")

	logger.info('CCD_EXPOSURE property found')

	hasBinning = True
	retries = 10
	ccd_binning = ccd.getNumber("CCD_BINNING")
	while not ccd_binning:
		retries -= 1
		if retries == 0:
			hasBinning = False
			logger.error('Cannot get CCD_BINNING property')
			break
		time.sleep(0.5)
		ccd_binning = ccd.getNumber("CCD_BINNING")

	if hasBinning:
		logger.info('CCD_BINNING property found')

	hasGain = True
	retries = 10
	ccd_gain = ccd.getNumber("CCD_GAIN")
	while not ccd_gain:
		retries -= 1
		if retries == 0:
			hasGain = False
			logger.error('Cannot get CCD_GAIN property')
			break
		time.sleep(0.5)
		ccd_gain = ccd.getNumber("CCD_GAIN")

	if hasGain:
		logger.info('CCD_GAIN property found')

	indi.setBLOBMode(PyIndi.B_ALSO, cameraName, 'CCD1')
	logger.info('BLOB mode set')

	ccd_ccd1 = ccd.getBLOB("CCD1")
	while not(ccd_ccd1):
		time.sleep(0.5)
		ccd_ccd1 = ccd.getBLOB("CCD1")
	logger.info('CCD1 BLOB found')

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
	logger.info(' [*] Waiting for messages. To exit press CTRL+C')

	exposure = None
	gain = None
	bin = None

	def callback(ch, method, props, body):
		global bin, gain, exposure, cameraName, indi, ccd_binning, ccd_ccd1

		payload = json.loads(body.decode())
		logger.info("Received message: %s", body.decode())

		if hasGain and 'gain' in payload and payload['gain'] != gain:
			gain = payload['gain']
			ccd_gain[0].value = gain
			indi.sendNewNumber(ccd_gain)
			logger.info('Setting GAIN to %s', gain)

		if hasBinning and 'bin' in payload and payload['bin'] != bin:
			bin = payload['bin']
			ccd_binning[0].value = bin
			ccd_binning[1].value = bin
			indi.sendNewNumber(ccd_binning)
			logger.info('Setting BINNING to %s', bin)

		if payload['exposure'] != exposure:
			exposure = payload['exposure']
			logger.info('Setting exposure to %s seconds', exposure)

		indi.props = props
		indi.ch = ch

		ccd_exposure[0].value = exposure
		indi.sendNewNumber(ccd_exposure)
		logger.info("Starting exposure: %s seconds", exposure)

		# wait file
		# @todo thread.lock and timeout
		time.sleep(exposure + 2)

		fit = None
		for blob in ccd_ccd1:
			logger.debug("BLOB received - Name: %s, Size: %s, Format: %s", 
				blob.name, blob.size, blob.format)
			if blob.size > 0:
				fit = fits.open(io.BytesIO(blob.getblobdata()))
				hdu = fit[0]
				hdu.header['TELESCOP'] = 'AllSky'
				hdu.header['DATE-OBS'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
				hdu.writeto('/fits/current.fit', overwrite=True)
				logger.info("Image saved to /fits/current.fit")

		if fit is None:
			logger.error('Failed to capture image')
		else:
			logger.info("Exposure completed successfully")

		ch.basic_publish(exchange='',
						routing_key=props.reply_to,
						properties=pika.BasicProperties(correlation_id = props.correlation_id),
						body='Ok')

		ch.basic_ack(delivery_tag=method.delivery_tag)

	channel.basic_qos(prefetch_count=1)
	channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_CAMERA'), on_message_callback=callback)

	channel.start_consuming()

except Exception as e:
	logger.error("Initialization failed: %s", str(e))
	cleanup_resources()
	sys.exit(1)
