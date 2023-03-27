# thaw_app_config.py
#
# Copyright (C) 2011-2021 Vas Vasiliadis
# University of Chicago
#
# Set app configuration options for thaw utility
#
##

class Config(object):

  CSRF_ENABLED = True

  AWS_REGION_NAME = "us-east-1"

  # AWS DynamoDB table
  AWS_DYNAMODB_ANNOTATIONS_TABLE = "tchon_annotations"

  # AWS SQS queues
  AWS_SQS_THAW_QUEUE_NAME = "tchon_a17_thaw"
  AWS_SQS_MAX_MESSAGES = 10

  # AWS Glacier
  AWS_GLACIER_VAULT = 'ucmpcs'

  # AWS SNS topics
  LAMBDA_SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:127134666975:tchon_a17_restore"

### EOF
