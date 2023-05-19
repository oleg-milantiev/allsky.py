#!/usr/bin/python3
import pika
import time
import os
import json
import uuid

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

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

        self.response = None
        self.corr_id = None

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, gain, exposure):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key=os.getenv('RABBITMQ_QUEUE'),
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=json.dumps({'gain': gain, 'exposure': exposure}))
        self.connection.process_data_events(time_limit=exposure + 5)
        return str(self.response)


camera = CameraClient()

print(" [x] Requesting Snap(10, 0.1)")
response = camera.call(gain=10, exposure=0.1)
print(" [.] Got %r" % response)

