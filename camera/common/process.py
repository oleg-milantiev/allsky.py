#!/usr/bin/python3

"""
AllSky Camera Image Processing Module
===================================

This module handles the image processing pipeline for the AllSky camera system.
It processes astronomical images from the camera, applying various corrections
and enhancements while maintaining scientific validity of the data.

Key Features:
- Hot pixel removal and noise reduction
- Star detection and counting using DAOStarFinder
- Color correction and debayering for CFA sensors
- Image enhancement (white balance, gamma, contrast)
- Metadata annotation (timestamp, location, star count)
- Support for FITS format with header metadata

The module operates as a RabbitMQ consumer, processing images as they arrive
from the camera system. It supports both scientific and visual enhancement
processing paths.

Dependencies:
	- astropy: Astronomical data handling
	- photutils: Astronomical source detection
	- scipy: Scientific computing and image processing
	- PIL: Image processing and annotation
	- pika: RabbitMQ client
	- MySQLdb: Database connectivity

Author: Oleg Milantiev
License: MIT
"""

import lib

import config
import os
import pika
import re
import requests
import scipy
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
import signal
import sys
import time
import json
import MySQLdb
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
from astropy.io import fits
from datetime import datetime, timedelta
from collections.abc import Iterable
#import cv2


def terminate(signal,frame):
	logging.info("Start Terminating: %s" % datetime.now())
	sys.exit(0)

signal.signal(signal.SIGTERM, terminate)

logging.basicConfig(filename=config.log['path'], level=config.log['level'])

logging.info('[+] Start')

web = lib.getWebConfig()

connection = pika.BlockingConnection(
	pika.ConnectionParameters(
		os.getenv('RABBITMQ_HOST'),
		os.getenv('RABBITMQ_PORT'),
		'/',
		pika.PlainCredentials(
			os.getenv('RABBITMQ_DEFAULT_USER'),
			os.getenv('RABBITMQ_DEFAULT_PASS'))))

channel = connection.channel()

channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_PROCESS'), durable=True)
channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_PROCESS'), durable=True)
logging.info(' [*] Waiting for messages. To exit press CTRL+C')

