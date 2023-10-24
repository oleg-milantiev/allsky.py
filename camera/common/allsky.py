#!/usr/bin/python3

from astropy.io import fits
import config
from datetime import datetime
import json
import logging
import MySQLdb
import numpy as np
import pika # rabbitmq client
import signal
import sys
import time
import os
import uuid

def terminate(signal,frame):
	global camera;

	camera.purge()
	print("Start Terminating: %s" % datetime.now())
	sys.exit(0)

signal.signal(signal.SIGTERM, terminate)


def reload(ch, method, properties, body):
	print(" [x] Received RELOAD")
	ch.basic_ack(delivery_tag=method.delivery_tag)
	sys.exit(0);

# Класс общения с docker.camera контейнером через rabbitmq в шаблоне RPC-Client
class CameraClient(object):

	def __init__(self):
		self.connection = pika.BlockingConnection(
			pika.ConnectionParameters(
				os.getenv('RABBITMQ_HOST'),
				os.getenv('RABBITMQ_PORT'),
				'/',
				pika.PlainCredentials(
					os.getenv('RABBITMQ_DEFAULT_USER'),
					os.getenv('RABBITMQ_DEFAULT_PASS'))))

		self.channel = self.connection.channel()

		self.channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_PROCESS'), durable=True)
		self.channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_ALLSKY'), durable=True)

		result = self.channel.queue_declare(queue='camera_callback', exclusive=True)
		self.callback_queue = result.method.queue

		self.channel.basic_consume(
			queue=self.callback_queue,
			on_message_callback=self.on_response,
			auto_ack=True)

		self.response = None
		self.corr_id = None

		self.channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_ALLSKY'), on_message_callback=reload)

	def purge(self):
		self.channel.queue_purge(os.getenv('RABBITMQ_QUEUE_CAMERA'))

	def on_response(self, ch, method, props, body):
		if self.corr_id == props.correlation_id:
			self.response = body

	def call(self, gain, exposure, bin):
		self.response = None
		self.corr_id = str(uuid.uuid4())
		self.channel.basic_publish(
			exchange='',
			routing_key=os.getenv('RABBITMQ_QUEUE_CAMERA'),
			properties=pika.BasicProperties(
				reply_to=self.callback_queue,
				correlation_id=self.corr_id,
			),
			body=json.dumps({'gain': gain, 'exposure': exposure, 'bin': bin}))
		self.connection.process_data_events(time_limit=exposure + 20)

		return str(self.response)

