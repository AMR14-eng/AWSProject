# LabCloud - Multi-Tenant Healthcare Lab Results Platform

🏥 **SaaS platform for small laboratories with complete data isolation**

## 📋 Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Deployment Guide](#deployment-guide)
- [Testing](#testing)
- [Billing System](#billing-system)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

## 🌟 Overview

LabCloud is a multi-tenant SaaS platform that allows small laboratories to:
- Store and manage lab results securely
- Provide patient-facing portals
- Track usage and billing per tenant
- Scale to 50+ laboratory clients on shared infrastructure

### Key Features
- ✅ **Multi-Tenant Architecture** with complete data isolation
- ✅ **HIPAA Compliant** - Encryption at rest and in transit
- ✅ **Automated Tenant Provisioning** - New labs ready in < 5 minutes
- ✅ **Usage Tracking & Billing** - Per-tenant metrics with automated invoicing
- ✅ **RESTful API** with JWT authentication
- ✅ **Infrastructure as Code** - 100% OpenTofu/Terraform

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd AWSProject
```

### 2. Deploy Infrastructure
```bash
cd terraform
tofu init
tofu validate
tofu apply
```

### 3. Deploy Application
```bash
./scripts/deploy.sh
```

### 4. Run Tests
```bash
./scripts/test-labcloud.sh
```

## 📋 Prerequisites

### Required Tools
- **OpenTofu** >= 1.0 (or Terraform >= 1.0)
- **AWS CLI** >= 2.0
- **Python** >= 3.8
- **Git**

### AWS Account Requirements
- Active AWS account with appropriate permissions
- AWS credentials configured (`aws configure`)
- Default region set to `us-east-2`

## 📚 Deployment Guide

### Step-by-Step Deployment

1. **Infrastructure Setup**
```bash
cd terraform
tofu init
tofu plan
tofu apply
```

2. **Application Deployment**
```bash
./scripts/deploy.sh
```

3. **Verification**
```bash
./scripts/test-labcloud.sh
```

### Deployment Outputs
After successful deployment, you'll get:
- **Application URL**: `http://YOUR_EC2_IP`
- **Health Check**: `http://YOUR_EC2_IP/health`
- **SSH Access**: `ssh -i tenant-lab-key.pem ubuntu@YOUR_EC2_IP`

## 💰 Billing System

### Overview
The platform includes automated usage tracking and billing:

**Pricing Structure:**
- **Base Fee**: $299/month
- **Included Results**: 1,000 results/month
- **Overage**: $0.50 per additional result
- **Storage**: $0.50 per GB/month
- **API Calls**: $0.10 per 1,000 calls

### Using the Billing System

**Generate Invoice for Tenant:**
```bash
# SSH into EC2 and run:
cd /opt/labcloud
sudo python3 -c "
from app.billing import calculate_tenant_bill
from datetime import date

invoice = calculate_tenant_bill('LAB001', date.today().replace(day=1))
print('Monthly Invoice:', invoice)
"
```

**Track Current Usage:**
```bash
sudo python3 -c "
from app.models import TenantUsage
from datetime import date
from app import app

with app.app_context():
    current_month = date.today().replace(day=1)
    usage = TenantUsage.query.filter_by(month=current_month).all()
    for u in usage:
        print(f'{u.tenant_id}: {u.results_processed} results, {u.api_calls} API calls')
"
```

## 🧪 Testing

### Automated Test Suite
```bash
./scripts/test-labcloud.sh
```

**Tests Included:**
- Infrastructure validation
- Application accessibility
- Database connectivity
- Tenant operations
- AWS component verification

### Manual Testing
```bash
# Test health endpoint
curl http://$(tofu output -raw ec2_public_ip)/health

# Create test tenant
curl -X POST http://$(tofu output -raw ec2_public_ip)/admin/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"TEST001","company_name":"Test Lab"}'

# List tenants
curl http://$(tofu output -raw ec2_public_ip)/admin/tenants
```

## 🔌 API Reference

### Public Endpoints
- `GET /` - Application information
- `GET /health` - Health check with database status

### Admin Endpoints
- `POST /admin/tenants` - Create new tenant
- `GET /admin/tenants` - List all tenants
- `GET /admin/tenants/<id>` - Get tenant details

### Tenant API Endpoints
- `POST /api/v1/results` - Create lab result (Cognito required)
- `GET /api/v1/results/<patient_id>` - Get patient results (Cognito required)
- `POST /api/v1/upload` - Upload file to S3 (Cognito required)

## 🔧 Troubleshooting

### Common Issues

**Application not accessible:**
```bash
ssh -i terraform/tenant-lab-key.pem ubuntu@$(tofu output -raw ec2_public_ip)
sudo systemctl status labcloud
sudo journalctl -u labcloud -n 50
```

**Database connection issues:**
```bash
PGPASSWORD='lAbTeNaNt!' psql -h $(tofu output -raw rds_endpoint) -U postgres -d labcloud -c "SELECT 1;"
```

**Deployment script fails:**
- Use Git Bash on Windows instead of PowerShell
- Ensure AWS credentials are configured
- Check Terraform state exists

### Log Files
- **Application**: `sudo journalctl -u labcloud -f`
- **Nginx**: `sudo tail -f /var/log/nginx/error.log`
- **Bootstrap**: `sudo tail -f /var/log/user-data.log`

---

**Deployment Time**: 20-30 minutes  
**Monthly Cost**: $4-30 (Free Tier to production)  
**Tenant Capacity**: 50+ laboratories  
```

