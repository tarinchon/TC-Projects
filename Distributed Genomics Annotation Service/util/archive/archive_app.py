# archive_app.py
#
# Archive free user data
#
##

import requests
from flask import Flask, jsonify, request
import boto3, json
from uuid import uuid4
from datetime import datetime
from botocore.client import Config
import subprocess, os, shutil, sys
sys.path.insert(1, os.path.realpath(os.path.pardir))
from botocore.exceptions import ClientError
import helpers

app = Flask(__name__)
environment = 'archive_app_config.Config'
app.config.from_object(environment)

@app.route('/', methods=['GET'])
def home():
  return (f"This is the Archive utility: POST requests to /archive.")

@app.route('/archive', methods=['POST'])
def archive_free_user_data():
  sqs = boto3.resource("sqs", region_name=app.config['AWS_REGION_NAME'])

  try:
    queue = sqs.get_queue_by_name(QueueName=app.config['AWS_SQS_ARCHIVE_QUEUE_NAME'])
  except ClientError as error:
    app.logger.error(f"{error}")
  except Exception as e:
    app.logger.error(f"{e}")

  if request.headers['x-amz-sns-message-type'] == 'SubscriptionConfirmation':
    # Confirm SNS topic subscription confirmation
    msg_body = request.get_json(force=True)
    url = msg_body["SubscribeURL"]
    try:
      r = requests.get(url)
    except Exception as e: 
      app.logger.error(f'{e}')
  elif request.headers['x-amz-sns-message-type'] == 'Notification':
    # Process job request notification
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
        
        job_id = msg_body["job_id"]

        dynamodb = boto3.resource('dynamodb', region_name = app.config['AWS_REGION_NAME'])
        try:
          tchon_annotations = dynamodb.Table(app.config["AWS_DYNAMODB_ANNOTATIONS_TABLE"])
        except ClientError as e:
          app.logger.error(f'Table does not exist: {e}')

        try:
          response = tchon_annotations.get_item(Key={'job_id':job_id})
        except ClientError as e:
          app.logger.error(f'Failed to get item: {e}') 

        result = response["Item"] 
        user = result["user_id"]
        profile = helpers.get_user_profile(id=user)
        
        if profile["role"] != "premium_user":   
          results_bucket = result['s3_results_bucket']
          annot_file = result['s3_key_result_file']        
          s3 = boto3.resource('s3', region_name = app.config['AWS_REGION_NAME']) 
          try:
            obj = s3.Object(results_bucket, annot_file)
            contents = obj.get()['Body'].read()
          except ClientError as e:
            app.logger.error(f'Failed to read results file: {e}')

          glacier = boto3.client('glacier', region_name = app.config['AWS_REGION_NAME'])
          try:
            archive_info = glacier.upload_archive(vaultName=app.config['AWS_GLACIER_VAULT_NAME'], body=contents)
          except ClientError as e:
            app.logger.error(f'Failed to upload results file: {e}')
            raise
          else:
            print("Successfully uploaded archive...")
          
          archive_id = archive_info['archiveId']          

          try:
              tchon_annotations.update_item(
                Key = {"job_id": job_id}, 
                UpdateExpression = 'SET #results_file_archive_id = :archive_id',
                ExpressionAttributeNames = {'#results_file_archive_id': 'results_file_archive_id'},
                ExpressionAttributeValues = {':archive_id': archive_id}
                )
          except ClientError as error:
              app.logger.error(f"{error}")

          try:
            x = obj.delete()
          except ClientError as e:
            app.logger.error(f"{e}") 
              
        else:
          print("Did not upload archive because user is a premium user...")

        try:
          message.delete()
        except ClientError as e:
          app.logger.error(f"{e}")

  return jsonify({
    "code": 200, 
    "message": "Archive upload request processed."
    }), 200


app.run('0.0.0.0', debug=True)
### EOF