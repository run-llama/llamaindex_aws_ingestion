#!/bin/sh

eksctl create cluster --name mq-workers --zones us-east-1a,us-east-1b,us-east-1c,us-east-1d,us-east-1f

sleep 5

kubectl create -f ./worker-deployment.yaml

sleep 5

kubectl create -f ./worker-service.yaml