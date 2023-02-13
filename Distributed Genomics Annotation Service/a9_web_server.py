import boto3, json
from flask import Flask, request, render_template, jsonify
from uuid import uuid4
from datetime import datetime, date
from botocore.config import Config
from botocore.exceptions import ClientError

app = Flask(__name__)

@app.route('/annotate', methods=['GET'])
def return_signed_form():
    """
    Server sends back pre-signed web form user can use to upload objects for a preset amount of time
    :return render_template('annotate.html', data=object): web form user uses to upload objects to gas-inputs bucket
    """
    # set signature version to v4 
    # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
    my_config = Config(region_name = 'us-east-1', signature_version='s3v4')
    s3_client=boto3.client("s3",config=my_config) 

    # create value for x-amz-date and store value in variable, iso_date
    # Reference for iso formatting: https://www.tutorialspoint.com/How-do-I-get-an-ISO-8601-date-in-string-format-in-Python
    current_date = datetime.now()
    iso_date = current_date.strftime('%Y%m%dT%H%M%SZ')

    # create value for x-amz-credential and store value in variable, credential
    # Reference for date formatting: https://www.geeksforgeeks.org/get-current-date-using-python/
    today = str(date.today()).replace('-','')
    credential = 'AKIAR3GORCDPVAULZ6NJ/' + today + '/us-east-1/s3/aws4_request'

    # hardcode bucket name
    bucket_name = 'gas-inputs'

    # create object key for file user will upload
    unique_id = str(uuid4())
    key_name = 'tchon/userX/' + unique_id + '~${filename}'

    # create redirect url
    redirect_url = request.url + '/job'

    # create fields dictionary we will pass into generate_presigned_post method
    # Reference: https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-HTTPPOSTForms.html
    fields = {'acl': 'private', 'success_action_redirect': redirect_url, 'x-amz-algorithm': 'AWS4-HMAC-SHA256', 'x-amz-credential': credential, 'x-amz-date': iso_date}
    
    # create conditions list we will pass into generate_presigned_post method
    conditions = [{'acl': 'private'}, {"success_action_redirect": redirect_url}]

    try:
        object = s3_client.generate_presigned_post(Bucket=bucket_name, Key=key_name, Conditions=conditions, Fields=fields, ExpiresIn=3600)
    except ClientError as error:
        return jsonify({"code": error.response['Error']['Code'], "status": "error", "message": f"{error}"})
    except Exception as e:
        return jsonify({"code": 500, "status": "error", "message": f"{e}"})         

    return render_template('annotate.html', data=object)

@app.route("/annotate/job", methods=['GET'])
def annotate_job():
    # Get bucket name, key, job ID, and name of input file from the S3 redirect URL
    bucket_name = request.args.get("bucket")
    object_name = request.args.get("key")
    job_ID = request.args.get("key").split('/')[-1].split('~')[0]
    input_file_name = request.args.get("key").split('/')[-1].split('~')[-1]

    # Reference: https://www.programiz.com/python-programming/datetime/timestamp-datetime
    now = datetime.now()
    secs_since_epoch = datetime.timestamp(now)
    # convert float to int and then to str
    secs_since_epoch = str(round(secs_since_epoch))
    # Create a job item and persist it to the annotations database
    item = { "job_id": {"S": job_ID}, 
            "user_id": {"S": "userX"},
            "input_file_name": {"S": input_file_name}, 
            "s3_inputs_bucket": {"S": bucket_name},
            "s3_key_input_file": {"S": object_name},
            "submit_time": {"N": secs_since_epoch},
            "job_status": {"S": "PENDING"}
            }  
    ddb = boto3.client("dynamodb", region_name='us-east-1')
    try:
        # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.put_item
        resp = ddb.put_item(TableName = 'tchon_annotations', Item=item)
    except ClientError as error:
        return jsonify({"code": error.response['Error']['Code'], "status": "error", "message": f"{error}"})
    except Exception as e:
        return jsonify({"code": 500, "status": "error", "message": f"{e}"})    

    sns = boto3.client('sns', region_name='us-east-1')
    message = json.dumps(item)
    try:
        # Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sns.html#SNS.Client.publish
        response = sns.publish(TopicArn= 'arn:aws:sns:us-east-1:127134666975:tchon_job_requests', Message=message)
    except ClientError as error:
        return jsonify({"code": error.response['Error']['Code'], "status": "error", "message": f"{error}"})
    except Exception as e:
        return jsonify({"code": 500, "status": "error", "message": f"{e}"})     

    return jsonify({'code': 201, 'data': {'job_id': job_ID, 'input_file': input_file_name}})



app.run(host='0.0.0.0', debug=True)