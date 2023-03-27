# views.py
#
# Application logic for the GAS
#
##

import uuid
import time
import json
from datetime import datetime

import boto3
from botocore.client import Config
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from flask import (abort, flash, redirect, render_template, 
  request, session, url_for)

from app import app, db
from decorators import authenticated, is_premium

"""Start annotation request
Create the required AWS S3 policy document and render a form for
uploading an annotation input file using the policy document

Note: You are welcome to use this code instead of your own
but you can replace the code below with your own if you prefer.
"""
@app.route('/annotate', methods=['GET'])
@authenticated
def annotate():
  # Open a connection to the S3 service
  s3 = boto3.client('s3', 
    region_name=app.config['AWS_REGION_NAME'], 
    config=Config(signature_version='s3v4'))

  bucket_name = app.config['AWS_S3_INPUTS_BUCKET']
  user_id = session['primary_identity']

  # Generate unique ID to be used as S3 key (name)
  key_name = app.config['AWS_S3_KEY_PREFIX'] + user_id + '/' + \
    str(uuid.uuid4()) + '~${filename}'

  # Create the redirect URL
  redirect_url = str(request.url) + "/job"

  # Define policy conditions
  encryption = app.config['AWS_S3_ENCRYPTION']
  acl = app.config['AWS_S3_ACL']
  fields = {
    "success_action_redirect": redirect_url,
    "x-amz-server-side-encryption": encryption,
    "acl": acl
  }
  conditions = [
    ["starts-with", "$success_action_redirect", redirect_url],
    {"x-amz-server-side-encryption": encryption},
    {"acl": acl}
  ]

  # Generate the presigned POST call
  try:
    presigned_post = s3.generate_presigned_post(
      Bucket=bucket_name, 
      Key=key_name,
      Fields=fields,
      Conditions=conditions,
      ExpiresIn=app.config['AWS_SIGNED_REQUEST_EXPIRATION'])
  except ClientError as e:
    app.logger.error(f'Unable to generate presigned URL for upload: {e}')
    return abort(500)

  # Render the upload form which will parse/submit the presigned POST
  return render_template('annotate.html',
    s3_post=presigned_post,
    role=session['role'])


"""Fires off an annotation job
Accepts the S3 redirect GET request, parses it to extract 
required info, saves a job item to the database, and then
publishes a notification for the annotator service.

Note: Update/replace the code below with your own from previous
homework assignments
"""
@app.route('/annotate/job', methods=['GET'])
@authenticated
def create_annotation_job_request():

  region = app.config['AWS_REGION_NAME']
  user_id = session.get('primary_identity')

  # Get bucket name, key, job ID, and name of input file from the S3 redirect URL
  bucket_name = request.args.get("bucket")
  object_name = request.args.get("key")
  job_ID = request.args.get("key").split('/')[-1].split('~')[0]
  input_file_name = request.args.get("key").split('/')[-1].split('~')[-1]
  if input_file_name == "":
    app.logger.error('User did not provide input file')
    return abort(500)

  # Reference: https://www.programiz.com/python-programming/datetime/timestamp-datetime
  now = datetime.now()
  secs_since_epoch = datetime.timestamp(now)
  secs_since_epoch = str(round(secs_since_epoch))
  # Create a job item and persist it to the annotations database
  item = { "job_id": {"S": job_ID}, 
          "user_id": {"S": user_id},
          "input_file_name": {"S": input_file_name}, 
          "s3_inputs_bucket": {"S": bucket_name},
          "s3_key_input_file": {"S": object_name},
          "submit_time": {"N": secs_since_epoch},
          "job_status": {"S": "PENDING"}
          }  
  ddb = boto3.client("dynamodb", region_name=region)
  try:
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.put_item
    resp = ddb.put_item(TableName = app.config["AWS_DYNAMODB_ANNOTATIONS_TABLE"], Item=item)
  except ClientError as e:
    app.logger.error(f'Unable to put item in annotations table: {e}')
    return abort(500)    

  sns = boto3.client('sns', region_name=region)
  message = json.dumps(item)
  try:
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sns.html#SNS.Client.publish
    response = sns.publish(TopicArn= app.config["AWS_SNS_JOB_REQUEST_TOPIC"], Message=message)
  except ClientError:
    app.logger.error(f'Unable to publish message to SNS topic: {e}')
    return abort(500) 

  return render_template('annotate_confirm.html', job_id=job_ID)


