#!/usr/bin/python3

# Standard library imports
import json
import logging
import os
import signal
import sys
import time
import uuid
from datetime import datetime
from functools import lru_cache
from typing import Optional, Dict, Any

# Third-party imports
import MySQLdb
import numpy as np
import pika
from astropy.io import fits

# Local imports
import config
import lib

# Constants for RabbitMQ configuration
RABBITMQ_RECONNECT_DELAY = 5
RABBITMQ_CONNECTION_TIMEOUT = 10
QUEUE_DECLARE_TIMEOUT = 5

def terminate(signal, frame):
    """Clean termination handler with proper cleanup"""
    global camera
    try:
        camera.purge()
        camera.close()  # Ensure connection is properly closed
        logging.info("Clean termination at: %s", datetime.now())
    except Exception as e:
        logging.error("Error during termination: %s", str(e))
    finally:
        sys.exit(0)

signal.signal(signal.SIGTERM, terminate)
signal.signal(signal.SIGINT, terminate)  # Also handle keyboard interrupts

def reload(ch, method, properties, body):
    """Handler for reload signals with proper cleanup"""
    try:
        logging.info("Received RELOAD signal")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.error("Error during reload: %s", str(e))
    finally:
        sys.exit(0)

@lru_cache(maxsize=1)
def get_rabbitmq_params() -> Dict[str, Any]:
    """Cache and return RabbitMQ connection parameters"""
    return {
        'host': os.getenv('RABBITMQ_HOST'),
        'port': os.getenv('RABBITMQ_PORT'),
        'user': os.getenv('RABBITMQ_DEFAULT_USER'),
        'password': os.getenv('RABBITMQ_DEFAULT_PASS'),
        'queue_process': os.getenv('RABBITMQ_QUEUE_PROCESS'),
        'queue_reload': os.getenv('RABBITMQ_QUEUE_RELOAD_ALLSKY'),
        'queue_camera': os.getenv('RABBITMQ_QUEUE_CAMERA')
    }

