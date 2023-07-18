#!/usr/bin/python3

import config
from datetime import datetime, timedelta
import json
import logging
import MySQLdb
import os
import re
import time

# Чтение конфига
db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
	 database=config.db['database'], charset='utf8')

cursor = db.cursor()

web = {}
cursor.execute('select id, val from config')
for row in cursor.fetchall():
	web[row[0]] = json.loads(row[1])

# Старт
logging.basicConfig(filename=config.log['path'], level=config.log['level'])

logging.info('[+] Start')


minute = datetime.now().strftime("%Y-%m-%d_%H-%M")

#import MySQLdb
#db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
#							 database=config.db['database'], charset='utf8')
#db.autocommit(True)
#cursor = db.cursor()

# Задачи watchdog
# + сбор мусора (архив фото, видео, фитов)
# - есть ли место?
# - получен ли кадр? Перезапуски, если нет
# - жива ли база? Перезапуск, если что
# - жив ли rabbit? Перезапуск, если что
# - живы ли rabbit-worker'ы:
#      - allsky
#      - process
#      - camera
# - жив ли веб:
#      - nginx
#      - php
# - (отдельно) генерация видео
# - реле (грелка)
# - все задачи уместились в 1 минуту?

#for relay in config.relay:
#	if 'hotter' in relay:
#		hotter = relay
#		hotter['stage'] = 0
#		hotter['state'] = 0
#		hotter['percent'] = 0
#		break


#def hotterRelay(state):
#	global hotter, db, cursor
#
#	hotter['state'] = state
#
#	f = open('/sys/class/gpio/gpio{}/value'.format(hotter['gpio']), 'wt')
#	f.write('{}'.format(state))
#	f.close()
#
#	ts = int(time.time())
#	cursor.execute('replace into relay (id, state, date) values ("{}", {}, {})'.format(hotter['name'], state, ts))
#	db.commit()
#
#	logging.debug('Реле обогрева {}'.format('включено' if state == 1 else 'выключено'));


#	# watchdog не контролирует время начального подбора выдержки - оно может быть значительным
#	if savedDate and (savedDate + timedelta(seconds=600)) < datetime.now():
#		# а потом проверяет давно ли получен кадр
#		logging.error('Уже 10 минут камера не записывает кадры. Попытка рестарта allsky.py через supervisord')
#		sys.exit(1)

#	if hotter:
#		if hotter['stage'] == 0:
#			import json
#
#			cursor.execute('select val from config where id = "hotPercent"')
#			row = cursor.fetchone()
#
#			hotter['percent'] = int(json.loads(row['val'])) if row else 0
#			if hotter['percent'] > 0:
#				hotterRelay(1)
#
#		hotter['stage'] += 1
#
#		if (hotter['stage'] * 10) > hotter['percent'] and hotter['state'] == 1:
#			hotterRelay(0)
#
#		if hotter['stage'] == 10:
#			hotter['stage'] = 0
#
#	time.sleep(6)

folders = {
	'jpg': '/web/snap/',
	'fit': '/web/fits/',
	'mp4': '/web/video/',
}

while True:

	# удаление старых жпегов и фитов
	for ext in folders:
		old = datetime.now() - timedelta(web['archive'][ext])

		for f in os.listdir(folders[ext]):
			if os.path.isfile(folders[ext] + f):
				result = re.match(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2}).' + ext, f)

				if result:
					date = datetime(int(result.group(1)), int(result.group(2)), int(result.group(3)),
									int(result.group(4)), int(result.group(5)))

					if date < old:
						logging.debug('Файл ' + f + ' удалён')
						os.remove(folders[ext] + f)

	logging.info('[+] Waiting next minute')

	while True:
		now = datetime.now().strftime("%Y-%m-%d_%H-%M")
		if now != minute:
			break
		time.sleep(1)

	minute = now
