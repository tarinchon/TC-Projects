# thaw_app.py
#
# Thaws upgraded (premium) user data
#
##

import json, requests, boto3, os
from botocore.exceptions import ClientError
from botocore.client import Config

from flask import Flask, jsonify, request

app = Flask(__name__)
environment = 'thaw_app_config.Config'
app.config.from_object(environment)
app.url_map.strict_slashes = False

@app.route('/', methods=['GET'])
def home():
  return (f"This is the Thaw utility: POST requests to /thaw.")

@app.route('/thaw', methods=['POST'])
def thaw_premium_user_data():
  sqs = boto3.resource("sqs", region_name=app.config['AWS_REGION_NAME'])
  try:
    queue = sqs.get_queue_by_name(QueueName=app.config['AWS_SQS_THAW_QUEUE_NAME'])
  except ClientError as error:
    app.logger.error(f"{error}")
  except Exception as e:
    app.logger.error(f"{e}")

  if request.headers['x-amz-sns-message-type'] == 'SubscriptionConfirmation':
    # Confirm SNS topic subscription confirmation
    # Reference: https://docs.aws.amazon.com/sns/latest/dg/sns-message-and-json-formats.html#http-subscription-confirmation-json
    msg_body = request.get_json(force=True)
    url = msg_body["SubscribeURL"]
    try:
      r = requests.get(url)
    except Exception as e: 
      app.logger.error(f'{e}')

  elif request.headers['x-amz-sns-message-type'] == 'Notification':
    # Process job request notification
    # Reference: https://docs.aws.amazon.com/sns/latest/dg/sns-message-and-json-formats.html#http-notification-json

    try:
      messages = queue.receive_messages(MaxNumberOfMessages=app.config['AWS_SQS_MAX_MESSAGES'])
    except ClientError as error:
      app.logger.error(f"{error}")
    except Exception as e:
      app.logger.error(f"{e}")

    if len(messages) > 0:
      print(f"Received {str(len(messages))} messages...")

      for message in messages:
        # Parse JSON message
        msg_body = json.loads(message.body)
        msg_body = json.loads(msg_body['Message'])

        glacier = boto3.client('glacier', region_name=app.config['AWS_REGION_NAME'])
        try:
          print("Attempting expedited retrieval...")
          response = glacier.initiate_job(vaultName=app.config['AWS_GLACIER_VAULT'],jobParameters={
            'Tier':'Expedited',
            'Type':'archive-retrieval',
            'ArchiveId':msg_body["archive_id"],
            'SNSTopic':app.config['LAMBDA_SNS_TOPIC_ARN'],
            'Description': msg_body["job_id"]
            })
          try:
            print("Expedited retrieval initiated...")
            message.delete()
            print("Message deleted from queue...")
          except ClientError as e:
            print(f"{e}")
        except glacier.exceptions.InsufficientCapacityException as e:
          print(f"Expedited retrieval failed: {e}")
          print("Attempting standard retrieval...")
          try:
            info = glacier.initiate_job(vaultName=app.config['AWS_GLACIER_VAULT'],jobParameters={
              'Tier':'Standard',
              'Type':'archive-retrieval',
              'ArchiveId':msg_body["archive_id"],
              'SNSTopic':app.config['LAMBDA_SNS_TOPIC_ARN'],
              'Description': msg_body["job_id"]
              })
            try:
              print("Standard retrieval initiated...")
              message.delete()
              print("Message deleted from queue...")
            except ClientError as e:
              print(f"{e}")
          except ClientError as e:
            print(f"Standard retrieval failed: {e}")
        except ClientError as e:
          print(f"{e}")


  return jsonify({
    "code": 200, 
    "message": "Thaw request processed."
    }), 200


### EOF
