from flask import Flask, request, jsonify, g, send_from_directory
from flask_migrate import Migrate
from flask_cors import CORS
from app.config import Config
from app.models import db, Tenant, UserProfile, LabResult
from app.auth import cognito_required, verify_jwt
from app.s3client import upload_bytes
from app.usage import incr_results_processed, incr_api_calls
from app.provisioner import provision_tenant
import time
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Configurar SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = Config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

@app.before_request
def attach_tenant_from_header():
    """Extract tenant_id from header or JWT"""
    # Simple: accept X-Tenant-Id header OR try to get it from JWT claims
    tenant_id = request.headers.get("X-Tenant-Id")
    if not tenant_id:
        token = request.headers.get("Authorization")
        if token:
            try:
                token_value = token.split(" ")[1] if " " in token else token
                claims = verify_jwt(token_value)
                tenant_id = claims.get("custom:tenant_id") or claims.get("tenant_id")
            except Exception as e:
                logger.warning(f"Failed to extract tenant from JWT: {e}")
                tenant_id = None
    g.tenant_id = tenant_id


@app.route("/")
def serve_frontend():
    """Sirve el frontend (index.html)"""
    try:
        # Ruta al directorio frontend
        frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        return send_from_directory(frontend_path, 'index.html')
    except Exception as e:
        # Fallback: mostrar info del API si el frontend no está disponible
        return jsonify({
            "message": "LabCloud Flask API - Frontend not available",
            "error": str(e),
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "admin": "/admin/tenants", 
                "api": "/api/v1"
            }
        }), 500

@app.route("/<path:path>")
def serve_static_files(path):
    """Sirve archivos estáticos (CSS, JS, imágenes)"""
    try:
        frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        return send_from_directory(frontend_path, path)
    except Exception as e:
        return jsonify({"error": "File not found", "details": str(e)}), 404


@app.route("/health")
def health():
    """Health check endpoint for ALB"""
    try:
        # Check database connection
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    health_status = {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "timestamp": time.time()
    }
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code

# ===== ADMIN ENDPOINTS =====

@app.route("/admin/tenants", methods=["POST"])
def create_tenant():
    """Create a new tenant (admin only)"""
    try:
        data = request.json
        tenant_id = data.get("tenant_id")
        company_name = data.get("company_name")
        subscription_tier = data.get("subscription_tier", "professional")
        
        if not tenant_id:
            return jsonify({"message": "tenant_id required"}), 400
        
        # Check if tenant already exists
        existing = Tenant.query.filter_by(tenant_id=tenant_id).first()
        if existing:
            return jsonify({"message": "Tenant already exists"}), 409
        
        # Create tenant record in database
        tenant = Tenant(
            tenant_id=tenant_id,
            company_name=company_name,
            subscription_tier=subscription_tier
        )
        db.session.add(tenant)
        db.session.commit()
        
        logger.info(f"Created tenant {tenant_id} in database")
        
        # Provision resources (async in production)
        try:
            provisioning_result = provision_tenant(tenant_id)
            logger.info(f"Provisioned resources for tenant {tenant_id}")
            
            return jsonify({
                "message": "Tenant created and provisioned successfully",
                "tenant_id": tenant_id,
                "provisioning": provisioning_result
            }), 201
        except Exception as e:
            logger.error(f"Provisioning failed for {tenant_id}: {e}")
            return jsonify({
                "message": "Tenant created but provisioning failed",
                "tenant_id": tenant_id,
                "error": str(e)
            }), 207  # Multi-Status
            
    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        return jsonify({"message": f"Failed to create tenant: {str(e)}"}), 500

@app.route("/admin/tenants", methods=["GET"])
def list_tenants():
    """List all tenants (admin only)"""
    try:
        tenants = Tenant.query.all()
        return jsonify({
            "tenants": [
                {
                    "tenant_id": t.tenant_id,
                    "company_name": t.company_name,
                    "subscription_tier": t.subscription_tier,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                }
                for t in tenants
            ],
            "count": len(tenants)
        })
    except Exception as e:
        logger.error(f"Failed to list tenants: {e}")
        return jsonify({"message": f"Failed to list tenants: {str(e)}"}), 500

