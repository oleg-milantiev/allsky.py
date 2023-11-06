#!/usr/bin/env python3

# https://learn.adafruit.com/adafruit-bme280-humidity-barometric-pressure-temperature-sensor-breakout/python-circuitpython-test

import board
import busio
import digitalio
import bme280

import time

import config
import mysql.connector

db = mysql.connector.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'], database=config.db['database'], charset='utf8')
cursor = db.cursor()

channel = 1

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.D22)
data = adafruit_bme280.Adafruit_BME280_SPI(spi, cs)

#print("\nTemperature: %0.1f C" % bme280.temperature)
#print("Humidity: %0.1f %%" % bme280.humidity)
#print("Pressure: %0.1f hPa" % bme280.pressure)

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

db.commit()

cursor.close()
db.close()
