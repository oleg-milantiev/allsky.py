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
import smbus2
import bme280
#import time
#from threading import Thread

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

channel = 0

# try BME280 i2c 
for f in os.listdir('/dev'):
	if f[0:4] == 'i2c-':
		port = int(f[4:])

		try:
			print('[.] Search BME280 on /dev/'+ f)
			address = 0x76
			bus = smbus2.SMBus(port)
			bme280.load_calibration_params(bus, address)
			data = bme280.sample(bus, address)
		except:
			print('[-] No BME280 on /dev/'+ f)


sys.exit()

bme280.load_calibration_params(bus, address)
data = bme280.sample(bus, address)

logging.info('[+] Start')




minute = datetime.now().strftime("%Y-%m-%d_%H-%M")

while True:

	# get sensors data
	

	# store sensors data
	db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
		 database=config.db['database'], charset='utf8')

	cursor = db.cursor()

	#cursor.execute('delete from sensor where date < '+ str(time.time() - 86400 * int(web['archive']['sensors'])))

	cursor.close()
	db.close()

	while True:
		now = datetime.now().strftime("%Y-%m-%d_%H-%M")
		if now != minute:
			break

		time.sleep(1)

	minute = now
