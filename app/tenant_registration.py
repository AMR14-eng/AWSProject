# tenant_registration.py - VERSIÓN CORREGIDA
import boto3
import os
import secrets
import string
from datetime import datetime
import psycopg2
from dotenv import load_dotenv
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
    """
    
    # Generate tenant_id from company name
    company_name = tenant_data['company_name']
    tenant_id = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')[:20]
    
    # Add timestamp to make it unique
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    tenant_id = f"{tenant_id}_{timestamp}"
    
    # Generate credentials
    temp_password = generate_temp_password()
    admin_email = tenant_data['email']
    
    try:
        # 1. Connect to database
        db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        # Try using DATABASE_URL if individual variables not set
        if not all(db_config.values()):
            DATABASE_URL = os.getenv("DATABASE_URL")
            if DATABASE_URL:
                conn = psycopg2.connect(DATABASE_URL)
            else:
                raise Exception("No database configuration found")
        else:
            conn = psycopg2.connect(**db_config)
            
        cur = conn.cursor()
        
        # 2. Create tenant record
        cur.execute("""
            INSERT INTO tenants (tenant_id, company_name, subscription_tier, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            tenant_id,
            company_name,
            tenant_data.get('subscription_tier', 'professional'),
            datetime.utcnow()
        ))
        
        tenant_db_id = cur.fetchone()[0]
        
        # 3. Create schema for tenant (optional)
        try:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {tenant_id}")
            logger.info(f"✅ Schema created for tenant: {tenant_id}")
        except Exception as e:
            logger.warning(f"Could not create schema: {e}")
        
        conn.commit()
        logger.info(f"✅ Created tenant {tenant_id} in database")
        
        # 4. Create Cognito user - ¡VERSIÓN CORREGIDA SIN custom:is_admin!
        cognito = boto3.client('cognito-idp', region_name=os.getenv("AWS_REGION", "us-east-2"))
        user_pool_id = os.getenv("COGNITO_POOL_ID")
        
        if not user_pool_id:
            raise Exception("COGNITO_POOL_ID not found")
        
        # Solo usar atributos que SÍ existen en el schema
        response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=admin_email,
            TemporaryPassword=temp_password,
            MessageAction='SUPPRESS',
            UserAttributes=[
                {'Name': 'email', 'Value': admin_email},
                {'Name': 'email_verified', 'Value': 'True'},
                {'Name': 'custom:tenant_id', 'Value': tenant_id},  # Este sí debería existir
                {'Name': 'name', 'Value': tenant_data.get('contact_name', '')},
                # NO incluir 'custom:is_admin' si no está en el schema
            ]
        )
        
        # 5. En lugar de custom attribute, puedes usar grupos
        try:
            # Crear grupo de Admins si no existe
            try:
                cognito.create_group(
                    UserPoolId=user_pool_id,
                    GroupName='Admins',
                    Description='Administrator users'
                )
                logger.info("✅ Created 'Admins' group")
            except cognito.exceptions.GroupExistsException:
                logger.info("⚠️ 'Admins' group already exists")
            
            # Agregar usuario al grupo
            cognito.admin_add_user_to_group(
                UserPoolId=user_pool_id,
                Username=admin_email,
                GroupName='Admins'
            )
            logger.info(f"✅ Added user {admin_email} to Admins group")
        except Exception as e:
            logger.warning(f"Could not manage groups: {e}")
            # Continuar de todos modos
        
        logger.info(f"✅ Created user {admin_email} in Cognito")
        
        return {
            "success": True,
            "tenant_id": tenant_id,
            "email": admin_email,
            "temp_password": temp_password,
            "message": "Tenant and user created successfully."
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