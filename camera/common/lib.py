#!/usr/bin/python3

'''
Common functions library
Exists in all containers root as readonly /lib.py
'''

import config
from functools import cache
import ephem

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
	observatory.lat, observatory.lon = web['observatory']['lat'], web['observatory']['lon']

	return observatory

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