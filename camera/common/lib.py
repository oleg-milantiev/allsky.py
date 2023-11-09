#!/usr/bin/python3

'''
Common functions library
Exists in all containers root as readonly /lib.py
'''

import config
from functools import cache
import ephem

@cache
def getArch():
	import os

	return os.popen('uname -m').read().strip()

@cache
def getWebConfig():
	import json
	import MySQLdb

	db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
		 database=config.db['database'], charset='utf8')

	cursor = db.cursor()

	web = {}
	cursor.execute('select id, val from config')
	for row in cursor.fetchall():
		web[row[0]] = json.loads(row[1])

	cursor.close()
	db.close()

	return web

@cache
def isConfigExistsGPS():
	web = getWebConfig()

	return bool('observatory' in web and 'lat' in web['observatory'] and 'lon' in web['observatory'] and 'timezone' in web['observatory'] and web['observatory']['lat'] != '' and web['observatory']['lon'] != '' and web['observatory']['timezone'] != '')

@cache
def getObservatory():
	web = getWebConfig()

	if not isConfigExistsGPS():
		return None

	observatory = ephem.Observer()
	observatory.lat, observatory.lon = str(web['observatory']['lat']), str(web['observatory']['lon'])

	return observatory

# d must be in UTC!
# Return today sunrise datetime
# ex.: d=day_3:00 => day_6:30, d=day_15:00 => day_6:30 (not next sunrise, but today)
@cache
def getTodaySunrise(d):
	import math

	observatory = getObservatory()

	if not observatory:
		return None

	observatory.date = d.strftime('%Y-%m-%d %H:%M') 

	next = observatory.next_rising(ephem.Sun())

	if next.datetime().strftime('%d') == d.strftime('%d'):
		# now night. Next rise is same day
		return next.datetime()
	else:
		# now after sunrise
		return observatory.previous_rising(ephem.Sun()).datetime()

# d must be in UTC!
# Return None|string dayPart by given datetime
# ['day'|'morning'|'evening'|'night'|'night/moon']
@cache
def getDayPart(d):
	observatory = getObservatory()

	if not observatory:
		return None

	observatory.date = d.strftime('%Y-%m-%d %H:%M') 

	s = ephem.Sun()
	s.compute(observatory)
	twilight = -12 * ephem.degree
	if s.alt > 0:
		dayPart = 'day'
	elif s.alt > twilight:
		dayPart = 'morning' if d.hour < 12 else 'evening'
	else:
		dayPart = 'night'
		m = ephem.Moon()
		m.compute(observatory)

		if m.alt > 5 * ephem.degree:
			dayPart += '/moon' 

	return dayPart