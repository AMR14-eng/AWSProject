# tenant_registration.py - VERSIÓN QUE SÍ FUNCIONA
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
    Create a new tenant with Cognito user - VERSIÓN CORREGIDA
    """
    
    # Generate tenant_id
    company_name = tenant_data['company_name']
    tenant_id = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')[:20]
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    tenant_id = f"{tenant_id}_{timestamp}"
    
    # Generate credentials
    temp_password = generate_temp_password()
    admin_email = tenant_data['email']
    
    try:
        # ===== 1. PRIMERO crear en Cognito (más importante) =====
        cognito = boto3.client('cognito-idp', region_name=os.getenv("AWS_REGION", "us-east-2"))
        user_pool_id = os.getenv("COGNITO_POOL_ID", "us-east-2_Wi7VHkSWm")
        
        # Verificar qué atributos personalizados existen
        print(f"🔍 Creando usuario en Cognito: {admin_email}")
        print(f"🔍 User Pool ID: {user_pool_id}")
        
        # Lista SEGURA de atributos (solo los que sabemos que existen)
        user_attributes = [
            {'Name': 'email', 'Value': admin_email},
            {'Name': 'email_verified', 'Value': 'True'},
            {'Name': 'name', 'Value': tenant_data.get('contact_name', '')}
        ]
        
        # Solo agregar custom:tenant_id si estamos seguros que existe
        # Si falla, lo intentamos sin él
        try:
            # Intentar con custom:tenant_id
            response = cognito.admin_create_user(
                UserPoolId=user_pool_id,
                Username=admin_email,
                TemporaryPassword=temp_password,
                MessageAction='SUPPRESS',
                UserAttributes=user_attributes + [
                    {'Name': 'custom:tenant_id', 'Value': tenant_id}
                ]
            )
            print("✅ Usuario creado CON custom:tenant_id")
            
        except Exception as e:
            if "custom:tenant_id" in str(e):
                print("⚠️ custom:tenant_id no existe, creando sin él")
                # Crear sin custom:tenant_id
                response = cognito.admin_create_user(
                    UserPoolId=user_pool_id,
                    Username=admin_email,
                    TemporaryPassword=temp_password,
                    MessageAction='SUPPRESS',
                    UserAttributes=user_attributes
                )
            else:
                raise e
        
        # ===== 2. LUEGO intentar crear en PostgreSQL (si hay configuración) =====
        try:
            db_config = {
                'host': os.getenv('DB_HOST'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD')
            }
            
            if all(db_config.values()):  # Si todas las vars están configuradas
                conn = psycopg2.connect(**db_config)
                cur = conn.cursor()
                
                # Crear tenant en DB
                cur.execute("""
                    INSERT INTO tenants (tenant_id, company_name, subscription_tier, created_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (tenant_id) DO NOTHING
                    RETURNING id
                """, (
                    tenant_id,
                    company_name,
                    tenant_data.get('subscription_tier', 'professional'),
                    datetime.utcnow()
                ))
                
                conn.commit()
                print(f"✅ Tenant creado en PostgreSQL: {tenant_id}")
                
                # Crear schema si es necesario
                try:
                    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {tenant_id}")
                    conn.commit()
                    print(f"✅ Schema creado: {tenant_id}")
                except Exception as schema_error:
                    print(f"⚠️ No se pudo crear schema: {schema_error}")
                
                cur.close()
                conn.close()
            else:
                print("⚠️ Configuración de DB incompleta, saltando PostgreSQL")
                
        except Exception as db_error:
            print(f"⚠️ Error con PostgreSQL (continuando): {db_error}")
            # Continuamos aunque falle la DB, lo importante es Cognito
        
        # ===== 3. Crear estructura en S3 (opcional) =====
        try:
            s3 = boto3.client('s3')
            bucket_name = os.getenv('S3_BUCKET', 'tenant-lab-bucket')
            
            # Crear folders
            folders = [f"{tenant_id}/uploads/", f"{tenant_id}/results/"]
            for folder in folders:
                s3.put_object(Bucket=bucket_name, Key=folder, Body=b'')
            
            print(f"✅ Folders S3 creados para: {tenant_id}")
        except Exception as s3_error:
            print(f"⚠️ Error con S3 (continuando): {s3_error}")
        
        return {
            "success": True,
            "tenant_id": tenant_id,
            "email": admin_email,
            "temp_password": temp_password,
            "message": "Usuario creado exitosamente en Cognito"
        }
        
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": str(e),
            "tenant_id": tenant_id
        }

def get_all_subscription_tiers():
    """Get available subscription tiers"""
    return [
        {"id": "basic", "name": "Basic", "price": 99.0, "features": ["1000 results/month", "10GB storage", "Basic support"]},
        {"id": "professional", "name": "Professional", "price": 299.0, "features": ["5000 results/month", "50GB storage", "Priority support", "API access"]},
        {"id": "enterprise", "name": "Enterprise", "price": 599.0, "features": ["Unlimited results", "200GB storage", "24/7 support", "Custom integrations"]}
    ]