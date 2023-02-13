import boto3, json
from uuid import uuid4
import subprocess, os, shutil
from botocore.exceptions import ClientError

def start_annotation_job():
    sqs = boto3.resource('sqs', region_name = 'us-east-1')
    try:
        # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.ServiceResource.get_queue_by_name
        queue = sqs.get_queue_by_name(QueueName='tchon_job_requests')
    except ClientError as error:
        print(f"{error}")
    except Exception as e:
        print(f"{e}")

    while True:
        print("Asking SQS for up to 10 messages.")
        try:
            # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Queue.receive_messages
            messages = queue.receive_messages(WaitTimeSeconds= 20, MaxNumberOfMessages= 10)
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

                # Reference for os.path.abspath: Professor Vasiliadis
                BASE_DIR = os.path.abspath(os.path.dirname(__file__)) + "/"
                USER_DIR = BASE_DIR + username
                if not os.path.exists(USER_DIR):
                    os.mkdir(USER_DIR)

                input_file_path = os.path.join(USER_DIR,input_file)

                s3 = boto3.client('s3', region_name = 'us-east-1')
                try:
                    # Download file to the correct file location
                    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-example-download-file.html
                    s3.download_file(bucket_name, object_name, input_file_path)
                except ClientError as error:
                    print(f"{error}")
                except Exception as e:
                    print(f"{e}")

                # Change directories and spawn subprocess
                # Reference for using cwd parameter: Professor Vasiliadis
                try:
                    ann_process = subprocess.Popen(["python", "a9_run.py", input_file_path, job_id], cwd=BASE_DIR)
                except Exception as e:
                    print(f"{e}")

                dynamodb = boto3.client('dynamodb', region_name = 'us-east-1')
                primary_key = {"job_id": {"S": job_id}}
                try:
                    # Reference from documentation: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.update_item
                    # Reference from StackOverflow: https://stackoverflow.com/questions/62036785/how-to-update-dynamodb-attribute-based-on-a-condition-on-another-attribute
                    dynamodb.update_item(TableName='tchon_annotations', Key=primary_key, UpdateExpression = 'SET #job_status = :running', ConditionExpression = '#job_status = :pending', ExpressionAttributeNames = {'#job_status': 'job_status'}, ExpressionAttributeValues = {':pending': {'S': 'PENDING'}, ':running': {'S': 'RUNNING'}})
                except ClientError as error:
                    print(f"{error}")
                except Exception as e:
                    print(f"{e}")
                
                try:
                    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Message.delete
                    message.delete()
                except ClientError as e:
                    print(f"{e}")

if __name__ == '__main__':
    start_annotation_job()