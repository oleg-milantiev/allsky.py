ccd = {
	'name':		'ZWO CCD ASI120MC',
	'binning':	1,
	'avgMin':	100,
	'avgMax':	150,
	'expMin':	0.0001,
	'expMax':	45.
}

archive = {
	'days':		7, # Хранить архив жпегов 7 дней
}

path = {
	'web':		'/var/www/html/'
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
