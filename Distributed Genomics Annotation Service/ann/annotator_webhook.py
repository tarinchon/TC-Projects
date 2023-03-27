# annotator_webhook.py
#
# NOTE: This file lives on the AnnTools instance
# Modified to run as a web server that can be called by SNS to process jobs
# Run using: python annotator_webhook.py
#
##

import requests
from flask import Flask, jsonify, request
import boto3, json
from uuid import uuid4
import subprocess, os, shutil
from botocore.exceptions import ClientError

app = Flask(__name__)
environment = 'ann_config.Config'
app.config.from_object(environment)

sqs = boto3.resource("sqs", region_name=app.config['AWS_REGION_NAME'])

try:
  queue = sqs.get_queue_by_name(QueueName=app.config['AWS_SQS_REQUESTS_QUEUE_NAME'])
except ClientError as error:
    print(f"{error}")
except Exception as e:
    print(f"{e}")

'''
A13 - Replace polling with webhook in annotator

Receives request from SNS; queries job queue and processes message.
Reads request messages from SQS and runs AnnTools as a subprocess.
Updates the annotations database with the status of the request.
'''
@app.route('/process-job-request', methods=['GET', 'POST'])
def annotate():

  if (request.method == 'GET'):
    return jsonify({
      "code": 405, 
      "error": "Expecting SNS POST request."
    }), 405
  if (request.method == 'POST'):
    # Check message type
    # Reference: https://docs.aws.amazon.com/sns/latest/dg/SendMessageToHttp.prepare.html
    if request.headers['x-amz-sns-message-type'] == 'SubscriptionConfirmation':
        # Confirm SNS topic subscription confirmation
        msg_body = request.get_json(force=True)
        url = msg_body["SubscribeURL"]
        try:
            r = requests.get(url)
        except Exception as e: 
            print(f'{e}')
    elif request.headers['x-amz-sns-message-type'] == 'Notification':
        # Process job request notification
        try:
          messages = queue.receive_messages(MaxNumberOfMessages=app.config['AWS_SQS_MAX_MESSAGES'])
        except ClientError as error:
          print(f"{error}")
        except Exception as e:
          print(f"{e}")

        if len(messages) > 0:
            print(f"Received {str(len(messages))} messages...")

            for message in messages:
                # Parse JSON message
                msg_body = json.loads(message.body)
                msg_body = json.loads(msg_body['Message'])
                
                input_file_name = msg_body['input_file_name']['S']
                bucket_name = msg_body["s3_inputs_bucket"]['S']
                object_name = msg_body["s3_key_input_file"]['S']
                input_file = object_name.split('/')[-1]
                job_id = msg_body["job_id"]['S']
                username = msg_body["user_id"]['S']

                BASE_DIR = os.path.abspath(os.path.dirname(__file__)) + "/"
                USER_DIR = BASE_DIR + username
                if not os.path.exists(USER_DIR):
                    os.mkdir(USER_DIR)

                input_file_path = os.path.join(USER_DIR,input_file)

                s3 = boto3.client('s3', region_name = app.config['AWS_REGION_NAME'])
                try:
                    # Download file to the correct file location
                    s3.download_file(bucket_name, object_name, input_file_path)
                except ClientError as error:
                    print(f"{error}")
                except Exception as e:
                    print(f"{e}")

                # Change directories and spawn subprocess
                try:
                    ann_process = subprocess.Popen(["python", "run.py", input_file_path, username, job_id], cwd=BASE_DIR)
                except Exception as e:
                    print(f"{e}")

                dynamodb = boto3.client('dynamodb', region_name = app.config['AWS_REGION_NAME'])
                primary_key = {"job_id": {"S": job_id}}
                try:
                    dynamodb.update_item(
                                        TableName=app.config['AWS_DYNAMODB_ANNOTATIONS_TABLE'], 
                                        Key=primary_key, UpdateExpression = 'SET #job_status = :running', 
                                        ConditionExpression = '#job_status = :pending', 
                                        ExpressionAttributeNames = {'#job_status': 'job_status'}, 
                                        ExpressionAttributeValues = {':pending': {'S': 'PENDING'}, ':running': {'S': 'RUNNING'}}
                                        )
                except ClientError as error:
                    print(f"{error}")
                except Exception as e:
                    print(f"{e}")
                
                try:
                    message.delete()
                except ClientError as e:
                    print(f"{e}")
  return jsonify({
    "code": 200, 
    "message": "Annotation job request processed."
  }), 200

app.run('0.0.0.0', debug=True)

### EOF