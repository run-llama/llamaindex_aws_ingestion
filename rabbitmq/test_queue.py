import json
import pika

from llama_index import Document

rabbitmq_url = "a3ad05b37871d4dd4a5dfbd8c573230e-623959034.us-east-1.elb.amazonaws.com"
rabbitmq_user = "guest"
rabbitmq_password = "guest"

credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
parameters = pika.ConnectionParameters(
    host=rabbitmq_url, 
    port=5672, 
    credentials=credentials
)
connection = pika.BlockingConnection(parameters=parameters)
channel = connection.channel()
channel.queue_declare(queue='etl')

documents = [Document(text="logan")]
data = {
    'user': "Logan",  # must be upper-case
    'documents': [document.json() for document in documents]
}

channel.basic_publish(exchange="", routing_key='etl', body=json.dumps(data))

def callback(ch, method, properties, body):
  print(body, flush=True)
  print("Success! Use `ctrl+c` to exit.", flush=True)

channel.basic_consume(queue='etl', on_message_callback=callback, auto_ack=True)
channel.start_consuming()
