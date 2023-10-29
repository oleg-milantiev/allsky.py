#!/usr/bin/env python3

import smbus2
import bme280
import time

import config
import mysql.connector

db = mysql.connector.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'], database=config.db['database'], charset='utf8')
cursor = db.cursor()

channel = 0

port = 0
address = 0x76
bus = smbus2.SMBus(port)

bme280.load_calibration_params(bus, address)

data = bme280.sample(bus, address)

#print("temp = {0}".format(data.temperature))
#print("pressure = {0}".format(data.pressure))
#print("humidity = {0}".format(data.humidity))

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
