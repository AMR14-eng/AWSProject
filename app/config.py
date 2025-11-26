from dotenv import load_dotenv
import os

# Carga variables del .env
load_dotenv()

# ----------------------
# Variables globales
# ----------------------
S3_BUCKET = os.getenv("S3_BUCKET", "tenant-lab-bucket")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
AWS_REGION = "us-east-2"

# ----------------------
# Clase Config (para Flask)
# ----------------------
class Config:
    S3_BUCKET = S3_BUCKET
    DATABASE_URL = DATABASE_URL
    COGNITO_USER_POOL_ID = COGNITO_USER_POOL_ID
    COGNITO_CLIENT_ID = COGNITO_CLIENT_ID
    AWS_REGION = AWS_REGION
