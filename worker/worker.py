import json
import os
import threading

import fastapi
import pika
import uvicorn
import weaviate

from llama_index.embeddings import TextEmbeddingsInference
from llama_index.ingestion import IngestionPipeline
from llama_index.text_splitter import TokenTextSplitter
from llama_index.schema import Document
from llama_index.vector_stores import WeaviateVectorStore


app = fastapi.FastAPI()


def worker_thread():
    """Worker thread that runs the ingestion pipeline using rabbitmq."""
    weaviate_api_key = os.environ['WEAVIATE_API_KEY']
    weaviate_url = os.environ['WEAVIATE_URL']

    auth_config = weaviate.AuthApiKey(api_key=weaviate_api_key)
    
    rabbitmq_url = os.environ['RABBITMQ_URL']
    rabbitmq_user = os.environ['RABBITMQ_USER']
    rabbitmq_password = os.environ['RABBITMQ_PASSWORD']

    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
    parameters = pika.ConnectionParameters(
        host=rabbitmq_url, 
        port=5672, 
        credentials=credentials
    )
    connection = pika.BlockingConnection(parameters=parameters)
    channel = connection.channel()
    channel.queue_declare(queue='etl')

    def callback(ch, method, properties, body):
        try:
            data = json.loads(body.decode('utf-8'))
            documents = [Document.parse_raw(d) for d in data['documents']]

            user = data['user']
            user = user[0].upper() + user[1:]

            client = weaviate.Client(url=weaviate_url, auth_client_secret=auth_config)
            vector_store = WeaviateVectorStore(weaviate_client=client, class_prefix=user)

            tei_url = os.environ['TEI_URL']

            # setup pipeline
            ingestion_pipeline = IngestionPipeline(
                transformations=[
                    TokenTextSplitter(chunk_size=512),
                    TextEmbeddingsInference(
                        base_url=tei_url,
                        embed_batch_size=10,
                        model_name="BAAI/bge-large-en-v1.5"
                    ),
                ],
                vector_store=vector_store,
            )

            # ingest data directly into the users vector db
            ingestion_pipeline.run(documents=documents)
        except Exception as e:
            print("Error during ingestion pipeline: ", e)
            pass

    channel.basic_consume(queue='etl', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()


@app.get('/health')
def health():
    return {'status': 'ok'}


if __name__ == '__main__':
    # start worker thread
    threading.Thread(target=worker_thread).start()

    # start webserver
    uvicorn.run(app, host='0.0.0.0', port=8000)