class ImageProcessor:
	"""
	Image processing class for AllSky camera system.
	Handles the processing pipeline for astronomical images including
	corrections and enhancements while maintaining data integrity.
	"""
	def __init__(self, web, hdu, filename):
		self.logger = logging.getLogger(__name__)
		self.stars = None
		self.day_part = None
		self.web = web
		self.hdu = hdu
		self.img = None
		self.filename = filename

	def hot_pixels(self):
		"""
		Remove hot pixels from the image using a hot pixel map.

		Returns:
			bool: True if hot pixels were removed, False if hot pixel map not found
		"""
		binning = self.hdu.header['XBINNING']
		hot_filename = f'/camera/hot-{binning}.png'
		if not os.path.isfile(hot_filename):
			return False

		self.logger.info('Removing hot pixels')
		hot_count = 0

		xy = np.where(np.array(ImageOps.grayscale(Image.open(hot_filename))) == 255)

		for i in range(len(xy[0])):
			x = xy[1][i]
			y = xy[0][i]

			hot_count += 1
			self.hdu.data[y, x] = round((
				float(self.hdu.data[y-1, x-1]) + float(self.hdu.data[y-1, x]) +
				float(self.hdu.data[y-1, x+1]) + float(self.hdu.data[y, x-1]) +
				float(self.hdu.data[y, x+1]) + float(self.hdu.data[y+1, x-1]) +
				float(self.hdu.data[y+1, x]) + float(self.hdu.data[y+1, x+1])
			) / 8)

		self.logger.debug(f'Removed hot pixels: {hot_count}')
		return True

	def median(self):
		"""
		Apply median filter to reduce noise in the image if enabled in settings.

		Returns:
			bool: True if filter was applied
		"""
		if not ('noise' in self.web['processing'] and 
				'median' in self.web['processing']['noise'] and 
				self.web['processing']['noise']['median'] in [3, 5]):
			return False

		kernel_size = self.web['processing']['noise']['median']
		self.logger.info(f'Applying median filter with kernel size: {kernel_size}')
		self.hdu.data = scipy.signal.medfilt2d(self.hdu.data, kernel_size=kernel_size)
		return True

	def update_location(self):
		"""Update location information in HDU header if available."""
		if 'lat' in self.web['observatory'] and self.web['observatory']['lat'] != '':
			self.hdu.header.set('LAT', self.web['observatory']['lat'], 'Observatory latitude')
		if 'lon' in self.web['observatory'] and self.web['observatory']['lon'] != '':
			self.hdu.header.set('LON', self.web['observatory']['lon'], 'Observatory longitude')

	def detect_stars(self):
		"""
		Detect stars in the image if star detection is enabled.

		Returns:
			bool: True if stars were detected
		"""
		if not self.web['processing']['sd']:
			return False

		date_obs = datetime.strptime(self.hdu.header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S')
		self.logger.info('Calculating image statistics and detecting stars')

		# Calculate sigma-clipped statistics
		mean, median, std = sigma_clipped_stats(self.hdu.data, sigma=3.0)

		# Update FITS header with statistics
		self.hdu.header.set('MEAN', mean, 'Mean by whole image')
		self.hdu.header.set('MEDIAN', median, 'Median by whole image')
		self.hdu.header.set('STD-DEV', std, 'Std.dev by whole image')

		self.logger.debug(f'Sigma-clipped statistics: mean={mean}, median={median}, std={std}')

		# Determine day part
		self.day_part = lib.getDayPart(date_obs)
		self.logger.debug(f'Day part: {self.day_part}')
		self.hdu.header.set('DAY-PART', self.day_part, 'Day part')

		self.stars = None
		if self.day_part in ['night', 'night/moon']:
			self.logger.debug('Night time - searching for stars')
			try:
				daofind = DAOStarFinder(
					fwhm=float(self.web['processing']['sd']['fwhm']),
					threshold=float(self.web['processing']['sd']['threshold']) * std
				)
				self.stars = daofind(self.hdu.data - median)
				if self.stars is not None:
					self.logger.debug(f'Found stars: {len(self.stars)}')
					self.hdu.header.set('STAR-CNT', len(self.stars), 'Stars count by whole image using DAOStarFinder')
			except Exception as e:
				self.logger.error(f'Star detection failed: {str(e)}')
				self.stars = None
		return True

	def update_timezone(self):
		"""Update timezone information in HDU header if available."""
		if 'timezone' in self.web['observatory'] and self.web['observatory']['timezone'] != '':
			self.hdu.header.set('TIMEZONE', self.web['observatory']['timezone'], 'Observatory timezone')
		else:
			self.web['observatory']['timezone'] = 0

	def process_color(self, ccd_config, wb_config):
		"""
		Process color image including debayering and white balance.

		Args:
			ccd_config: Dictionary containing CCD configuration
			wb_config: Dictionary containing white balance configuration

		Returns:
			PIL.Image: Processed color image
		"""
		if 'cfa' not in ccd_config:
			return Image.fromarray(
				self.hdu.data if ccd_config['bits'] == 8
				else (self.hdu.data / 256).astype('uint8')
			)

		self.logger.info('Debayering CFA pattern')
		# Convert to 8-bit if needed and apply CFA pattern
		data_8bit = (self.hdu.data if ccd_config['bits'] == 8
					else (self.hdu.data / 256).astype('uint8'))
		rgb = cv2.cvtColor(data_8bit, ccd_config['cfa'])

		# Handle overexposed regions
		img2gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
		_, mask = cv2.threshold(img2gray, 245, 255, cv2.THRESH_BINARY)
		mask_inv = cv2.bitwise_not(mask)
		img_overexposed = cv2.bitwise_and(rgb, rgb, mask=mask)

		# Apply white balance if configured
		if wb_config and 'type' in wb_config:
			self.logger.info(f'Applying white balance: {wb_config["type"]}')
			if wb_config['type'] == 'gain':
				rgb = cv2.xphoto.applyChannelGains(
					rgb,
					wb_config['r'],
					wb_config['g'],
					wb_config['b']
				)
			elif wb_config['type'] == 'simple':
				wb = cv2.xphoto.createSimpleWB()
				rgb = wb.balanceWhite(rgb)
			elif wb_config['type'] == 'gray':
				wb = cv2.xphoto.createGrayworldWB()
				wb.setSaturationThreshold(0.95)
				rgb = wb.balanceWhite(rgb)

		# Combine balanced image with overexposed regions
		img_wb = cv2.bitwise_and(rgb, rgb, mask=mask_inv)
		return Image.fromarray(cv2.add(img_wb, img_overexposed), 'RGB')

	def gamma(self):
		"""
		Apply gamma correction to the image if enabled.
		"""
		if not 'gamma' in self.web['processing']:
			return

		gamma_value = float(self.web['processing']['gamma'])
		if not gamma_value:
			return

		self.logger.info(f'Applying gamma correction: {gamma_value}')
		self.img = ImageEnhance.Brightness(self.img).enhance(gamma_value)

	def auto_contrast(self):
		"""
		Apply automatic contrast adjustment to the image if enabled.
		"""
		if not 'autoContrast' in self.web['processing']:
			return

		cutoff = float(self.web['processing']['autoContrast'])
		self.logger.debug(f'Applying auto contrast with clipping: {cutoff}')
		self.img = ImageOps.autocontrast(self.img, cutoff=cutoff)

	def transpose(self):
		"""
		Apply transposition (rotation/mirror) to the image if enabled.
		"""
		transpose_mode = self.web['processing'].get('transpose', -1)
		if not ('transpose' in self.web['processing'] and 
				0 <= transpose_mode <= 6):
			return

		self.logger.debug(f'Transposing image (rotation/mirror): {transpose_mode}')
		self.img = self.img.transpose(transpose_mode)

	def logo(self):
		"""
		Add logo watermark to the image if enabled.
		"""
		if not ('logo' in self.web['processing'] and 
				'file' in self.web['processing']['logo'] and 
				self.web['processing']['logo'].get('file')):
			return

		self.logger.info('Adding logo watermark')
		try:
			logo_config = self.web['processing']['logo']
			bin = int(self.hdu.header['XBINNING'] if 'XBINNING' in self.hdu.header else 1)
			watermark = Image.open(config['path']['jpg'] + '/' + logo_config['file'])
			x = int(logo_config['x'] / bin)
			y = int(logo_config['y'] / bin)
			self.img.paste(watermark, (x, y))
		except Exception as e:
			self.logger.error(f'Failed to add logo: {str(e)}')

	def annotate(self):
		"""
		Add text annotations to the image if enabled.
		"""
		annotations = self.web['processing'].get('annotation', [])
		if not ('annotation' in self.web['processing'] and 
				isinstance(annotations, Iterable) and 
				len(annotations) > 0):
			return

		self.logger.info('Adding text annotations')
		bin = int(self.hdu.header['XBINNING'] if 'XBINNING' in self.hdu.header else 1)

		# Create transparent overlay for text
		txt = Image.new('RGBA', self.img.size, (255, 255, 255, 0))
		d = ImageDraw.Draw(txt)

		for annotation in annotations:
			# Load font with scaled size
			font = ImageFont.truetype('/camera/sans-serif.ttf',
									int(int(annotation['size']) / bin))

			# Format text based on annotation type
			text = ''
			match annotation['type']:
				case 'stars':
					text = annotation['format'].format(
						len(self.stars) if self.stars is not None else 'n/a')
				case 'yolo-clear':
					text = annotation['format'].format(
						'%0.2f' % (float(self.hdu.header['AI-CLEAR']) * 100)
						if 'AI-CLEAR' in self.hdu.header else 'n/a')
				case 'yolo-cloud':
					text = annotation['format'].format(
						'%0.2f' % (float(self.hdu.header['AI-CLOUD']) * 100)
						if 'AI-CLOUD' in self.hdu.header else 'n/a')
				case 'text':
					text = annotation['format']
				case 'datetime':
					date_obs = datetime.strptime(self.hdu.header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S')
					tz_offset = int(self.web['observatory']['timezone'])
					text = (date_obs + timedelta(hours=tz_offset)).strftime(annotation['format'])
				case 'avg' | 'average':
					text = annotation['format'].format(round(self.hdu.header['AVG']))
				case 'exposure':
					text = annotation['format'].format(round(self.hdu.header['EXPTIME'], 4))
				case _:
					continue

			# Draw text with outline for better visibility
			x = int(int(annotation['x']) / bin)
			y = int(int(annotation['y']) / bin)
			
			# Handle color values that can be either hex strings or RGB tuples
			def parse_color(color_value):
				if isinstance(color_value, str):
					if color_value.startswith('#'):
						# Handle hex color
						color_value = color_value.lstrip('#')
						return tuple(int(color_value[i:i+2], 16) for i in (0, 2, 4))
					else:
						# Handle named colors
						return (255, 255, 255)  # Default to white for invalid colors
				elif isinstance(color_value, (list, tuple)):
					# Handle RGB tuple
					return tuple(int(c) for c in color_value[:3])
				return (255, 255, 255)  # Default to white for any other type

			outline_color = (0, 0, 0) if 'outline' not in annotation else parse_color(annotation['outline'])
			text_color = (255, 255, 255) if 'color' not in annotation else parse_color(annotation['color'])

			for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
				d.text((x+dx, y+dy), text, font=font, fill=outline_color)
			d.text((x, y), text, font=font, fill=text_color)

		# Merge annotations with original image
		self.img = Image.alpha_composite(self.img.convert('RGBA'), txt).convert('RGB')

	def publish(self):
		"""
		Publish the JPG image if publishing is configured.
		Uses a separate thread to avoid blocking the main process.
		"""
		if 'jpg' not in self.web['publish'] or not self.web['publish']['jpg']:
			return

		filename = self.filename.replace(':', '-').replace('T', '_')
		filepath = f'/snap/{filename}.jpg'

		def do_publish():
			try:
				with open(filepath, 'rb') as f:
					r = requests.post(
						self.web['publish']['jpg'],
						files={'file': f},
						data={'name': self.web['observatory']['name'], 'pass': 'kjH3vxzm4G'},
						timeout=10  # 10 seconds timeout
					)
					self.logger.info(f'File {filename} has been published: {r.text}')
			except requests.Timeout:
				self.logger.error(f'Timeout publishing file {filename}')
			except requests.RequestException as e:
				self.logger.error(f'Error publishing file {filename}: {str(e)}')
			except Exception as e:
				self.logger.error(f'Unexpected error publishing file {filename}: {str(e)}')

		# Run publish in a separate thread
		from threading import Thread
		Thread(target=do_publish, daemon=True).start()

	def save_jpg(self):
		"""
		Save the processed image as JPG.
		"""
		self.logger.debug('Writing JPEG file...')
		self.img.save('/snap/' + self.filename + '.jpg')
		self.logger.info('File ' + self.filename + '.jpg has been written.')

		# Create symlink to current.jpg
		if os.path.islink('/snap/current.jpg'):
			os.remove('/snap/current.jpg')
		os.symlink(self.filename + '.jpg', '/snap/current.jpg')

	def process(self):
		"""
		Process the FITS image applying various corrections and enhancements.
		"""
		self.hot_pixels()
		self.median()
		self.update_location()
		self.detect_stars()
		self.update_timezone()

		if 'cfa' in self.web['ccd']:
			self.img = self.process_color(self.web['ccd'], self.web['processing']['wb'])
		else:
			self.img = Image.fromarray(self.hdu.data if self.web['ccd']['bits'] == 8 else (self.hdu.data / 256).astype('uint8'))

		self.gamma()
		self.auto_contrast()
		self.transpose()

		self.logo()
		self.annotate()

		# Save and publish the image
		self.save_jpg()
		self.publish()


def callback(ch, method, properties, body):
	logging.info(" [x] Received %r" % body.decode())
	timeCycleStart = time.time()

	if not re.match(r"\d\d\d\d-\d\d-\d\d_\d\d-\d\d", body.decode()):
		logging.error('[!] Invalid input file format')
		ch.basic_ack(delivery_tag=method.delivery_tag)
		return

	try:
		fit = fits.open('/fits/'+ body.decode() +'.fit', mode='update')
		hdu = fit[0]
	except:
		logging.error('[!] Cannot open FITS file')
		ch.basic_ack(delivery_tag=method.delivery_tag)
		return

	processor = ImageProcessor(web, hdu, body.decode())
	processor.process()

	fit.close()

	ts = datetime.strptime(hdu.header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S').timestamp() + web['observatory']['timezone'] * 3600
	channel = 0  # multicamera support

	# Prepare data for batch insert
	sensor_data = [
		{'time': ts, 'channel': 0, 'type': 'uptime', 'val': lib.getUptime()}
	]

	# Add sensor data if available in header
	header_to_sensor = {
		'EXPTIME': 'ccd-exposure',
		'AVG': 'ccd-average',
		'GAIN': 'ccd-gain',
		'XBINNING': 'ccd-bin',
		'AI-CLEAR': 'ai-clear',
		'AI-CLOUD': 'ai-cloud'
	}

	for header_key, sensor_type in header_to_sensor.items():
		try:
			if header_key in hdu.header:
				sensor_data.append({
					'time': ts,
					'channel': channel,
					'type': sensor_type,
					'val': float(hdu.header[header_key])
				})
		except:
			logging.debug(f'Cannot insert {header_key}')

	# Add star count if available
	if processor.stars is not None:
		sensor_data.append({
			'time': ts,
			'channel': channel,
			'type': 'stars-count',
			'val': len(processor.stars)
		})

	# Add processing cycle time
	sensor_data.append({
		'time': datetime.now().timestamp(),
		'channel': 6,
		'type': 'docker-cycle',
		'val': time.time() - timeCycleStart
	})

	# Batch insert and replace
	if sensor_data:
		# try to break "Lock wait timeout exceeded; try restarting transaction" db hang by new connection
		db2 = MySQLdb.connect(host=config.db['host'], user=config.db['user'], passwd=config.db['passwd'],
			database=config.db['database'], charset='utf8')
		cursor2 = db2.cursor()

		try:
			for data in sensor_data:
				print(data)
				if data['type'] not in ['docker-cycle', 'uptime']:
					# Insert into main sensor table
					cursor2.execute(
						"""INSERT INTO sensor(date, channel, type, val)
						VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)""" % data
					)
				
				# Update last sensor value
				cursor2.execute(
					"""REPLACE INTO sensor_last(date, channel, type, val)
					VALUES (%(time)i, %(channel)i, '%(type)s', %(val)f)""" % data
				)

			db2.commit()
		except Exception as e:
			db2.rollback()
			logging.error(f'Error executing database operations: {str(e)}')

		cursor2.close()
		db2.close()

	logging.info('[+] Done')
	ch.basic_ack(delivery_tag=method.delivery_tag)


def reload(ch, method, properties, body):
	logging.info(" [x] Received RELOAD")
	ch.basic_ack(delivery_tag=method.delivery_tag)
	sys.exit(0)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_PROCESS'), on_message_callback=callback)
channel.basic_consume(queue=os.getenv('RABBITMQ_QUEUE_RELOAD_PROCESS'), on_message_callback=reload)

channel.start_consuming()
