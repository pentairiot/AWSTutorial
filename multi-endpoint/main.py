import boto3
from botocore.exceptions import ClientError
import os
from io import BytesIO
import json

if 'S3_BUCKET' not in os.environ:
    # The Service S3 Bucket is defined in the serverless config and its name will be set as an environment variable
    raise Exception('S3_BUCKET environment variable not set')


def get_s3_file_contents(key):
    """
    Download the given file from the service S3 Bucket and return its contents.
    See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#bucket
    :param key:
    :return:
    """
    obj = BytesIO()
    bucket = os.environ['S3_BUCKET']
    print('Downloading file s3://%s/%s' % (bucket, key))
    boto3.resource('s3').Bucket(bucket).Object(key).download_fileobj(obj)
    obj.seek(0)     # move the cursor to the beginning of the file object
    return obj.read().decode('utf-8')   # return as a string


def put_s3_file_contents(key, contents):
    """
    Save the given contents to a file in the service S3 Bucket.
    See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#bucket
    :param key:
    :param contents:
    :return:
    """
    obj = BytesIO()
    obj.write(contents)
    obj.seek(0)
    bucket = os.environ['S3_BUCKET']
    print('Saving file s3://%s/%s' % (bucket, key))
    boto3.resource('s3').Bucket(bucket).Object(key).upload_fileobj(obj)


def handle_get(event):
    """
    Check the path for a file and try to get it from S3. If the file does not exist, return a 404.
    :param event:
    :return:
    """
    key = event['pathParameters']['key']
    try:
        return {'statusCode': 200, 'body': get_s3_file_contents(key)}
    except ClientError as e:
        if '404' in str(e):
            return {'statusCode': 404, 'body': 'File with name %s not found' % key}
        else:
            return {'statusCode': 500, 'body': 'Something went wrong:\n\t%s' % str(e)}
    except Exception as e2:
        return {'statusCode': 500, 'body': 'Something went wrong:\n\t%s' % str(e2)}


def handle_post(event):
    """
    Check the path for the file and save the request body to that file. If the file already exists overwrite it.
    :param event:
    :return:
    """
    key = event['pathParameters']['key']
    # contents needs to be in bytes, not str
    contents = event['body'].encode('utf-8') if not isinstance(event['body'], bytes) else event['body']
    try:
        return {'statusCode': 200, 'body': put_s3_file_contents(key, contents)}
    except Exception as e:
        return {'statusCode': 500, 'body': 'Something went wrong:\n\t%s' % str(e)}


def handle_request(event, context):
    """
    Events will come in with the format:
        ```
        {
            "resource": "Resource path",
            "path": "Path parameter",
            "httpMethod": "Incoming request's method name"
            "headers": {String containing incoming request headers}
            "multiValueHeaders": {List of strings containing incoming request headers}
            "queryStringParameters": {query string parameters }
            "multiValueQueryStringParameters": {List of query string parameters}
            "pathParameters":  {path parameters}
            "stageVariables": {Applicable stage variables}
            "requestContext": {Request context, including authorizer-returned key-value pairs}
            "body": "A JSON string of the request payload."
            "isBase64Encoded": "A boolean flag to indicate if the applicable request payload is Base64-encode"
        }
        ```
    Depending on the `httpMethod` they will be passed to either `handle_get`, `handle_post`,
    or return 415 - method not allowed
    :return:
    """
    print('Received Event: %s' % json.dumps(event))
    if event['httpMethod'].lower() == 'get':
        return handle_get(event)
    elif event['httpMethod'].lower() == 'post':
        return handle_post(event)
    else:
        return {'statusCode': 415, 'body': 'method not allowed'}
