#!/usr/bin/python3

import config

import MySQLdb
db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
							 database=config.db['database'], charset='utf8')
db.autocommit(True)
cursor = db.cursor()

# Задачи watchdog
# - есть ли место?
# - получен ли кадр? Перезапуски, если нет
# - жива ли база? Перезапуск, если что
# - жив ли gearman? Перезапуск, если что

# - (отдельно) генерация видео
# - реле (грелка)
# - сбор мусора
# - детектор звёзд

for relay in config.relay:
	if 'hotter' in relay:
		hotter = relay
		hotter['stage'] = 0
		hotter['state'] = 0
		hotter['percent'] = 0
		break


def hotterRelay(state):
	global hotter, db, cursor

	hotter['state'] = state

	f = open('/sys/class/gpio/gpio{}/value'.format(hotter['gpio']), 'wt')
	f.write('{}'.format(state))
	f.close()

	ts = int(time.time())
	cursor.execute('replace into relay (id, state, date) values ("{}", {}, {})'.format(hotter['name'], state, ts))
	db.commit()

	logging.debug('Реле обогрева {}'.format('включено' if state == 1 else 'выключено'));


while ccd:
	# watchdog не контролирует время начального подбора выдержки - оно может быть значительным
	if savedDate and (savedDate + timedelta(seconds=600)) < datetime.now():
		# а потом проверяет давно ли получен кадр
		logging.error('Уже 10 минут камера не записывает кадры. Попытка рестарта allsky.py через supervisord')
		sys.exit(1)

	if hotter:
		if hotter['stage'] == 0:
			import json

			cursor.execute('select val from config where id = "hotPercent"')
			row = cursor.fetchone()

			hotter['percent'] = int(json.loads(row['val'])) if row else 0
			if hotter['percent'] > 0:
				hotterRelay(1)

		hotter['stage'] += 1

		if (hotter['stage'] * 10) > hotter['percent'] and hotter['state'] == 1:
			hotterRelay(0)

		if hotter['stage'] == 10:
			hotter['stage'] = 0

	time.sleep(6)
