import pika
import json

def lambda_handler(event, context):
    user = event.get('user', '')
    documents = event.get('documents', [])

    if not user or not documents:
        return {
            'statusCode': 400,
            'body': json.dumps('Missing user or documents')
        }
    
    credentials = pika.PlainCredentials("guest", "guest")
    parameters = pika.ConnectionParameters(host="a5c51e88038e34e18ac2e8fc6e6281e7-1376501245.us-east-1.elb.amazonaws.com", port=5672, credentials=credentials)
    connection = pika.BlockingConnection(parameters=parameters)

    channel = connection.channel()
    channel.queue_declare(queue='etl')

    for document in documents:
        data = {
            'user': user,
            'documents': [document]
        }
        channel.basic_publish(
            exchange="", 
            routing_key='etl', 
            body=json.dumps(data)
        )

    return {
        'statusCode': 200,
        'body': json.dumps('Documents queued for ingestion')
    }
