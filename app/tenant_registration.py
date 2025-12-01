# tenant_registration.py
import boto3
import os
import secrets
import string
from datetime import datetime
import psycopg2
from dotenv import load_dotenv
from flask import current_app
import logging

logger = logging.getLogger(__name__)

load_dotenv()

def generate_temp_password(length=12):
    """Generate a secure temporary password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def create_new_tenant_with_user(tenant_data):
    """
    Create a new tenant with Cognito user and database schema
    
    Args:
        tenant_data: dict with keys:
            - company_name: Name of the company/lab
            - email: Admin email
            - contact_name: Contact person name
            - subscription_tier: basic/professional/enterprise
    """
    
    # Generate tenant_id from company name
    tenant_id = tenant_data['company_name'].lower().replace(' ', '_').replace('.', '').replace(',', '')[:20]
    
    # Add timestamp to make it unique
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    tenant_id = f"{tenant_id}_{timestamp}"
    
    # Generate credentials
    temp_password = generate_temp_password()
    admin_email = tenant_data['email']
    
    try:
        # 1. Connect to database
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        
        # 2. Create tenant record
        cur.execute("""
            INSERT INTO tenants (tenant_id, company_name, subscription_tier, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            tenant_id,
            tenant_data['company_name'],
            tenant_data.get('subscription_tier', 'professional'),
            datetime.utcnow()
        ))
        
        tenant_db_id = cur.fetchone()[0]
        
        # 3. Create schema for tenant (if using schema isolation)
        try:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {tenant_id}")
        except Exception as e:
            logger.warning(f"Could not create schema for tenant {tenant_id}: {e}")
        
        conn.commit()
        logger.info(f"✅ Created tenant {tenant_id} in database")
        
        # 4. Create Cognito user
        cognito = boto3.client('cognito-idp', region_name=os.getenv("AWS_REGION", "us-east-2"))
        user_pool_id = os.getenv("COGNITO_POOL_ID")
        
        response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=admin_email,
            TemporaryPassword=temp_password,
            MessageAction='SUPPRESS',
            UserAttributes=[
                {'Name': 'email', 'Value': admin_email},
                {'Name': 'email_verified', 'Value': 'True'},
                {'Name': 'custom:tenant_id', 'Value': tenant_id},
                {'Name': 'name', 'Value': tenant_data.get('contact_name', '')},
                {'Name': 'custom:is_admin', 'Value': 'true'}
            ]
        )
        
        # 5. Add user to admin group if exists
        try:
            cognito.admin_add_user_to_group(
                UserPoolId=user_pool_id,
                Username=admin_email,
                GroupName='Admins'
            )
        except Exception as e:
            logger.warning(f"Could not add user to admin group: {e}")
        
        logger.info(f"✅ Created user {admin_email} in Cognito")
        
        # 6. Create S3 folder structure
        s3 = boto3.client('s3')
        bucket_name = os.getenv("S3_BUCKET", "tenant-lab-bucket")
        
        # Create folder structure
        folders = [f"{tenant_id}/uploads/", f"{tenant_id}/results/", f"{tenant_id}/exports/"]
        for folder in folders:
            s3.put_object(Bucket=bucket_name, Key=folder, Body=b'')
        
        logger.info(f"✅ Created S3 folders for tenant {tenant_id}")
        
        # 7. Send welcome email (optional - implement email service)
        # send_welcome_email(admin_email, tenant_id, temp_password)
        
        return {
            "success": True,
            "tenant_id": tenant_id,
            "email": admin_email,
            "temp_password": temp_password,
            "message": "Tenant created successfully. Check your email for credentials."
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to create tenant: {e}")
        return {
            "success": False,
            "error": str(e),
            "tenant_id": tenant_id
        }
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

def get_all_subscription_tiers():
    """Get available subscription tiers"""
    return [
        {"id": "basic", "name": "Basic", "price": 99.0, "features": ["1000 results/month", "10GB storage", "Basic support"]},
        {"id": "professional", "name": "Professional", "price": 299.0, "features": ["5000 results/month", "50GB storage", "Priority support", "API access"]},
        {"id": "enterprise", "name": "Enterprise", "price": 599.0, "features": ["Unlimited results", "200GB storage", "24/7 support", "Custom integrations"]}
    ]