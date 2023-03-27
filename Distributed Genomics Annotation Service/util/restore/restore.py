# restore.py
#
# Restores thawed data, saving objects to S3 results bucket
# NOTE: This code is for an AWS Lambda function
#
##

import boto3, json
from botocore.exceptions import ClientError
REGION = 'us-east-1'
RESULTS_BUCKET = 'gas-results'
DYNAMODB_TABLE = 'tchon_annotations'
VAULT = 'ucmpcs'

def lambda_handler(event, context):
    message = event['Records'][0]['Sns']['Message']
    message = json.loads(message)
    archive_retrieval_job_id = message['JobId']
    archive_id = message['ArchiveId']
    annotation_job_id = message['JobDescription']
    ddb_resource = boto3.resource('dynamodb', region_name=REGION)
    try:
        tchon_annotations = ddb_resource.Table(DYNAMODB_TABLE)
    except ClientError as e:
        print(f"{e}")
    try:
        result = tchon_annotations.get_item(Key={'job_id': annotation_job_id})
    except ClientError as e:
        print(f"{e}")
    item = result["Item"]
    obj_key = item["s3_key_result_file"]
    glacier = boto3.client('glacier', region_name = REGION)
    try:
        response = glacier.get_job_output(vaultName=VAULT,jobId=archive_retrieval_job_id)
    except ClientError as e:
        print(f"{e}")    
    obj_contents = response["body"]
    s3 = boto3.client('s3', region_name=REGION)
    try:
        s3.put_object(Body=obj_contents.read(),Bucket=RESULTS_BUCKET,Key=obj_key)
    except ClientError as e:
        print(f"{e}")
    try:
        glacier.delete_archive(vaultName=VAULT, archiveId=archive_id)
    except ClientError as e:
        print(f"{e}")
    no_archive_id = ''    
    try:
        x = tchon_annotations.update_item(
            Key = {"job_id": annotation_job_id}, 
            UpdateExpression = 'SET #results_file_archive_id = :no_archive_id',
            ExpressionAttributeNames = {'#results_file_archive_id': 'results_file_archive_id'},
            ExpressionAttributeValues = {':no_archive_id': no_archive_id}
            )
    except ClientError as e:
        print(f"{e}")




### EOF