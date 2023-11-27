#!/usr/bin/python3

from astropy.io import fits
import config
from datetime import datetime, timedelta
import ephem
import glob
import json
import logging
import MySQLdb
import math
import numpy
import os
import pika
from PIL import Image
import re
import signal
import subprocess
import sys
import time
from threading import Thread

sys.path.insert(0, '/common')
import lib

def terminate(signal,frame):
	print("Start Terminating: %s" % datetime.now())

	global running
	running = False
	thread.join()

	print(" [x] Watchdog thread stopped")

	sys.exit(0)

signal.signal(signal.SIGTERM, terminate)


web = lib.getWebConfig()

logging.basicConfig(filename=config.log['path'], level=config.log['level'])
logging.info('[+] Start')

'''
tbd

if 'uptime' in web and float(web['uptime']) > lib.getUptime():
	for relay in web['relays']:
		f = open('/sys/class/gpio/export', 'wt')
		f.write(relay['gpio'])
		f.close()

	time.sleep(0.1)

	for relay in web['relays']:
		f = open('/sys/class/gpio/gpio{}/direction'.format(relay['gpio']), 'wt')
		f.write('out')
		f.close()

		os.chown('/sys/class/gpio/gpio{}/value'.format(relay['gpio']), pwd.getpwnam("www-data").pw_uid, grp.getgrnam("www-data").gr_gid)

	time.sleep(0.1)

	for relay in web['relays']:
		cursor.execute('SELECT state FROM relay where id = "{}"'.format(relay['name']))
		state = cursor.fetchone()

		f = open('/sys/class/gpio/gpio{}/value'.format(relay['gpio']), 'wt')
		f.write('{}'.format(state['state']) if state else '0')
		f.close()
'''


def reload(ch, method, properties, body):
	print(" [x] Received RELOAD")
	ch.basic_ack(delivery_tag=method.delivery_tag)

	global running
	running = False
	thread.join()

	print(" [x] Watchdog thread stopped")

	sys.exit(0);


def watchdog():
	print(' [*] Start watchdog thread')
	global web

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

	minute = datetime.now().strftime("%Y-%m-%d_%H-%M")
	hourSensor = datetime.now().strftime("%Y-%m-%d_%H")
	sunrisePlusHour = None

	while running:

		now = datetime.now()

		#print('"now" is '+ now.strftime('%d/%m/%Y %H:%M:%S'))

		db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
			 database=config.db['database'], charset='utf8')

		cursor = db.cursor()


		# TBD контроль за запущенными докерами. А пока просто список в сенсоры (и оттуда - в заббикс)

		dockerMap = {
			'allsky-allsky': 0,   #+cycle
			'allsky-camera': 1,   #-cycle - надо выделить универсального INDI клиента с автопоиском камеры
			'allsky-db': 2,
			'allsky-indi': 3,
			'allsky-nginx': 4,
			'allsky-php': 5,
			'allsky-process': 6,  #+cycle
			'allsky-rabbit': 7,
			'allsky-sensor': 8,   #+cycle
			'allsky-watchdog': 9, #+cycle
			'allsky-yolo': 10     #-cycle тут нет mysql вовсе
		}

		'''
		docker inspect --format='{{json .State}}' allsky-watchdog
		{"Status":"running","Running":true,"Paused":false,"Restarting":false,"OOMKilled":false,"Dead":false,"Pid":319830,"ExitCode":0,"Error":"","StartedAt":"2023-11-25T18:16:09.768754342Z","FinishedAt":"2023-11-25T18:16:09.317634819Z"}

		docker inspect --format='{{.State.StartedAt}}' allsky-watchdog
		'''

		for item in dockerMap:
			startedAt = os.popen("/docker inspect --format='{{.State.StartedAt}}' "+ item).read()
			#2023-11-25T06:51:52.920311027Z
			#"Status": "running",
			#"Status": "restarting",

			# todo а в локальные сенсоры надо это записывать?
			cursor.execute("""REPLACE INTO sensor_last(date, channel, type, val)
				VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
				""" % {"time": now.timestamp(), "channel": dockerMap[item], "type": 'docker-started', "val": datetime.strptime(startedAt[:19] +'+00:00', '%Y-%m-%dT%H:%M:%S%z').timestamp() })

		todaySunrise = lib.getTodaySunrise(now)
		#print('Today sunrise at '+ todaySunrise.strftime("%d/%m/%Y %H:%M:%S"))
		#if sunrisePlusHour is None:
		#	print('sunrisePlusHour is None')
		#else:
		#	print('day of sunrise is '+ sunrisePlusHour.strftime('%d'))
		#print('day of now is '+ now.strftime('%d'))
		if now > (todaySunrise + timedelta(hours=1)) and (sunrisePlusHour is None or sunrisePlusHour.strftime('%d') != now.strftime('%d') ):

			logging.info('[+] Sunrise +1h')
			sunrisePlusHour = now

			videoFilename = '/web/video/'+ now.strftime('%Y-%m-%d') +'.mp4'
			keoFilename = '/web/keogram/keogram-'+ now.strftime('%Y-%m-%d') +'.jpg'
			if not os.path.isfile(videoFilename):