def findExpo():
	global web, exposure, gain, bin, avg, left, right, attempt

	'''
	# Надо найти следующие bin / gain / exp, даже если удачная выдержка

	Используем обучающуюся нейросетку с входами:
	- date, time, dayPart, moon из эфемеед [1-4]
	- clear / cloud из yolo [5]
	- stardetect из scipy [6]
	- avg, bin / gain / exposure из предыдущего кадра [7-10]
	
	Функция loss:
	- попадание в avgMin / avgMax = 0.5
	- приближение к avgAvg = 0.5
	
	На выходе нужны новые:
	- bin / gain / exposure
	
	Мне нужна мультивыходная регрессия! (10 -> 3)
	- получен кадр, имеем 10 входов
	- по ним получаем новые bin / gain / exp
	- делаем новый кадр, получаем avg
	- имеем loss функцию
	не, херь какая-то)
	
	таблица из 10 входов, 3 выходов и avg (по нему loss)
	а ещё надо учитывать 3..5 предыдущих кадров

	Нужны ли эти данные?
	дата(день) - Дата всё время разная
	время - повторяется, но не привязано к солнцу / Луне

	Датасет. То, что повторяется, имеет закономерности:

	Нужны ли dayPart и dayPartTime? Или достаточно sunAltAz, moonAltAz, moonPhase?
	dayPart - {0 = day | 0.33 = morning | 0.66 = evening | 1 = night}
	dayPartTime - 0..1 доля части дня. ex. полдень = day, 0.5
	moonPhase - 0..1 фаза Луны
	moonAlt - 0..1 высота Луны
	cloud - 0..1 clear / cloud из YOLO
	starsCount - int16 кол-во звёзд из scipy

	was3*** - 3 кадра назад, 4 параметра
	was2*** - 2 кадра назад, 4 параметра

	wasAvg - 0..1 среднее по прошлому кадру (0.5 идеал)
	wasBin - {0 | 1} (0 = bin1, 1 = bin2) бин прошлого кадра
	wasGain - 0..1 gain прошлого кадра
	wasExp - 0..1 exp/55 прошлого кадра (1 = 55 секунд)

	nowAvg - 0..1 среднее по кадру (0.5 идеал)
	nowBin - {0 | 1} (0 = bin1, 1 = bin2) бин кадра
	nowGain - 0..1 gain кадра
	nowExp - 0..1 exp/55 кадра (1 = 55 секунд)

	--
	nowAvg используется для loss
	Остальные три now* - искомый результат по всем остальным параметрам.

	--
	*avg считаются = 0.5, если:
	- пережОг и выдержка, бин и gain = min
	- недожОг и выдержка, bin и gain = max
	То есть модель сделала что могла, дальше камера не тянет
	Учесть, что лучше недожОг, чем пережОг.

	--
	А не привинтить ли к датасету ещё и показания погодника в этот момент?
	
	регрессия с множеством выходов
	https://scikit-learn.org/stable/modules/generated/sklearn.multioutput.MultiOutputRegressor.html
	
	RNN
	https://habr.com/ru/articles/701798/ -> https://github.com/LevPerla/Time_Series_Prediction_RNN
	
	ARIMA
	https://pythonpip.ru/examples/model-arima-v-python
	'''

	if gain < web['ccd']['gainMin']:
		gain = web['ccd']['gainMin']

	if gain > web['ccd']['gainMax']:
		gain = web['ccd']['gainMax']

	gainWas = gain
	binWas = bin

	if exposure < (web['ccd']['expMin'] + (web['ccd']['expMax'] - web['ccd']['expMin']) * 0.01) and avg > web['ccd']['avgMax']:
		logging.debug('Выдержка < 1%, но всё ещё много света - опущу gain / bin')

		if gain > web['ccd']['gainMin']:
			gain -= web['ccd']['gainStep']

			if gain < web['ccd']['gainMin']:
				gain = web['ccd']['gainMin']

			logging.debug('Gain ещё есть куда опускать. Опустил до {}'.format(gain))
		else:
			if bin != 1:
				logging.debug('Gain уже минимальный. Опущу bin до 1')

				bin = 1

		if gainWas != gain or binWas != bin:
			return

	if exposure > (web['ccd']['expMin'] + (web['ccd']['expMax'] - web['ccd']['expMin']) * 0.85) and avg < web['ccd']['avgMin']:
		logging.debug('Выдержка > 85%, но всё ещё мало света - подниму gain / bin')

		if gain < web['ccd']['gainMax']:
			gain += web['ccd']['gainStep']

			if gain > web['ccd']['gainMax']:
				gain = web['ccd']['gainMax']

			logging.debug('Gain ещё есть куда поднимать. Поднял до {}'.format(gain))
		else:
			if bin != 2:
				logging.debug('Gain уже максиамльный. Поднял бин до 2')

				bin = 2

		if gainWas != gain or binWas != bin:
			return

	# выдержка в пределах min ... max, но ещё не предельная - пробую подобрать выдержку
	if avg > web['ccd']['avgMax']:
		logging.debug('Right сузился и стал {}'.format(exposure))

		right = exposure

		if attempt > 1:
			left /= 1.1
			left -= 0.1 # когда ex.: 0.002 делишь на 1.1, то идти к expMin можно вечно. Нужен форсаж на низких!

			if left < web['ccd']['expMin']:
				left = web['ccd']['expMin']

			logging.debug('Left расширился и стал {}'.format(left))

#		if attempt > 5:
#			logging.debug('Очень долго иду к нулю. Поставлю exp = expMin')

#			exposure = web['ccd']['expMin']


	if avg < web['ccd']['avgMin']:
		logging.debug('Left сузился и стал {}'.format(exposure))

		left = exposure

		if attempt > 1:
			right *= 1.1

			logging.debug('Right расширился и стал {}'.format(right))

	exposure = left + (right - left) / 2

	if exposure < web['ccd']['expMin']:
		exposure = web['ccd']['expMin']
	if exposure > web['ccd']['expMax']:
		exposure = web['ccd']['expMax']

		if right > web['ccd']['expMax']:
			right = web['ccd']['expMax']
			logging.debug('Right стукнулся о край и стал = expMax = {}'.format(right))

	return


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

