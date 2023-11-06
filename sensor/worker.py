#!/usr/bin/python3

#from astropy.io import fits
from datetime import datetime#, timedelta
#import json
import logging
import MySQLdb
import os
#import pika
#import re
import signal
import sys

# I2C BME280
import smbus2
import bme280
import time
#from threading import Thread

# SPI BME280
import board
import busio
import digitalio
import adafruit_bme280


sys.path.insert(0, '/camera')
import config
import lib

def terminate(signal,frame):
	print("Start Terminating: %s" % datetime.now())

	sys.exit(0)

signal.signal(signal.SIGTERM, terminate)

#web = lib.getWebConfig()

logging.basicConfig(filename=config.log['path'], level=config.log['level'])

logging.info('[+] Discovering sensors')

channels = []

# try BME280 i2c 
logging.info('[.] Searh BME280(i2c)')

for f in os.listdir('/dev'):
	if f[0:4] == 'i2c-':
		port = int(f[4:])

		try:
			logging.debug('[.] Search BME280 on /dev/'+ f)
			address = 0x76
			bus = smbus2.SMBus(port)
			bme280.load_calibration_params(bus, address)
			data = bme280.sample(bus, address)

			logging.info('[+] Found BME280(I2C) on /dev/'+ f)
			channels.append({'sensor': 'bme280', 'bus': 'i2c', 'port': port})
		except:
			logging.debug('[-] No BME280 on /dev/'+ f)

try:
	spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
	cs = digitalio.DigitalInOut(board.D22)
	data = adafruit_bme280.Adafruit_BME280_SPI(spi, cs)

	logging.info('[+] Found BME280(SPI)')
	channels.append({'sensor': 'bme280', 'bus': 'spi'})
except:
	logging.debug('[-] No BME280 on SPI')

#print(channels)

logging.info('[+] Start to serve')

minute = datetime.now().strftime("%Y-%m-%d_%H-%M")

while True:

	if len(channels) > 0:
		# get sensors data
		for channel in range(len(channels)):
			data = None

			if channels[channel]['sensor'] == 'bme280':
				if channels[channel]['bus'] == 'i2c':
					address = 0x76
					bus = smbus2.SMBus(channels[channel]['port'])
					bme280.load_calibration_params(bus, address)
					data = bme280.sample(bus, address)

				elif channels[channel]['bus'] == 'spi':
					spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
					cs = digitalio.DigitalInOut(board.D22)
					data = adafruit_bme280.Adafruit_BME280_SPI(spi, cs)

			if data is not None:
				print(data)

			# store sensors data
			db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
				 database=config.db['database'], charset='utf8')

			cursor = db.cursor()

			ts = int(time.time())

			cursor.execute("""INSERT INTO sensor(date, channel, type, val)
				VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
				"""%{"time":ts, "channel":channel, "type": 'temperature', "val":data.temperature })

			cursor.execute("""INSERT INTO sensor(date, channel, type, val)
				VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
				"""%{"time":ts, "channel":channel, "type": 'humidity', "val":data.humidity })

			cursor.execute("""INSERT INTO sensor(date, channel, type, val)
				VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
				"""%{"time":ts, "channel":channel, "type": 'pressure', "val":data.pressure * 0.75 })


			cursor.execute("""REPLACE INTO sensor_last(date, channel, type, val)
				VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
				"""%{"time":ts, "channel":channel, "type": 'temperature', "val":data.temperature })

			cursor.execute("""REPLACE INTO sensor_last(date, channel, type, val)
				VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
				"""%{"time":ts, "channel":channel, "type": 'humidity', "val":data.humidity })

			cursor.execute("""REPLACE INTO sensor_last(date, channel, type, val)
				VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
				"""%{"time":ts, "channel":channel, "type": 'pressure', "val":data.pressure * 0.75 })

			cursor.close()
			db.close()

	logging.debug('[.] Waiting for next minute')
	while True:
		now = datetime.now().strftime("%Y-%m-%d_%H-%M")
		if now != minute:
			break

		time.sleep(1)

	minute = now
