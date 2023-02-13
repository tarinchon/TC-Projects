# run.py
#
# Copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
#
# Wrapper script for running AnnTools
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import sys
import time
import driver
import boto3, os
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

    s3 = boto3.resource('s3', region_name = 'us-east-1')

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

      destination = 'tchon/userX/' + file_name
      my_list.append(destination)

      try:
        # Reference: https://stackoverflow.com/questions/15085864/how-to-upload-a-file-to-directory-in-s3-bucket-using-boto
        # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Bucket.upload_file
        s3.Bucket('gas-results').upload_file(file, destination)
      except ClientError as error:
        print(f"{error}... Upload of " + abbreviated_file_name + " failed.")
      except Exception as e:
        print(f"{e}... Upload of " + abbreviated_file_name + " failed.")

    files_to_upload.append(sys.argv[1])
    for file in files_to_upload:
      # Reference: https://www.geeksforgeeks.org/python-os-remove-method/
      os.remove(file)
    
    dynamodb = boto3.client('dynamodb', region_name = 'us-east-1')
    primary_key = {"job_id": {"S": sys.argv[2]}}
    # Reference: https://www.programiz.com/python-programming/datetime/timestamp-datetime
    now = datetime.now()
    time_complete = datetime.timestamp(now)
    # convert float to int and then to str
    time_complete = str(round(time_complete))
    try:
      # Reference: https://stackoverflow.com/questions/34447304/example-of-update-item-in-dynamodb-boto3/62030403#62030403
      dynamodb.update_item(TableName='tchon_annotations', 
        Key=primary_key, 
        UpdateExpression = 'SET #job_status = :completed, #results_bucket = :gas_results, #log_file = :log_file, #result_file = :result_file, #complete_time = :complete_time',
        ExpressionAttributeNames = {'#job_status': 'job_status', '#results_bucket': 's3_results_bucket', '#log_file': 's3_key_log_file', '#result_file': 's3_key_result_file', '#complete_time': 'complete_time'}, 
        ExpressionAttributeValues = {':completed': {'S': 'COMPLETED'}, ':gas_results': {'S': 'gas-results'}, ':log_file': {'S': my_list[0]}, ':result_file': {'S': my_list[1]}, ':complete_time': {'N': time_complete}}
        )
    except ClientError as error:
      print(f"{error}")
    except Exception as e:
      print(f"{e}")

  else:
    print("A valid .vcf file must be provided as input to this program.")

### EOF