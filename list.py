#!/usr/bin/python3

import config

import os
import sys
import time
import logging
import numpy
from datetime import datetime


import PyIndi

class IndiClient(PyIndi.BaseClient):
	device = None

	def __init__(self):
		super(IndiClient, self).__init__()
		self.logger = logging.getLogger('PyQtIndi.IndiClient')
		self.logger.info('creating an instance of PyQtIndi.IndiClient')
	def newDevice(self, d):
		self.logger.info("new device " + d.getDeviceName())
		self.device = d

	def newProperty(self, p):
		self.logger.info("new property "+ p.getName() + " for device "+ p.getDeviceName())

	def removeProperty(self, p):
		self.logger.info("remove property "+ p.getName() + " for device "+ p.getDeviceName())

	def newSwitch(self, svp):
		self.logger.info ("new Switch "+ svp.name.decode() + " for device "+ svp.device.decode())

	def newNumber(self, nvp):
		self.logger.info("new Number "+ nvp.name.decode() + " for device "+ nvp.device.decode())

	def newText(self, tvp):
		self.logger.info("new Text "+ tvp.name.decode() + " for device "+ tvp.device.decode())
	def newLight(self, lvp):
		self.logger.info("new Light "+ lvp.name.decode() + " for device "+ lvp.device.decode())
	def newMessage(self, d, m):
		self.logger.info("new Message "+ d.messageQueue(m).decode())
	def serverConnected(self):
		print("Server connected ("+self.getHost()+":"+str(self.getPort())+")")
	def serverDisconnected(self, code):
		self.logger.info("Server disconnected (exit code = "+str(code)+","+str(self.getHost())+":"+str(self.getPort())+")")

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

indiclient=IndiClient()

indiclient.setServer(config.indi['host'], config.indi['port'])

print("Connecting and waiting 2secs")

if (not(indiclient.connectServer())):
	 print("No indiserver running on "+indiclient.getHost()+":"+str(indiclient.getPort())+" - Try to run")
	 print("  indiserver indi_simulator_telescope indi_simulator_ccd")
	 sys.exit(1)

time.sleep(2)

while True:
	time.sleep(1)