"""List all annotations for the user
"""
@app.route('/annotations', methods=['GET'])
@authenticated
def annotations_list():
  # Get list of annotations to display
  resource = boto3.resource('dynamodb', region_name=app.config['AWS_REGION_NAME'])
  username = session['primary_identity']
  try:
    tchon_annotations = resource.Table(app.config["AWS_DYNAMODB_ANNOTATIONS_TABLE"])
  except ClientError as e:
    app.logger.error(f'Table does not exist: {e}')
    return abort(404)

  try:
    # Reference: https://stackoverflow.com/questions/35758924/how-do-we-query-on-a-secondary-index-of-dynamodb-using-boto3
    response = tchon_annotations.query(KeyConditionExpression=Key('user_id').eq(username),IndexName='user_id_index')
  except ClientError as e:
    app.logger.error(f'Query failed: {e}')
    return abort(500)

  query_results = response["Items"]
  for result in query_results:
      # Reference: https://stackoverflow.com/questions/12400256/converting-epoch-time-into-the-datetime
      result["submit_time"] = datetime.fromtimestamp(result["submit_time"]).strftime('%Y-%m-%d %H:%M')
      result["url"] = request.url + '/' + result["job_id"]  

  return render_template('annotations.html', annotations=query_results)


"""Display details of a specific annotation job
"""
@app.route('/annotations/<id>', methods=['GET'])
@authenticated
def annotation_details(id):
    resource = boto3.resource('dynamodb', region_name=app.config['AWS_REGION_NAME'])
    username = session['primary_identity']
    try:
      tchon_annotations = resource.Table(app.config["AWS_DYNAMODB_ANNOTATIONS_TABLE"])
    except ClientError as e:
      app.logger.error(f'Table does not exist: {e}')
      return abort(500)
    
    try:
      # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Table.get_item
      response = tchon_annotations.get_item(Key={'job_id':str(id)})
    except ClientError as e:
      app.logger.error(f'Failed to get item: {e}')
      return abort(500)

    result = response["Item"]
  
    s3 = boto3.client('s3', region_name = app.config['AWS_REGION_NAME'], config=Config(signature_version='s3v4'))

    if result['user_id'] == username:
        inputs_bucket = result['s3_inputs_bucket']
        input_file = result['s3_key_input_file']

        try:
          # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.generate_presigned_url
          input_file_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': inputs_bucket, 'Key': input_file},
            ExpiresIn=3600
            )
        except ClientError as e:
          app.logger.error(f'Failed to generate presigned url: {e}')
          return abort(500)

        job_info = {}
        if result['job_status'] == 'COMPLETED':
            results_bucket = result['s3_results_bucket']
            results_file = result['s3_key_result_file']
            log_file = result['s3_key_log_file']

            try:
              # Reference: https://stackoverflow.com/questions/60163289/how-do-i-create-a-presigned-url-to-download-a-file-from-an-s3-bucket-using-boto3
              results_file_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': results_bucket, 'Key': results_file},
                ExpiresIn=3600
                )
            except ClientError as e:
              app.logger.error(f'Failed to generate presigned url: {e}')
              return abort(500)  
                        
            log_file_url = request.url + '/log'

            job_info['Log File URL'] = log_file_url
            job_info['Complete Time'] = datetime.fromtimestamp(result['complete_time']).strftime('%Y-%m-%d @ %H:%M:%S')
            now = round(datetime.timestamp(datetime.now()))
            if now < int(result['complete_time']) + 300:
              job_info['Access'] = 'let download'
            if now >= int(result['complete_time']) + 300:
              if session["role"] == "premium_user":
                archive_key = 'results_file_archive_id'
                if archive_key in result:
                  if result["results_file_archive_id"] != '':
                    job_info['Access'] = 'THAWING'
                  else:
                    job_info['Access'] = 'let download'
                else:
                  job_info['Access'] = 'let download'
              elif session["role"] == "free_user":
                job_info['Access'] = 'restrict access'
            job_info['Results File URL'] = results_file_url
            job_info['Make Me Premium Link'] = url_for('subscribe')

        job_info['Input File URL'] = input_file_url    
        job_info['Request ID'] = result['job_id']
        job_info['Request Time'] = datetime.fromtimestamp(result['submit_time']).strftime('%Y-%m-%d @ %H:%M:%S')
        job_info['Status'] = result['job_status']
        job_info['VCF Input File'] = result['input_file_name']

    else:
      app.logger.error('Requested job does not belong to authenticated user')
      return abort(403)
  

    return render_template('annotation.html', data=job_info)


