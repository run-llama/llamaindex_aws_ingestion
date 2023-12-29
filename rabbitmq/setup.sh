#!/bin/sh

# had to add these zones, else it fails to deploy
eksctl create cluster --name mqCluster --zones us-east-1a,us-east-1b,us-east-1c,us-east-1d,us-east-1f

sleep 5

eksctl utils associate-iam-oidc-provider --cluster=mqCluster --region us-east-1 --approve

sleep 5

eksctl create iamserviceaccount \
    --name ebs-csi-controller-sa \
    --namespace kube-system \
    --cluster mqCluster \
    --role-name AmazonEKS_EBS_CSI_DriverRole \
    --role-only \
    --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
    --approve

sleep 5

eksctl create addon --name aws-ebs-csi-driver --cluster mqCluster --service-account-role-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/AmazonEKS_EBS_CSI_DriverRole --force

sleep 5

kubectl apply -f https://github.com/rabbitmq/cluster-operator/releases/latest/download/cluster-operator.yml

sleep 5

kubectl apply -f rabbitmqcluster.yaml

sleep 5

echo "RabbitMQ URL is: $(kubectl get svc production-rabbitmqcluster -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"

echo "Note: It may take some time for pods and storage to be ready. Run 'kubectl get pods' to check status."