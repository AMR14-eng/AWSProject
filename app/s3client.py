import boto3
from app.config import S3_BUCKET

s3 = boto3.client("s3")

def upload_file(file, key):
    s3.upload_fileobj(file, S3_BUCKET, key)
    return f"s3://{S3_BUCKET}/{key}"

def upload_bytes(bucket, key, data):
    """Sube bytes directamente a S3"""
    s3.put_object(Bucket=bucket, Key=key, Body=data)
    return f"s3://{bucket}/{key}"