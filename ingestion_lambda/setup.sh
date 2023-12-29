#!/bin/sh

pip install -r requirements.txt -t .

zip -r9 ../ingestion_lambda.zip . -x "*.git*" "*setup.sh*" "*requirements.txt*" "*.zip*"