class CameraClient:
    """RPC Client for communicating with docker.camera container via RabbitMQ"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.response = None
        self.corr_id = None
        self.callback_queue = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to RabbitMQ with retry logic"""
        params = get_rabbitmq_params()
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=params['host'],
                        port=params['port'],
                        credentials=pika.PlainCredentials(
                            params['user'],
                            params['password']
                        ),
                        socket_timeout=RABBITMQ_CONNECTION_TIMEOUT,
                        heartbeat=600  # Increased heartbeat for better connection stability
                    )
                )
                self.channel = self.connection.channel()
                self._setup_queues()
                return
                
            except (pika.exceptions.AMQPConnectionError, pika.exceptions.AMQPChannelError) as e:
                retry_count += 1
                if retry_count == max_retries:
                    logging.error("Failed to connect to RabbitMQ after %d attempts: %s", max_retries, str(e))
                    sys.exit(1)
                logging.warning("Connection attempt %d failed, retrying in %d seconds...", 
                              retry_count, RABBITMQ_RECONNECT_DELAY)
                time.sleep(RABBITMQ_RECONNECT_DELAY)
            
            except Exception as e:
                logging.error("Unexpected error during connection: %s", str(e))
                sys.exit(1)

    def _setup_queues(self) -> None:
        """Setup RabbitMQ queues with improved error handling and timeout"""
        params = get_rabbitmq_params()
        try:
            # Declare durable queues
            for queue in [params['queue_process'], params['queue_reload']]:
                self.channel.queue_declare(
                    queue=queue,
                    durable=True
                )

            # Declare callback queue
            result = self.channel.queue_declare(
                queue='camera_callback',
                exclusive=True
            )
            self.callback_queue = result.method.queue

            # Setup consumers with prefetch count for better load balancing
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=self.callback_queue,
                on_message_callback=self.on_response,
                auto_ack=True
            )
            self.channel.basic_consume(
                queue=params['queue_reload'],
                on_message_callback=reload
            )
                
        except pika.exceptions.AMQPError as e:
            logging.error("Failed to setup RabbitMQ queues: %s", str(e))
            self.close()
            sys.exit(1)

    def purge(self) -> None:
        """Purge camera queue with connection recovery"""
        params = get_rabbitmq_params()
        try:
            if not self.channel or self.channel.is_closed:
                self._connect()
            self.channel.queue_purge(params['queue_camera'])
        except pika.exceptions.AMQPError as e:
            logging.error("Failed to purge queue: %s", str(e))
            self._connect()  # Try to reconnect for next operation

    def on_response(self, ch, method, props, body) -> None:
        """Handle RPC response"""
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, gain: float, exposure: float, bin: int) -> Optional[str]:
        """Make RPC call with improved error handling and connection recovery"""
        params = get_rabbitmq_params()
        try:
            if not self.channel or self.channel.is_closed:
                self._connect()
                
            self.response = None
            self.corr_id = str(uuid.uuid4())
            
            message = json.dumps({
                'gain': gain,
                'exposure': exposure,
                'bin': bin
            })
            
            self.channel.basic_publish(
                exchange='',
                routing_key=params['queue_camera'],
                properties=pika.BasicProperties(
                    reply_to=self.callback_queue,
                    correlation_id=self.corr_id,
                    delivery_mode=2  # Make message persistent
                ),
                body=message
            )
            
            # Add small buffer to timeout for network latency
            timeout = exposure + 20
            self.connection.process_data_events(time_limit=timeout)
            return str(self.response) if self.response else None
            
        except pika.exceptions.AMQPError as e:
            logging.error("Failed to publish message: %s", str(e))
            self._connect()  # Try to reconnect for next operation
            return None
        except Exception as e:
            logging.error("Unexpected error during RPC call: %s", str(e))
            return None

    def close(self) -> None:
        """Properly close connection"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except Exception as e:
            logging.error("Error closing connection: %s", str(e))

def findExpo():
    global web, exposure, gain, bin, avg, left, right, attempt

    '''
    поиск bias?
    лучше avg негорелой части брать
    
    allsky-allsky    | [
    {'exp': 0.0001, 'avg': 13815.888942307693},
     {'exp': 0.17918823819298696, 'avg': 65535.0},
     {'exp': 0.039639573641948006, 'avg': 14647.346988284704},
     {'exp': 0.11837331782711684, 'avg': 65535.0},
     {'exp': 0.027204646932625698, 'avg': 14663.915265804597},
     {'exp': 0.07870764827122712, 'avg': 65057.16998231653}

    (0.27 - bias) = 14663/65535 = 0,2237430380712596
    (0.51 - bias) = 30000/65535 = 0,4577706569008927 !
    (0.78 - bias) = 65057/65535 = 0,9927061875333791

    (0.78-bias) / 65057 = x / 30000
    (0.27-bias) / 14663 = x / 30000

    x = (0.027-bias) / 14663 * 30000 = 0,05524108299802223 => 0,0347814226283844
    x = (0.078-bias) / 65057 * 30000 = 0,03596845842876247 => 0,0313571176045622

    (0.027-bias) * 65057 = (0.078-bias) * 14663
    0.027 * 65057 - 65057*bias = 0.078 * 14663 - 14663*bias
    -50394*bias = 1143,714 - 1756,539
    50394*bias = 612,825
    bias = 0,0121606738897488


    allsky-allsky    | [
    {'exp': 0.0744168060210422, 'avg': 14706.483523983201},
     {'exp': 0.08519466353919876, 'avg': 65535.0},
     {'exp': 0.026423152688254917, 'avg': 15480.05964025199},
     {'exp': 0.06006864129068678, 'avg': 15589.704061671087},
     {'exp': 0.08157709208655865, 'avg': 65535.0},
     {'exp': 0.018092473902682406, 'avg': 15323.948787024758}

    allsky-allsky    | [
    {'exp': 0.05391363759894847, 'avg': 16324.097430371352},
     {'exp': 0.07182421944708149, 'avg': 16413.933330570293},
     {'exp': 0.08526625043590874, 'avg': 65535.0},
     {'exp': 0.0252804976939005, 'avg': 17383.239925950485},
     {'exp': 0.05953668658670006, 'avg': 16690.884811560565},
     {'exp': 0.08135442480707483, 'avg': 65535.0}
    '''

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
            if bin != 2 and web['ccd']['binning'] == 2:
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
            left -= 0.01 # когда ex.: 0.002 делишь на 1.1, то идти к expMin можно вечно. Нужен форсаж на низких!

#			if left < web['ccd']['expMin']:
#				left = web['ccd']['expMin']

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


def findExpo2():
    """
    Automatically adjust exposure, gain and bin settings based on image average and web configs.
    Uses a more sophisticated approach to reach optimal settings faster.
    """
    global web, exposure, gain, bin, avg, left, right, attempt

    # Store initial values for comparison
    gainWas = gain
    binWas = bin

    # Ensure gain is within bounds
    gain = max(web['ccd']['gainMin'], min(web['ccd']['gainMax'], gain))
    
    # Calculate target average (middle of the desired range)
    target_avg = (web['ccd']['avgMin'] + web['ccd']['avgMax']) / 2
    
    # Calculate how far we are from target
    avg_ratio = avg / target_avg if target_avg > 0 else float('inf')
    
    # Adjust settings based on current state
    if avg > web['ccd']['avgMax']:  # Image too bright
        if exposure > web['ccd']['expMin']:
            # First try to reduce exposure
            factor = min(avg / web['ccd']['avgMax'], 1.5)  # Limit adjustment factor
            exposure = max(web['ccd']['expMin'], exposure / factor)
            logging.debug(f'Reducing exposure to {exposure:.3f} (factor: {factor:.2f})')
        elif gain > web['ccd']['gainMin']:
            # Then try to reduce gain
            gain = max(web['ccd']['gainMin'], gain - web['ccd']['gainStep'])
            logging.debug(f'Reducing gain to {gain}')
        elif bin > 1:
            # Finally try to reduce binning
            bin = 1
            logging.debug('Reducing binning to 1')
    
    elif avg < web['ccd']['avgMin']:  # Image too dark
        if bin == 1 and web['ccd']['binning'] == 2:
            # First try to increase binning
            bin = 2
            logging.debug('Increasing binning to 2')
        elif gain < web['ccd']['gainMax']:
            # Then try to increase gain
            gain = min(web['ccd']['gainMax'], gain + web['ccd']['gainStep'])
            logging.debug(f'Increasing gain to {gain}')
        elif exposure < web['ccd']['expMax']:
            # Finally try to increase exposure
            factor = max(web['ccd']['avgMin'] / avg if avg > 0 else 2.0, 1.1)
            factor = min(factor, 4.0)  # Limit maximum increase
            exposure = min(web['ccd']['expMax'], exposure * factor)
            logging.debug(f'Increasing exposure to {exposure:.3f} (factor: {factor:.2f})')
    
    # Fine-tune exposure if we're close to target
    if web['ccd']['avgMin'] * 0.8 < avg < web['ccd']['avgMax'] * 1.2:
        factor = target_avg / avg if avg > 0 else 1.1
        factor = max(0.9, min(1.1, factor))  # Limit fine adjustment to ±10%
        new_exposure = exposure * factor
        if web['ccd']['expMin'] <= new_exposure <= web['ccd']['expMax']:
            exposure = new_exposure
            logging.debug(f'Fine-tuning exposure to {exposure:.3f} (factor: {factor:.2f})')
    
    # Update search boundaries for binary search if needed
    if avg > web['ccd']['avgMax']:
        right = exposure
    elif avg < web['ccd']['avgMin']:
        left = exposure
    
    # Return if gain or bin changed to allow system to stabilize
    if gainWas != gain or binWas != bin:
        return
    
    # Ensure final exposure is within bounds
    exposure = max(web['ccd']['expMin'], min(web['ccd']['expMax'], exposure))
    
    return

web = lib.getWebConfig()

logging.basicConfig(filename=config.log['path'], level=config.log['level'])

logging.info('[+] Start')

camera = CameraClient()

minute = datetime.now().strftime("%Y-%m-%d_%H-%M")
bin = 1
gain = web['ccd']['gainMin']
exposure = web['ccd']['expMin']

attempt = 0
attempts = []
left = web['ccd']['expMin']
right = web['ccd']['expMax']


while True:
    logging.debug('Получаю новый кадр...')
    timeCycleStart = time.time()

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

        if hdu is not None and round(hdu.header['EXPTIME'], 2) == round(exposure, 2) and (not 'GAIN' in hdu.header or ('GAIN' in hdu.header and round(hdu.header['GAIN'], 2) == round(gain, 2))) and int(hdu.header['XBINNING']) == bin:
            break;

        if hdu is not None:
            # старый кадр. Ждём запрошенного
            logging.info('Выдержка / gain / bin полученного кадра не соответствует запрошенной '+ str(round(exposure, 2)) +'/'+ str(gain if 'GAIN' in hdu.header else 'na') +'/'+ str(bin) +' != '+ str(round(hdu.header['EXPTIME'], 2)) +'/'+ str(hdu.header['GAIN'] if 'GAIN' in hdu.header else 'na') +'/'+ str(hdu.header['XBINNING']))

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
        or (exposure == web['ccd']['expMax'] and gain == web['ccd']['gainMax'] and bin == web['ccd']['binning'] and avg < web['ccd']['avgMin'])
                                                                # или минимум выдержки, gain и bin, но avg много
        or (exposure == web['ccd']['expMin'] and gain == web['ccd']['gainMin'] and bin == 1 and avg > web['ccd']['avgMax'])):

        logging.debug('Удачная экспозиция или дальше некуда крутить, или кол-во попыток превышено')

        attempt = 0
        print(attempts)
        attempts = []
        attempts.append({'expWas': exposure, 'avgWas': avg})

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


        # store cycle time
        db = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
                database=config.db['database'], charset='utf8')

        cursor = db.cursor()

        cursor.execute("""REPLACE INTO sensor_last(date, channel, type, val)
                VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)
                """ % {"time": datetime.now().timestamp(), "channel": 0, "type": 'docker-cycle', "val": time.time() - timeCycleStart })

        db.commit()

        cursor.close()
        db.close()


        logging.debug('Жду следующей минуты')

        while True:
            now = datetime.now().strftime("%Y-%m-%d_%H-%M")
            if now != minute:
                break
            time.sleep(1)

        minute = now

    else:
        logging.debug('Неудачная экспозиция. И ещё есть что подобрать')

        attempts.append({'exp': exposure, 'avg': avg})

        findExpo2()

        logging.info('Попытка {}. Новая выдержка {}, gain {}, bin {}'.format(attempt, exposure, gain, bin))
