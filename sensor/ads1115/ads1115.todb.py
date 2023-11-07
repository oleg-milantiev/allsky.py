#!/usr/bin/env python3

#- pip3 install Adafruit_ADS1x15 Adafruit_Python_PureIO.git Adafruit_Python_GPIO.git. Но иногда может не прокатить. Поэтому я добавил эти три библиотеки в /opt/allsky.py/ads1115


import time
import Adafruit_ADS1x15
import mysql.connector

import sys
sys.path.append("/opt/allsky.py")
import config

adc = Adafruit_ADS1x15.ADS1115()

db = mysql.connector.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'], database=config.db['database'], charset='utf8')
cursor = db.cursor()

GAIN = 1
#  -   1 = +/-4.096V
#  -   2 = +/-2.048V
#  -   4 = +/-1.024V
#  -   8 = +/-0.512V
#  -  16 = +/-0.256V

minute = ""
avg = [0] * 4

for repeat in range(10):
	for i in range(4):
		avg[i] += adc.read_adc(i, gain=GAIN)

#print(avg[0] / 10)
#print(avg[1] / 10)

ts = int(time.time()) + 3600 * 3

cursor.execute("""INSERT INTO sensor(date, channel, type, val)
	VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
	"""%{"time":ts, "channel":0, "type": 'voltage', "val":avg[0] / 10 })

cursor.execute("""INSERT INTO sensor(date, channel, type, val)
	VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
	"""%{"time":ts, "channel":1, "type": 'voltage', "val":avg[1] / 10 })


cursor.execute("""REPLACE INTO sensor_last(date, channel, type, val)
	VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
	"""%{"time":ts, "channel":0, "type": 'voltage', "val":avg[0] / 10 })

cursor.execute("""REPLACE INTO sensor_last(date, channel, type, val)
	VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
	"""%{"time":ts, "channel":1, "type": 'voltage', "val":avg[1] / 10 })

db.commit()

cursor.close()
db.close()
