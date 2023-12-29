#!/bin/sh

eksctl create cluster --name embeddings --node-type=g5.xlarge --nodes 1

sleep 5

kubectl create -f ./tei-deployment.yaml

sleep 5

kubectl create -f ./tei-service.yaml

echo "Embeddings URL is: $(kubectl get svc tei-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"