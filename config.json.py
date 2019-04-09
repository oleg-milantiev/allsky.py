#!/usr/bin/python3

import json
import config

print(json.dumps({
	'name':			config.name,
	'ccd':			config.ccd,
	'archive':		config.archive,
	'video':		config.video,
	'relay':		config.relay,
	'db':			config.db,
	'path':			config.path,
	'timestamp':	config.timestamp,
}))