camera = CameraClient()

minute = datetime.now().strftime("%Y-%m-%d_%H-%M")
bin = 1
gain = web['ccd']['gainMin']
exposure = web['ccd']['expMin']

attempt = 0
left = web['ccd']['expMin']
right = web['ccd']['expMax']

while True:
	logging.debug('Получаю новый кадр...')

	while True:
		# rabbit - получение кадра с начальным exposure / gain / bin
		camera.purge()
		if camera.call(gain=gain, exposure=exposure, bin=bin) is None:
			logging.error('Не смог отправить запрос к rabbitmq')
			sys.exit(-1)

		try:
			fit = fits.open('/fits/current.fit', mode='update')
			hdu = fit[0]
		except:
			hdu = None
			logging.error('Не получил fit от контейнера камеры')

		if hdu is not None and round(hdu.header['EXPTIME'], 2) == round(exposure, 2):
			break;

		if hdu is not None:
			# старый кадр. Ждём запрошенного
			logging.info('Выдержка полученного кадра не соответствует запрошенной '+ str(exposure) +' != '+ str(hdu.header['EXPTIME']))

	# Подсчёт среднего по центру кадра
	center = 50

	if 'ccd' in web and 'center' in web['ccd']:
		center = web['ccd']['center']

	if 0 < center <= 100:
		logging.debug('Среднее по центральным {}%'.format(center))
		avg = np.mean(hdu.data[
			int(hdu.data.shape[0] * (50 - center / 2) / 100):int(hdu.data.shape[0] * (50 + center / 2) / 100),
			int(hdu.data.shape[1] * (50 - center / 2) / 100):int(hdu.data.shape[1] * (50 + center / 2) / 100)])

		hdu.header.set('AVGPART', center, 'Average measure image center part in percent')
		hdu.header.set('AVG', avg, 'Average measured value')

		fit.close()

	logging.info('Получил кадр выдержкой {} сек. со средним {}'.format(exposure, avg))

	attempt += 1

	if (
		(web['ccd']['avgMin'] < avg < web['ccd']['avgMax'])		# удачная экспозиция
		or (attempt == 10)										# или кол-во попыток максимально
		or (attempt > 6 and avg < web['ccd']['avgMax'])			# или после шестой попытки изображение не горелое (компромисс)
																# или максимум выдержки, gain и bin, но avg мало
		or (exposure == web['ccd']['expMax'] and gain == web['ccd']['gainMax'] and bin == 2 and avg < web['ccd']['avgMin'])
																# или минимум выдержки, gain и bin, но avg много
		or (exposure == web['ccd']['expMin'] and gain == web['ccd']['gainMin'] and bin == 1 and avg > web['ccd']['avgMax'])):

		logging.debug('Удачная экспозиция или дальше некуда крутить, или кол-во попыток превышено')

		attempt = 0

		os.system('mv /fits/current.fit /fits/'+ minute +'.fit')
		logging.info('Файл {}.fit сохранён'.format(minute))

		# Если хочется AI классификации кадра, сначала пусть он отработает и впишет свои заголовки в фит.
		# Потом он позовёт process.py сам
		camera.channel.basic_publish(
			exchange='',
			routing_key=os.getenv('RABBITMQ_QUEUE_YOLO') if 'yolo' in web['processing'] and 'enable' in web['processing']['yolo'] and web['processing']['yolo']['enable'] else os.getenv('RABBITMQ_QUEUE_PROCESS'),
			body=minute,
			properties=pika.BasicProperties(
				delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
				))

		logging.debug('Жду следующей минуты')

		while True:
			now = datetime.now().strftime("%Y-%m-%d_%H-%M")
			if now != minute:
				break
			time.sleep(1)

		minute = now

	else:
		logging.debug('Неудачная экспозиция. И ещё есть что подобрать')

		findExpo()

		logging.info('Попытка {}. Новая выдержка {}, gain {}, bin {}'.format(attempt, exposure, gain, bin))