#			if not os.path.isfile(keoFilename):

				observatory = lib.getObservatory()

				if observatory:
					observatory.date = todaySunrise 
					begin = observatory.previous_setting(ephem.Sun()).datetime() - timedelta(hours=1)
					end = todaySunrise + timedelta(hours=1)

					logging.debug('[.] Begin {}, end {}'.format(begin, end))

					files = []
					minWidth = None
					minHeight = None

					for f in sorted(glob.glob('/web/snap/????-??-??_??-??.jpg')):
						result = re.match(r'/web/snap/(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2}).jpg', f)

						if result:
							date = datetime(int(result.group(1)), int(result.group(2)), int(result.group(3)), int(result.group(4)), int(result.group(5))) - timedelta(hours=int(web['observatory']['timezone']))

							if date >= begin and date <= end:
								try:
									im = Image.open(f)

									files.append(f)

									if minWidth is None or im.size[0] < minWidth:
										minWidth = im.size[0]

									if minHeight is None or im.size[1] < minHeight:
										minHeight = im.size[1]
								except:
									pass

					if len(files) > 5 and minWidth is not None and minHeight is not None:
						logging.debug('[.] Found suitable images: {}, minWidth={}, minHeight={}'.format(len(files), minWidth, minHeight))
						keogram = Image.new('RGB', (len(files), minHeight), 'black')

						for f in glob.glob('/web/snap/day-*.jpg'):
							os.remove(f)

						i = 0
						for f in files:
							im = Image.open(f)
							# Image.fromarray(numpy.mean(im, axis=1).reshape(keogram.size[1], 1, 3).astype('uint8')) - average keo
							if im.size[0] != minWidth or im.size[1] != minHeight:
								im.resize((minWidth, minHeight))

							keogram.paste(im.crop( (math.floor(minWidth / 2), 0, math.floor(minWidth / 2) + 1, minHeight) ), (i, 0) )
							os.symlink(f, '/web/snap/day-'+ "%06d" % i +'.jpg')

							i += 1

						keogram.save(keoFilename)

						scale = '{}:{}'.format(minWidth, minHeight)

						if 'cfa' in web['ccd']:
							options = '-vf scale='+ scale
						else:
							options = '-pix_fmt yuv420p -vf format=gray,scale='+ scale

						cmd = '/docker run --rm -v /opt/allsky.py/web:/web olegmilantiev/allsky-ffmpeg ffmpeg -f image2 -i /web/snap/day-%06d.jpg '+ options +' '+ videoFilename
						logging.debug('Run ffmpeg via docker: '+ cmd)
						os.system(cmd)

						for f in glob.glob('/web/snap/day-*.jpg'):
							os.remove(f)

					#else:
					#	todo чтобы больше не запускался

		# every hour remove old sensor data from db
		if hourSensor != now.strftime("%Y-%m-%d_%H") and now.minute > 33:
			print('Removing old sensors data: start')
			hourSensor = now.strftime("%Y-%m-%d_%H")

			cursor.execute('delete from sensor where date < '+ str(time.time() - 86400 * int(web['archive']['sensors'])))

			print('Removing old sensors data: done')

		# remove old jpg, fit, mp4
		for ext in folders:
			old = now - timedelta(web['archive'][ext])

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

		cursor.execute("""REPLACE INTO sensor_last(date, channel, type, val)
			VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
			""" % {"time": time.time(), "channel": 9, "type": 'docker-cycle', "val": time.time() - now.timestamp() })

		db.commit()
		cursor.close()
		db.close()

		while running:
			now = datetime.now().strftime("%Y-%m-%d_%H-%M")
			if now != minute:
				break

			time.sleep(1)

		minute = now

running = True
thread = Thread(target = watchdog)
thread.start()

connection = pika.BlockingConnection(
	pika.ConnectionParameters(
		os.getenv('RABBITMQ_HOST'),
		os.getenv('RABBITMQ_PORT'),
		'/',
		pika.PlainCredentials(
			os.getenv('RABBITMQ_DEFAULT_USER'),
			os.getenv('RABBITMQ_DEFAULT_PASS'))))

channel = connection.channel()

queue = channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_WATCHDOG'), durable=True)
print(' [*] Waiting for messages. To exit press CTRL+C')

channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_WATCHDOG'), on_message_callback=reload)

channel.start_consuming()