@app.route("/admin/tenants/<tenant_id>", methods=["GET"])
def get_tenant(tenant_id):
    """Get tenant details (admin only)"""
    try:
        tenant = Tenant.query.filter_by(tenant_id=tenant_id).first()
        if not tenant:
            return jsonify({"message": "Tenant not found"}), 404
        
        return jsonify({
            "tenant_id": tenant.tenant_id,
            "company_name": tenant.company_name,
            "subscription_tier": tenant.subscription_tier,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None
        })
    except Exception as e:
        logger.error(f"Failed to get tenant: {e}")
        return jsonify({"message": f"Failed to get tenant: {str(e)}"}), 500

# ===== API ENDPOINTS (TENANT-SCOPED) =====

@app.route("/api/v1/results", methods=["POST"])
@cognito_required
def create_result():
    """Create a lab result for a tenant"""
    try:
        tenant_id = g.tenant_id or request.json.get("tenant_id")
        if not tenant_id:
            return jsonify({"message": "No tenant_id provided"}), 400
        
        # Verify tenant exists
        tenant = Tenant.query.filter_by(tenant_id=tenant_id).first()
        if not tenant:
            return jsonify({"message": "Tenant not found"}), 404
        
        data = request.json
        patient_id = data.get("patient_id")
        test_code = data.get("test_code")
        test_data = data.get("test_data")
        
        if not patient_id or not test_code:
            return jsonify({"message": "patient_id and test_code are required"}), 400
        
        # Create lab result
        r = LabResult(
            tenant_id=tenant_id,
            patient_id=patient_id,
            test_code=test_code,
            test_data=test_data
        )
        db.session.add(r)
        db.session.commit()
        
        # Track usage
        incr_results_processed(tenant_id, 1)
        incr_api_calls(tenant_id, 1)
        
        logger.info(f"Created result {r.id} for tenant {tenant_id}")
        
        return jsonify({
            "id": r.id,
            "message": "Lab result created successfully"
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create result: {e}")
        db.session.rollback()
        return jsonify({"message": f"Failed to create result: {str(e)}"}), 500

@app.route("/api/v1/results/<patient_id>", methods=["GET"])
@cognito_required
def get_results(patient_id):
    """Get lab results for a patient (tenant-scoped)"""
    try:
        tenant_id = g.tenant_id
        if not tenant_id:
            return jsonify({"message": "No tenant_id provided"}), 400
        
        # Query only this tenant's results
        results = LabResult.query.filter_by(
            tenant_id=tenant_id,
            patient_id=patient_id
        ).all()
        
        out = [
            {
                "id": r.id,
                "test_code": r.test_code,
                "test_data": r.test_data,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in results
        ]
        
        incr_api_calls(tenant_id, 1)
        
        return jsonify({
            "tenant_id": tenant_id,
            "patient_id": patient_id,
            "results": out,
            "count": len(out)
        })
        
    except Exception as e:
        logger.error(f"Failed to get results: {e}")
        return jsonify({"message": f"Failed to get results: {str(e)}"}), 500

@app.route("/api/v1/upload", methods=["POST"])
@cognito_required
def upload_file():
    """Upload a file to S3 (tenant-scoped)"""
    try:
        tenant_id = g.tenant_id
        if not tenant_id:
            return jsonify({"message": "No tenant_id provided"}), 400
        
        file_content = request.data or b""
        if not file_content:
            return jsonify({"message": "No file content provided"}), 400
        
        # Upload to S3 with tenant prefix
        bucket = app.config.get('S3_BUCKET', 'tenant-lab-bucket')
        key = f"{tenant_id}/uploads/{int(time.time())}.bin"
        
        upload_bytes(bucket, key, file_content)
        incr_api_calls(tenant_id, 1)
        
        logger.info(f"Uploaded file for tenant {tenant_id}: s3://{bucket}/{key}")
        
        return jsonify({
            "message": "File uploaded successfully",
            "s3_uri": f"s3://{bucket}/{key}",
            "size": len(file_content)
        }), 201
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({"message": f"Upload failed: {str(e)}"}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"message": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)