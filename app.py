from flask import Flask, request, jsonify, g
from config import Config
from models import db, Tenant, UserProfile, LabResult
from auth import cognito_required, verify_jwt
from s3client import upload_bytes
from usage import incr_results_processed, incr_api_calls
from provisioner.py import provision_tenant  # if in same folder, adjust import

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

@app.before_request
def attach_tenant_from_header():
    # Simple: accept X-Tenant-Id header OR try to get it from JWT claims
    tenant_id = request.headers.get("X-Tenant-Id")
    if not tenant_id:
        token = request.headers.get("Authorization")
        if token:
            try:
                claims = verify_jwt(token.split(" ")[1])
                tenant_id = claims.get("custom:tenant_id") or claims.get("tenant_id")
            except Exception:
                tenant_id = None
    g.tenant_id = tenant_id

@app.route("/")
def home():
    return "LabCloud Flask API"

# Admin: create tenant (calls provisioner)
@app.route("/admin/tenants", methods=["POST"])
def create_tenant():
    data = request.json
    tenant_id = data.get("tenant_id")
    company_name = data.get("company_name")
    if not tenant_id:
        return {"message": "tenant_id required"}, 400
    res = provision_tenant(tenant_id, company_name)
    return jsonify(res), 201

# Create a lab result
@app.route("/api/v1/results", methods=["POST"])
@cognito_required
def create_result():
    tenant_id = g.tenant_id or request.json.get("tenant_id")
    if not tenant_id:
        return {"message": "No tenant_id"}, 400
    data = request.json
    patient_id = data.get("patient_id")
    test_code = data.get("test_code")
    test_data = data.get("test_data")
    r = LabResult(tenant_id=tenant_id, patient_id=patient_id, test_code=test_code, test_data=test_data)
    db.session.add(r)
    db.session.commit()
    incr_results_processed(tenant_id, 1)
    incr_api_calls(tenant_id, 1)
    return {"id": r.id}, 201

# Query results (only tenant's)
@app.route("/api/v1/results/<patient_id>", methods=["GET"])
@cognito_required
def get_results(patient_id):
    tenant_id = g.tenant_id
    if not tenant_id:
        return {"message": "No tenant_id"}, 400
    results = LabResult.query.filter_by(tenant_id=tenant_id, patient_id=patient_id).all()
    out = [{"id": r.id, "test_code": r.test_code, "test_data": r.test_data} for r in results]
    incr_api_calls(tenant_id, 1)
    return jsonify(out)

# Upload file to S3
@app.route("/api/v1/upload", methods=["POST"])
@cognito_required
def upload_file():
    tenant_id = g.tenant_id
    if not tenant_id:
        return {"message": "No tenant_id"}, 400
    file_content = request.data or b""
    key = f"{tenant_id}/uploads/{int(time.time())}.bin"
    bucket = f"{app.config['S3_BUCKET_PREFIX']}{tenant_id.lower()}"
    upload_bytes(bucket, key, file_content)
    # Roughly add bytes to usage (optional)
    # usage.storage_bytes += len(file_content) ...
    incr_api_calls(tenant_id, 1)
    return {"s3": f"s3://{bucket}/{key}"}, 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
