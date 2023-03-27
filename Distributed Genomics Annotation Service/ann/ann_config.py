# ann_config.py
#
#
# Set GAS annotator configuration options
#
##

class Config(object):

  CSRF_ENABLED = True

  ANNOTATOR_BASE_DIR = "/home/ubuntu/gas/ann/"

  AWS_REGION_NAME = "us-east-1"

  # AWS S3 upload parameters
  AWS_S3_INPUTS_BUCKET = "gas-inputs"
  AWS_S3_RESULTS_BUCKET = "gas-results"

  # AWS SQS queues
  AWS_SQS_WAIT_TIME = 20
  AWS_SQS_MAX_MESSAGES = 10
  AWS_SQS_REQUESTS_QUEUE_NAME = "tchon_a17_job_requests"

  # AWS DynamoDB
  AWS_DYNAMODB_ANNOTATIONS_TABLE = "tchon_annotations"

### EOF