# LlamaIndex <> AWS

This repository contains the code needed to setup and configure a complete ingestion and retrieval API, deployed to amazon AWS.

This will give a starting point for scaling your data ingestion to handle large volumes of data, as well as learn a bit more about AWS along the way.

The following tech stack is used:
- AWS Lambda for ingestion and retrieval with LlamaIndex
- RabbitMQ for queuing ingestion jobs
- A custom docker image for ingesting data with LlamaIndex
- Huggingface Text Embedding Interface for embedding our data

## Setup

First, ensure you have an AWS account. Ensure you have some quota room for G5 EC2 nodes.

Once you have an account, the following dependencies are needed:
1. [AWS account signup](https://portal.aws.amazon.com/billing/signup#/start/email) 
2. [Install AWS CLI](https://docs.aws.amazon.com/eks/latest/userguide/setting-up.html)
  - Used to authenticate your AWS account for CLI tools
3. [Install eksctl](https://eksctl.io/installation/)
  - Used to create `EKS` clusters easily
4. [Install kubectl](https://docs.aws.amazon.com/eks/latest/userguide/install-kubectl.html)
  - Used to configure and debug deployments, pods, services, etc.
5. [Install krew](https://krew.sigs.k8s.io/docs/user-guide/setup/install/)
  - Used to install extra tools to use with `kubectl`
6. Install rabbitmq operator plugin with krew — `kubectl krew install rabbitmq`
  - Used to easily deploy rabbitmq to a cluster and expose the proper services
7. [Install Docker](https://www.docker.com/products/docker-desktop/)

### 1. Deploying Text Embedding Inteface

```bash
cd tei
sh setup.sh
```

This will create a cluster using eksctl, using g5.xlarge nodes. You can adjust the `--nodes` argument as needed, as well as the number of replicas in the `tei-deployment.yaml` file.

Note the public URL when you run `kubectl get svc`. The URL under `external IP` will be used in `./worker/woker-deployment.yaml`.

For convience, the `setup.sh` script prints the URL for you at the end.

### 2. Deploying RabbitMQ

The setup for RabbitMQ leverages an `operator` -- a specific abstraction in AWS that helps handle all the resources needed for running RabbitMQ.

```
cd raibbitmq
sh setup.sh
```

RabbitMQ will be deployed on a eksctl cluster, where each node shares provisioned storage using EBS. You'll notice in the `setup.sh` file some extra commands to install the EBS add-on, as well as granting IAM permissions for provisioning the storage.

Lastly, we use the `RabbitmqCluster` extension installed by `krew` to easily create our cluster using mostly default configs. You can visit the [example repo]() for more complex rabbitmq deployments.

The setup may take some time. Even after the setup script finishes, it takes a while for pods and storage to start. You can check the output of `kubectl get pods` or `kubectl describe pod <pod_name>` to see current status, or check your AWS EKS dashboard.

Note that the public URL printed at the end will be used in `./worker/woker-deployment.yaml`.

You can visit `<public_url>:15672` to login with username/password "guest" to monitor the status of RabbitMQ once it's fully deployed.

### 3. Deploying the Worker

Our worker deployment will continously consume messages from the RabbitMQ queue. Then, it will use our TEI deployment to embed documents and insert into our vector db (cloud-hosted weaviate, in this case, to simplify ingestion).

Before running anything here, you should:

- `cd` into the `worker/` folder
- modify the env vars in `worker/worker-deployment.yaml` to point to the appropiate rabbitmq, tei, and weaviate credentials.
- modify the pipeline and vector store setup if needed in `worker.py`
- run `docker login` if not already logged in
- run `docker build -t <image name> .`
- run `docker tag logan-markewich/worker:latest <image_name>:<image_version>`
- run `docker push <image_name>:<image_version>`
- edit `worker-deployment.yaml` and adjust the line `image: lloganm/worker:1.4` under `conatiner` to point to your docker image

With these setups complete, we can simply run `sh ./setup.sh` which will create a cluster, deploy our container, and setup a load balancer.

`kubectl get pods` will display when your pods are ready.

### 4. Configuring AWS Lambda for Ingestion

Lastly, we need to configure AWS Lambda as a public endpoint to send data into our queue for processing.

While this can be done using the CLI, I preferred using the AWS UI for this.

First, update `ingestion_lambda/lambda_function.py` to point to the proper URL for your rabbit-mq deployment (from step 2 -- I hope you wrote that down!)

Then:

```bash
cd ingestion_lambda
sh setup.sh
```

This creates a zip file with our lambda function, as well as all the dependencies needed to run the lambda function (namely just the `pika` package).

With our zip package, we can create our lambda function:

- Open the Lambda console
- click `create function`
- Use a python3.11 runtime, give the function a name
- click `create function` at the bottom
- In the lambda editor, click the `upload from` button and select `.zip file` -- upload the zip file we created earlier.
- Click deploy!
- Your public `Function URL` will show up in the top panel, or under `Configuration`


## Ingesting your Data

Once everything is deployed, you have a fully working ETL pipeline with LlamaIndex. 

You can run ingestion by sending a POST request to your `Function URL` for your lambda function

```python
import requests
from llama_index import Document, SimpleDirectoryReader

documents = SimpleDirectoryReader("./data").load_data()

# this will also be the namespace for the vector store -- for weaviate, it needs to start with a captial and only alpha-numeric
user = "Loganm" 

body = {
  'user': user,
  'documents': [doc.json() for doc in documents]
}

# use the URL of our lambda function here
response = requests.post("https://vguwrj5wc4wsd5lhgbgn37itay0lmkls.lambda-url.us-east-1.on.aws/", json=body)
print(response.text)
```

## Using your Data

Once you've ingested data, querying with llama-index is a breeze. Our pipeline has automatically put the data into weaviate by default.

```python
from llama_index import VectorStoreIndex
from llama_index.vector_stores import WeaviateVectorStore
import weaviate

auth_config = weaviate.AuthApiKey(api_key="...")
client = weaviate.Client(url="...", auth_client_secret=auth_config)
vector_store = WeaviateVectorStore(weaviate_client=client, class_prefix="Loganm")

index = VectorStoreIndex.from_vector_store(vector_store)
```
