# run.py
#
#
# Wrapper script for running AnnTools
#
##

import sys
import time
import driver
import boto3, os, json
from configparser import ConfigParser
from datetime import datetime
from botocore.exceptions import ClientError

"""A rudimentary timer for coarse-grained profiling
"""
class Timer(object):
  def __init__(self, verbose=True):
    self.verbose = verbose

  def __enter__(self):
    self.start = time.time()
    return self

  def __exit__(self, *args):
    self.end = time.time()
    self.secs = self.end - self.start
    if self.verbose:
      print(f"Approximate runtime: {self.secs:.2f} seconds")

if __name__ == '__main__':
  # Call the AnnTools pipeline
  if len(sys.argv) > 1:
    with Timer():
      driver.run(sys.argv[1], 'vcf')

    config = ConfigParser(os.environ)
    config.read('ann_config.ini')  

    s3 = boto3.resource('s3', region_name = config['aws']['AwsRegionName'])

    input_file_path = sys.argv[1].split('/')
    input_file_path.pop()

    USER_DIR = '/'.join(input_file_path) + '/'
    
    files_to_upload = []

    input_file = sys.argv[1].split('/')[-1]

    log_file = input_file + '.count.log'
    log_file = USER_DIR + log_file

    files_to_upload.append(log_file)

    parts = input_file.split('.')
    annot_file = parts[0] + '.annot.' + parts[1]
    annot_file = USER_DIR + annot_file

    files_to_upload.append(annot_file)

    my_list = []

    for file in files_to_upload:
      file_name = file.split('/')[-1]
      abbreviated_file_name = file_name.split('~')[-1]

      destination = config['s3']['KeyPrefix'] + sys.argv[2] + '/' + file_name
      my_list.append(destination)

      try:
        s3.Bucket(config['s3']['OutputsBucket']).upload_file(file, destination)
      except ClientError as error:
        print(f"{error}... Upload of " + abbreviated_file_name + " failed.")
      except Exception as e:
        print(f"{e}... Upload of " + abbreviated_file_name + " failed.")

    files_to_upload.append(sys.argv[1])
    for file in files_to_upload:
      try:
        os.remove(file)
      except Exception as e:
        print(f"{e}")

    dynamodb = boto3.client('dynamodb', region_name = config['aws']['AwsRegionName'])
    primary_key = {"job_id": {"S": sys.argv[3]}}
    now = datetime.now()
    time_complete = datetime.timestamp(now)
    time_complete = str(round(time_complete))
    try:
      dynamodb.update_item(TableName=config['dynamodb']['TableName'], 
        Key=primary_key, 
        UpdateExpression = 'SET #job_status = :completed, #results_bucket = :gas_results, #log_file = :log_file, #result_file = :result_file, #complete_time = :complete_time',
        ExpressionAttributeNames = {'#job_status': 'job_status', '#results_bucket': 's3_results_bucket', '#log_file': 's3_key_log_file', '#result_file': 's3_key_result_file', '#complete_time': 'complete_time'}, 
        ExpressionAttributeValues = {':completed': {'S': 'COMPLETED'}, ':gas_results': {'S': 'gas-results'}, ':log_file': {'S': my_list[0]}, ':result_file': {'S': my_list[1]}, ':complete_time': {'N': time_complete}}
        )
    except ClientError as error:
      print(f"{error}")
    except Exception as e:
      print(f"{e}")
    
    sfn = boto3.client('stepfunctions', region_name = config['aws']['AwsRegionName'])
    data = {
      "Message": {"job_id": str(sys.argv[3])}
    }
    
    try:
      execution_info = sfn.start_execution(stateMachineArn=config['sfn']['StateMachineArn'], input=json.dumps(data))
    except ClientError as error:
      print(f"{error}")
    except Exception as e:
      print(f"{e}")

  else:
    print("A valid .vcf file must be provided as input to this program.")

### EOF