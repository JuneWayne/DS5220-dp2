#!/bin/bash
# Run this on your EC2 instance BEFORE deploying the CronJob

aws dynamodb create-table \
  --table-name cville-weather \
  --attribute-definitions \
    AttributeName=location,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=location,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
