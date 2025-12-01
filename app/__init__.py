from flask import Flask, request, jsonify, g, send_from_directory
from flask_migrate import Migrate
from flask_cors import CORS
from app.config import Config
from app.models import db, Tenant, UserProfile, LabResult
from app.auth import cognito_required, verify_jwt
from app.s3client import upload_bytes
from app.usage import incr_results_processed, incr_api_calls
from app.provisioner import provision_tenant
from datetime import datetime, date  # ¡IMPORTANTE!
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

# Middleware para debug de rutas
@app.before_request
def debug_routes():
    """Debug: muestra qué ruta se está capturando"""
    if request.path.startswith('/api/'):
        logger.info(f"🌐 API Route: {request.path} - Method: {request.method}")

@app.before_request
def attach_tenant_from_header():
    """Extract tenant_id from header or JWT"""
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

# ========== HEALTH CHECK ==========
@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for ALB"""
    try:
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

# ========== PUBLIC REGISTRATION ENDPOINTS ==========
@app.route("/api/public/register", methods=["POST", "GET"])  # GET temporal para debug
def register_tenant():
    """Public endpoint to register a new tenant"""
    logger.info(f"🎯 /api/public/register - Method: {request.method}")
    
    # Para debug: si es GET, mostrar info
    if request.method == "GET":
        return jsonify({
            "endpoint": "/api/public/register",
            "methods_allowed": ["POST"],
            "description": "Register a new tenant",
            "required_fields": ["company_name", "email", "contact_name"],
            "status": "active"
        })
    
    # Procesar POST
    try:
        # Verificar content-type
        if not request.is_json:
            logger.warning("❌ Content-Type no es application/json")
            return jsonify({
                "success": False,
                "message": "Content-Type must be application/json"
            }), 400
        
        # Parsear JSON
        data = request.get_json(silent=True)
        logger.info(f"📦 JSON recibido: {data}")
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No JSON data received or invalid JSON"
            }), 400
        
        # Validar campos requeridos
        required_fields = ['company_name', 'email', 'contact_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Validar email format
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, data['email']):
            return jsonify({
                "success": False,
                "message": "Invalid email format"
            }), 400
        
        # Importar y crear tenant
        from app.tenant_registration import create_new_tenant_with_user
        
        logger.info(f"📋 Creando tenant para: {data['company_name']}")
        result = create_new_tenant_with_user(data)
        logger.info(f"🎯 Resultado: {result}")
        
        if result.get('success'):
            return jsonify({
                "success": True,
                "message": "Registration successful!",
                "tenant_id": result['tenant_id'],
                "email": result['email'],
                "temp_password": result.get('temp_password', 'Check your email'),
                "note": "You will be prompted to change your password on first login."
            }), 201
        else:
            return jsonify({
                "success": False,
                "message": f"Registration failed: {result.get('error', 'Unknown error')}"
            }), 500
            
    except Exception as e:
        logger.error(f"💥 Registration failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Registration failed: {str(e)}"
        }), 500

@app.route("/api/public/subscription-tiers", methods=["GET"])
def get_subscription_tiers():
    """Get available subscription tiers"""
    try:
        from app.tenant_registration import get_all_subscription_tiers
        tiers = get_all_subscription_tiers()
        return jsonify({"tiers": tiers})
    except Exception as e:
        logger.error(f"Failed to get subscription tiers: {e}")
        return jsonify({"message": f"Failed to get tiers: {str(e)}"}), 500

# ========== DASHBOARD ADMIN ENDPOINTS ==========
@app.route("/api/v1/admin/billing", methods=["GET"])
@cognito_required
def get_my_billing():
    """Get billing information for current tenant (admin view)"""
    try:
        tenant_id = g.tenant_id
        if not tenant_id:
            return jsonify({"message": "No tenant_id provided"}), 400
        
        from app.billing import calculate_tenant_bill, get_monthly_usage_summary
        
        # Get current month invoice
        today = date.today()
        current_month = date(today.year, today.month, 1)
        current_invoice = calculate_tenant_bill(tenant_id, current_month)
        
        # Get usage summary for current year
        usage_summary = get_monthly_usage_summary(tenant_id, today.year)
        
        return jsonify({
            "tenant_id": tenant_id,
            "current_invoice": current_invoice,
            "usage_summary": usage_summary,
            "year": today.year
        })
        
    except Exception as e:
        logger.error(f"Failed to get billing: {e}")
        return jsonify({"message": f"Failed to get billing: {str(e)}"}), 500

# ========== BILLING ENDPOINTS (ADMIN) ==========
@app.route("/admin/billing/invoices", methods=["GET"])
def list_invoices():
    """List all invoices for all tenants (admin only)"""
    try:
        from app.billing import generate_invoice_for_all_tenants
        
        month_str = request.args.get("month")
        if month_str:
            month_date = datetime.strptime(month_str, "%Y-%m").date()
        else:
            today = date.today()
            month_date = date(today.year, today.month, 1)
        
        invoices = generate_invoice_for_all_tenants(month_date)
        
        return jsonify({
            "month": month_date.isoformat(),
            "invoices": invoices,
            "total_invoices": len(invoices),
            "total_revenue": sum(inv["total"] for inv in invoices)
        })
    except Exception as e:
        logger.error(f"Failed to list invoices: {e}")
        return jsonify({"message": f"Failed to list invoices: {str(e)}"}), 500

@app.route("/admin/billing/tenants/<tenant_id>/invoices", methods=["GET"])
def get_tenant_invoices(tenant_id):
    """Get all invoices for a specific tenant"""
    try:
        from app.billing import calculate_tenant_bill
        
        year = request.args.get("year", date.today().year, type=int)
        invoices = []
        
        for month in range(1, 13):
            month_date = date(year, month, 1)
            invoice = calculate_tenant_bill(tenant_id, month_date)
            if invoice:
                invoices.append(invoice)
        
        return jsonify({
            "tenant_id": tenant_id,
            "year": year,
            "invoices": invoices,
            "total_amount": sum(inv["total"] for inv in invoices)
        })
    except Exception as e:
        logger.error(f"Failed to get tenant invoices: {e}")
        return jsonify({"message": f"Failed to get tenant invoices: {str(e)}"}), 500

@app.route("/admin/billing/tenants/<tenant_id>/usage", methods=["GET"])
def get_tenant_usage(tenant_id):
    """Get usage summary for a tenant"""
    try:
        from app.billing import get_monthly_usage_summary
        
        year = request.args.get("year", date.today().year, type=int)
        summary = get_monthly_usage_summary(tenant_id, year)
        
        return jsonify({
            "tenant_id": tenant_id,
            "year": year,
            "usage_summary": summary,
            "total_results": sum(item["results_processed"] for item in summary),
            "total_api_calls": sum(item["api_calls"] for item in summary)
        })
    except Exception as e:
        logger.error(f"Failed to get tenant usage: {e}")
        return jsonify({"message": f"Failed to get tenant usage: {str(e)}"}), 500

# ========== ADMIN ENDPOINTS ==========
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

# ========== API ENDPOINTS (TENANT-SCOPED) ==========
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

# ========== FRONTEND ROUTES (¡AL FINAL!) ==========
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

# ¡ESTA RUTA DEBE SER LA ÚLTIMA!
@app.route("/<path:path>")
def serve_static_files(path):
    """Sirve archivos estáticos (CSS, JS, imágenes)"""
    # Si es una ruta de API, no servir archivos estáticos
    if path.startswith('api/') or path.startswith('admin/'):
        return jsonify({
            "error": "Endpoint not found",
            "path": f"/{path}",
            "available_endpoints": ["/api/public/register", "/api/v1/results", "/health"]
        }), 404
    
    try:
        frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        return send_from_directory(frontend_path, path)
    except Exception as e:
        return jsonify({"error": "File not found", "details": str(e)}), 404

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"message": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "message": "Method not allowed",
        "error": str(error.description)
    }), 405

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"message": "Internal server error"}), 500

if __name__ == "__main__":
    # Ejecutar en modo debug para ver errores
    print("🚀 Starting LabCloud Flask API...")
    print("📋 Available endpoints:")
    print("   - GET  /health")
    print("   - POST /api/public/register")
    print("   - GET  /api/public/subscription-tiers")
    print("   - GET  /api/v1/results/<patient_id>")
    print("   - POST /api/v1/results")
    print("   - POST /api/v1/upload")
    print("   - GET  /admin/tenants")
    print("\n🔍 Debug mode: ON")
    app.run(host="0.0.0.0", port=5000, debug=True)