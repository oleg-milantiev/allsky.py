import cv2

ccd = {
	'name':		'ZWO CCD ASI178MC',
	'binning':	2,
	'avgMin':	100,
	'avgMax':	150,
	'expMin':	0.0001,
	'expMax':	45.,
	'cfa':		cv2.COLOR_BayerBG2RGB
}

archive = {
	'days':		7, # Хранить архив жпегов 7 дней
}

path = {
	'web':		'/var/www/html/',
	'ffmpeg':	'/usr/bin/ffmpeg'
}

import logging

log = {
	'path':		'/var/log/allsky.log',
	'level':	logging.DEBUG
}


### дальше не править

if (path['web'][-1] != '/'):
	path['web'] += '/'

path['snap'] = path['web'] +'snap/'
path['video'] = path['web'] +'video/'