"""Display the log file contents for an annotation job
"""
@app.route('/annotations/<id>/log', methods=['GET'])
@authenticated
def annotation_log(id):
    username = session['primary_identity']
    resource = boto3.resource('dynamodb', region_name=app.config['AWS_REGION_NAME'])
    try:
      tchon_annotations = resource.Table(app.config["AWS_DYNAMODB_ANNOTATIONS_TABLE"])
    except ClientError as e:
      app.logger.error(f'Table does not exist: {e}')
      return abort(500)   

    try:
      response = tchon_annotations.get_item(Key={'job_id':str(id)})
    except ClientError as e:
      app.logger.error(f'Failed to get item: {e}') 
      return abort(500) 

    result = response["Item"]
    if result['user_id'] == username:
      results_bucket = result['s3_results_bucket']
      log_file = result['s3_key_log_file']
   
      s3 = boto3.resource('s3', region_name = app.config['AWS_REGION_NAME']) 

      try:
        # Reference: https://stackoverflow.com/questions/31976273/open-s3-object-as-a-string-with-boto3
        obj = s3.Object(results_bucket, log_file)
        contents = obj.get()['Body'].read().decode('utf-8')
      except ClientError as e:
        app.logger.error(f'Failed to read log file: {e}')
        return abort(500)
    else:
      app.logger.error('Requested job does not belong to authenticated user')
      return abort(403)

    return render_template('view_log.html', job_id=id, contents=contents)


"""Subscription management handler
"""
import stripe
from auth import update_profile

@app.route('/subscribe', methods=['GET'])
@authenticated
def subscribe():
  # Update user role in accounts database
  update_profile(
    identity_id=session['primary_identity'],
    role="premium_user"
  )
  # Update role in the session
  session['role'] = 'premium_user'

  # Request restoration of the user's data from Glacier
  resource = boto3.resource('dynamodb', region_name=app.config['AWS_REGION_NAME'])
  try:
    tchon_annotations = resource.Table(app.config["AWS_DYNAMODB_ANNOTATIONS_TABLE"])
  except ClientError as e:
    app.logger.error(f'Table does not exist: {e}')
    return abort(500)

  try:
    response = tchon_annotations.query(
      KeyConditionExpression=Key('user_id').eq(session["primary_identity"]),
      IndexName='user_id_index',
      FilterExpression=Attr('results_file_archive_id').exists()
      )
  except ClientError as e:
    app.logger.error(f"{e}")
    return abort(500)

  items = response["Items"]
  annotation_jobs = []
  for item in items:
    if item["results_file_archive_id"] != '':
      annotation_job = {}
      annotation_job["job_id"] = item["job_id"]
      annotation_job["archive_id"] = item["results_file_archive_id"]
      annotation_jobs.append(annotation_job)

  sns = boto3.client('sns', region_name=app.config['AWS_REGION_NAME'])
  for annotation_job in annotation_jobs:
    message = json.dumps(annotation_job)
    try:
      response = sns.publish(TopicArn= app.config["AWS_SNS_THAW_TOPIC"], Message=message)
    except ClientError:
      app.logger.error(f'Unable to publish message to SNS topic: {e}')
      return abort(500)  
      
  # Display confirmation page
  return render_template('subscribe_confirm.html', stripe_id="forced_upgrade")


"""Set premium_user role
"""
@app.route('/make-me-premium', methods=['GET'])
@authenticated
def make_me_premium():
  # Hacky way to set the user's role to a premium user; simplifies testing
  update_profile(
    identity_id=session['primary_identity'],
    role="premium_user"
  )
  return redirect(url_for('profile'))


"""Reset subscription
"""
@app.route('/unsubscribe', methods=['GET'])
@authenticated
def unsubscribe():
  # Hacky way to reset the user's role to a free user; simplifies testing
  update_profile(
    identity_id=session['primary_identity'],
    role="free_user"
  )
  return redirect(url_for('profile'))


"""DO NOT CHANGE CODE BELOW THIS LINE
*******************************************************************************
"""

"""Home page
"""
@app.route('/', methods=['GET'])
def home():
  return render_template('home.html')

"""Login page; send user to Globus Auth
"""
@app.route('/login', methods=['GET'])
def login():
  app.logger.info(f"Login attempted from IP {request.remote_addr}")
  # If user requested a specific page, save it session for redirect after auth
  if (request.args.get('next')):
    session['next'] = request.args.get('next')
  return redirect(url_for('authcallback'))

"""404 error handler
"""
@app.errorhandler(404)
def page_not_found(e):
  return render_template('error.html', 
    title='Page not found', alert_level='warning',
    message="The page you tried to reach does not exist. \
      Please check the URL and try again."
    ), 404

"""403 error handler
"""
@app.errorhandler(403)
def forbidden(e):
  return render_template('error.html',
    title='Not authorized', alert_level='danger',
    message="You are not authorized to access this page. \
      If you think you deserve to be granted access, please contact the \
      supreme leader of the mutating genome revolutionary party."
    ), 403

"""405 error handler
"""
@app.errorhandler(405)
def not_allowed(e):
  return render_template('error.html',
    title='Not allowed', alert_level='warning',
    message="You attempted an operation that's not allowed; \
      get your act together, hacker!"
    ), 405

"""500 error handler
"""
@app.errorhandler(500)
def internal_error(error):
  return render_template('error.html',
    title='Server error', alert_level='danger',
    message="The server encountered an error and could \
      not process your request."
    ), 500

### EOF