from dotenv import load_dotenv
import os

load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET", "tenant-lab-bucket")

DATABASE_URL = os.getenv("DATABASE_URL")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
AWS_REGION = "us-east-2"
