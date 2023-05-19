#!/usr/bin/python3
import pika
import time
import os
import json

connection = pika.BlockingConnection(
  pika.ConnectionParameters(
    os.getenv('RABBITMQ_HOST'),
    os.getenv('RABBITMQ_PORT'),
    '/',
    pika.PlainCredentials(
      os.getenv('RABBITMQ_DEFAULT_USER'),
      os.getenv('RABBITMQ_DEFAULT_PASS'))))

channel = connection.channel()

channel.queue_declare(queue=os.getenv('RABBITMQ_QUEUE'), durable=True)

message = {
  'gain': 10,
  'exposure': 0.1
  }

channel.basic_publish(
  exchange='',
  routing_key=os.getenv('RABBITMQ_QUEUE'),
  body=json.dumps(message),
  properties=pika.BasicProperties(
    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
  ))

print(" [x] Sent %r" % message)
connection.close()
