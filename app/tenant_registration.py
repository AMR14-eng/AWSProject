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
    Create a new tenant with Cognito user - VERSIÓN CORREGIDA SIN custom:is_admin
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
        print(f"🔧 Iniciando creación de tenant: {tenant_id}")
        
        # ===== 1. PostgreSQL (opcional) =====
        try:
            db_config = {
                'host': os.getenv('DB_HOST'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD')
            }
            
            if all(db_config.values()):
                conn = psycopg2.connect(**db_config)
                cur = conn.cursor()
                
                cur.execute("""
                    INSERT INTO tenants (tenant_id, company_name, subscription_tier, created_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (tenant_id) DO NOTHING
                """, (
                    tenant_id,
                    company_name,
                    tenant_data.get('subscription_tier', 'professional'),
                    datetime.utcnow()
                ))
                
                conn.commit()
                cur.close()
                conn.close()
                print(f"✅ Tenant creado en PostgreSQL")
            else:
                print("⚠️ PostgreSQL no configurado, omitiendo")
                
        except Exception as db_error:
            print(f"⚠️ Error PostgreSQL: {db_error}")
            # Continuar de todos modos
        
        # ===== 2. Cognito (IMPORTANTE) =====
        cognito = boto3.client('cognito-idp', region_name=os.getenv("AWS_REGION", "us-east-2"))
        user_pool_id = os.getenv("COGNITO_POOL_ID", "us-east-2_Wi7VHkSWm")
        
        print(f"🔑 Creando usuario en Cognito: {admin_email}")
        
        # Atributos SEGUROS (sin custom:is_admin)
        user_attributes = [
            {'Name': 'email', 'Value': admin_email},
            {'Name': 'email_verified', 'Value': 'True'},
            {'Name': 'name', 'Value': tenant_data.get('contact_name', 'Usuario')}
        ]
        
        # Intentar primero sin custom:tenant_id
        try:
            response = cognito.admin_create_user(
                UserPoolId=user_pool_id,
                Username=admin_email,
                TemporaryPassword=temp_password,
                MessageAction='SUPPRESS',
                UserAttributes=user_attributes
            )
            print("✅ Usuario creado en Cognito exitosamente")
            
        except Exception as e:
            print(f"⚠️ Error creando usuario: {e}")
            # Si falla, podríamos intentar otro método
            
            # Método de respaldo: crear sin atributos
            try:
                response = cognito.admin_create_user(
                    UserPoolId=user_pool_id,
                    Username=admin_email,
                    TemporaryPassword=temp_password,
                    MessageAction='SUPPRESS'
                )
                print("✅ Usuario creado (método simple)")
            except Exception as e2:
                print(f"❌ Error crítico: {e2}")
                return {
                    "success": False,
                    "error": f"No se pudo crear usuario en Cognito: {e2}",
                    "tenant_id": tenant_id
                }
        
        return {
            "success": True,
            "tenant_id": tenant_id,
            "email": admin_email,
            "temp_password": temp_password,
            "message": "Registro completado exitosamente. Guarda estas credenciales."
        }
        
    except Exception as e:
        print(f"❌ Error general: {e}")
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