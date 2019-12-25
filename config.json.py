#!/usr/bin/python3

import json
import config

with open('/opt/allsky.py/config.py.json', 'w') as f:
	f.write(json.dumps({
		'name':			config.name,
		'ccd':			config.ccd,
		'sensors':		config.sensors,
		'archive':		config.archive,
		'video':		config.video,
		'relay':		config.relay,
		'db':			config.db,
		'path':			config.path,
		'timestamp':	config.timestamp,
	}))
