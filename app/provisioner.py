import boto3
from app.config import S3_BUCKET

cognito = boto3.client("cognito-idp")
rds = boto3.client("rds")
apigw = boto3.client("apigatewayv2")

def provision_tenant(tenant_id):
    # Step 1 — NO CREAR BUCKETS (todos usan el global)

    # Step 2 — Crear un user pool POR TENANT (si lo necesitas)
    user_pool = cognito.create_user_pool(
        PoolName=f"tenant-{tenant_id}-pool"
    )

    # Step 3 — Crear schema en PostgreSQL (no nuevo database)
    create_schema_for_tenant(tenant_id)

    # Step 4 — Crear endpoint del tenant (subdominio o route)
    resp = apigw.create_api(
        Name=f"tenant-{tenant_id}-api",
        ProtocolType="HTTP"
    )

    api_endpoint = resp["ApiEndpoint"]

    return {
        "tenant_id": tenant_id,
        "user_pool_id": user_pool["UserPool"]["Id"],
        "s3_bucket": S3_BUCKET,     # SIEMPRE el mismo
        "api_endpoint": api_endpoint
    }


def create_schema_for_tenant(tenant_id):
    import psycopg2
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {tenant_id};")
    conn.commit()
    cur.close()
    conn.close()
