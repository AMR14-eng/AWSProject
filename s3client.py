import boto3
from config import S3_BUCKET

s3 = boto3.client("s3")

def upload_file(file, key):
    s3.upload_fileobj(file, S3_BUCKET, key)
    return f"s3://{S3_BUCKET}/{key}"
