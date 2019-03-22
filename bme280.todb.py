#!/usr/bin/env python3

# basic script to test BME280 functionality

import smbus2
import bme280
import time

import mysql.connector
db = mysql.connector.connect(host="localhost", user="root", passwd="master", database="allsky", charset='utf8')
cursor = db.cursor()


port = 1
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
	"""%{"time":ts, "channel":0, "type": 'temperature', "val":data.temperature })

cursor.execute("""INSERT INTO sensor(date, channel, type, val)
	VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
	"""%{"time":ts, "channel":0, "type": 'humidity', "val":data.humidity })

cursor.execute("""INSERT INTO sensor(date, channel, type, val)
	VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
	"""%{"time":ts, "channel":0, "type": 'pressure', "val":data.pressure * 0.75 })

db.commit()

cursor.close()
db.close()
