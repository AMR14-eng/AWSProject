from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Tenant(db.Model):
    __tablename__ = "tenants"
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.String(64), unique=True, nullable=False)  # e.g. LAB001
    company_name = db.Column(db.String(200))
    subscription_tier = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserProfile(db.Model):
    __tablename__ = "user_profiles"
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.String(64), db.ForeignKey('tenants.tenant_id'), index=True, nullable=False)
    user_id = db.Column(db.String(128))  # id from Cognito
    email = db.Column(db.String(200))
    name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LabResult(db.Model):
    __tablename__ = "lab_results"
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.String(64), index=True, nullable=False)
    patient_id = db.Column(db.String(128), nullable=False)
    test_code = db.Column(db.String(50))
    test_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TenantUsage(db.Model):
    __tablename__ = "tenant_usage"
    tenant_id = db.Column(db.String(64), primary_key=True)
    month = db.Column(db.Date, primary_key=True)
    results_processed = db.Column(db.Integer, default=0)
    api_calls = db.Column(db.Integer, default=0)
    storage_bytes = db.Column(db.BigInteger, default=0)
