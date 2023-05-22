#!/usr/bin/python3

import json
import config

with open('/opt/allsky.py/config.py.json', 'w') as f:
	f.write(json.dumps({
		'db':			config.db,
		'path':			config.path,
	}))
