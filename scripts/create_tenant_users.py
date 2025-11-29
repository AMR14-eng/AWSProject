# create_tenant_users_fixed.py
import boto3
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Cargar variables de entorno
load_dotenv()

def create_tenant_users():
    print("🔍 Leyendo variables de entorno...")
    
    # Usa COGNITO_POOL_ID (que ya tienes) en lugar de COGNITO_USER_POOL_ID
    user_pool_id = os.getenv('COGNITO_POOL_ID') or os.getenv('COGNITO_USER_POOL_ID')
    client_id = os.getenv('COGNITO_APP_CLIENT_ID') or os.getenv('COGNITO_CLIENT_ID')
    region = os.getenv('AWS_REGION', 'us-east-2')
    
    print(f"User Pool ID: {user_pool_id}")
    print(f"Client ID: {client_id}")
    print(f"Region: {region}")
    
    if not user_pool_id:
        print("❌ ERROR: No se encontró COGNITO_POOL_ID o COGNITO_USER_POOL_ID en .env")
        return
    
    # Configuración de Cognito
    cognito = boto3.client('cognito-idp', region_name=region)
    
    # Configuración de la base de datos
    db_config = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    tenants = [
        {"tenant_id": "laba", "company_name": "Laboratorio A"},
        {"tenant_id": "labb", "company_name": "Laboratorio B"}
    ]
    
    # Conectar a la base de datos
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        print("✅ Conectado a la base de datos")
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        return
    
    for tenant_data in tenants:
        print(f"\n--- Procesando {tenant_data['tenant_id']} ---")
        
        # 1. Verificar si el tenant ya existe en PostgreSQL
        try:
            cur.execute("SELECT tenant_id FROM tenants WHERE tenant_id = %s", (tenant_data['tenant_id'],))
            existing_tenant = cur.fetchone()
            
            if existing_tenant:
                print(f"✅ Tenant ya existe en DB: {tenant_data['tenant_id']}")
            else:
                cur.execute("""
                    INSERT INTO tenants (tenant_id, company_name, subscription_tier) 
                    VALUES (%s, %s, %s)
                """, (tenant_data['tenant_id'], tenant_data['company_name'], 'professional'))
                conn.commit()
                print(f"✅ Tenant creado en DB: {tenant_data['tenant_id']}")
                
        except Exception as e:
            print(f"❌ Error con la base de datos: {e}")
            conn.rollback()
            continue
        
        # 2. Crear usuario en Cognito
        email = f"user@{tenant_data['tenant_id']}.com"
        try:
            response = cognito.admin_create_user(
                UserPoolId=user_pool_id,
                Username=email,
                TemporaryPassword='TempPassword123!',
                MessageAction='SUPPRESS',
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'True'},
                    {'Name': 'custom:tenant_id', 'Value': tenant_data['tenant_id']}
                ]
            )
            print(f"✅ Usuario creado en Cognito: {email}")
            print(f"   Contraseña temporal: TempPassword123!")
            print(f"   Estado: {response['User']['UserStatus']}")
            
        except cognito.exceptions.UsernameExistsException:
            print(f"⚠️  Usuario ya existe en Cognito: {email}")
        except Exception as e:
            print(f"❌ Error creando usuario en Cognito: {e}")
    
    # Cerrar conexión
    cur.close()
    conn.close()
    
    print("\n🎉 Proceso completado!")
    print("\n📋 CREDENCIALES PARA ACCEDER:")
    print("Lab A - Usuario: user@laba.com, Contraseña: TempPassword123!")
    print("Lab B - Usuario: user@labb.com, Contraseña: TempPassword123!")
    print("\n⚠️  IMPORTANTE: En el primer login, Cognito pedirá cambiar la contraseña")

if __name__ == "__main__":
    create_tenant_users()