#!/usr/bin/python3

import config
import mysql.connector
import time

db = mysql.connector.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'], database=config.db['database'], charset='utf8')
cursor = db.cursor(dictionary=True)

for relay in config.relay:
	f = open('/sys/class/gpio/export', 'wt')
	f.write(relay['gpio'])
	f.close()

time.sleep(0.1)

for relay in config.relay:
	f = open('/sys/class/gpio/gpio{}/direction'.format(relay['gpio']), 'wt')
	f.write('out')
	f.close()

time.sleep(0.1)

for relay in config.relay:
	cursor.execute('SELECT state FROM relay where id = "{}"'.format(relay['name']))
	state = cursor.fetchone()

	f = open('/sys/class/gpio/gpio{}/value'.format(relay['gpio']), 'wt')
	f.write('{}'.format(state['state']) if state else '0')
	f.close()
