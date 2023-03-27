# archive_app_config.py
#
#
# Set app configuration options for archive utility
#
##

class Config(object):

  CSRF_ENABLED = True

  AWS_REGION_NAME = "us-east-1"

  # AWS DynamoDB table
  AWS_DYNAMODB_ANNOTATIONS_TABLE = "tchon_annotations"

  # AWS SQS queue
  AWS_SQS_ARCHIVE_QUEUE_NAME = "tchon_a17_archive"
  AWS_SQS_MAX_MESSAGES = 10

  # AWS Glacier
  AWS_GLACIER_VAULT_NAME = "ucmpcs"

### EOF