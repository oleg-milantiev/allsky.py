db = {
	'host':		'db',
	'user':		'root',
	'passwd':	'master',
	'database':	'allsky',
}

path = {
	'web':		'/opt/allsky.py/web/',
	'ffmpeg':	'/usr/bin/ffmpeg',
}

import logging

log = {
#	'path':		'/var/log/allsky.log',	# путь до лога. И уровень болтливости (debug = максимальный)
	'path':		'/dev/stdout',
	'level':	logging.DEBUG,			# менее подробные: logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL
}


### дальше не править

if (path['web'][-1] != '/'):
	path['web'] += '/'

path['jpg'] = path['web'] +'snap/'
path['keogram'] = path['web'] +'keogram/'
path['video'] = path['web'] +'video/'
path['video-demand'] = path['web'] +'video-demand/'
path['fit'] = path['web'] + 'fits/'
