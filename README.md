# LabCloud - Multi-Tenant Healthcare Lab Results Platform

🏥 **SaaS platform for small laboratories with complete data isolation**

## 📋 Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Manual Deployment Guide](#manual-deployment-guide)
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
git clone https://github.com/AMR14-eng/AWSProject.git
cd AWSProject
```

### 2. Deploy Infrastructure
```bash
cd terraform
tofu init
tofu validate
tofu apply
```

### 3. Deploy Application (Manual)
Follow the [Manual Deployment Guide](#manual-deployment-guide) below.

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

## 📚 Manual Deployment Guide

### Step 1: Deploy Infrastructure with Terraform
```bash
cd terraform
tofu init
tofu plan
tofu apply
```

Save the outputs, especially:
- `ec2_public_ip` - Your EC2 instance IP
- `rds_endpoint` - Database connection string

### Step 2: Access Your EC2 Instance
```bash
ssh -i terraform/tenant-lab-key.pem ubuntu@YOUR_EC2_IP
```

### Step 3: Clone and Setup Application on EC2
```bash
# On the EC2 instance:
sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/AMR14-eng/AWSProject.git labcloud
cd labcloud
```

### Step 4: Install Dependencies
```bash
# Update system and install dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx postgresql-client

# Install Python packages
sudo pip3 install -r requirements.txt
```

### Step 5: Configure Environment
```bash
# Create environment file from template
cp .env.example .env

# Edit with your actual values from Terraform outputs
sudo nano .env
```

**Required .env variables:**
```bash
# Database (from Terraform outputs)
DB_HOST=your-rds-endpoint
DB_PORT=5432
DB_NAME=labcloud
DB_USER=postgres
DB_PASSWORD=your-db-password

# AWS (from Terraform outputs)
AWS_REGION=us-east-2
S3_BUCKET=your-s3-bucket-name
COGNITO_POOL_ID=your-cognito-pool-id
COGNITO_APP_CLIENT_ID=your-cognito-client-id

# Flask
FLASK_APP=wsgi:app
FLASK_ENV=production
SECRET_KEY=your-generated-secret-key
```

### Step 6: Configure System Services

**Create Systemd Service:**
```bash
sudo tee /etc/systemd/system/labcloud.service > /dev/null << 'EOF'
[Unit]
Description=LabCloud Flask Application
After=network.target

[Service]
User=root
WorkingDirectory=/opt/labcloud
Environment=PATH=/usr/local/bin:/usr/bin:/bin
EnvironmentFile=/opt/labcloud/.env
ExecStart=/usr/local/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

**Configure Nginx:**
```bash
sudo tee /etc/nginx/sites-available/labcloud > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    # Serve frontend static files
    location / {
        root /opt/labcloud/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to Flask backend
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Proxy admin requests
    location /admin/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
        access_log off;
    }
}
EOF
```

### Step 7: Enable and Start Services
```bash
# Enable site
sudo ln -sf /etc/nginx/sites-available/labcloud /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Start services
sudo systemctl daemon-reload
sudo systemctl enable labcloud
sudo systemctl start labcloud
sudo systemctl enable nginx
sudo systemctl restart nginx
```

### Step 8: Initialize Database
```bash
cd /opt/labcloud
sudo python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully!')
"
```

### Step 9: Verify Deployment
```bash
# Check services are running
sudo systemctl status labcloud
sudo systemctl status nginx

# Test health endpoint
curl http://localhost/health

# Test frontend
curl -I http://localhost/
```

## 🚀 Updates and Maintenance

### Update Application (When Code Changes)
```bash
# On EC2 instance:
cd /opt/labcloud
sudo git pull
sudo systemctl restart labcloud
```

### View Logs
```bash
# Application logs
sudo journalctl -u labcloud -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log

# Real-time application logs
sudo tail -f /var/log/labcloud.log
```

## 💰 Billing System

### Using the Billing System

**Generate Invoice for Tenant:**
```bash
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

### Manual Testing
```bash
# Test health endpoint
curl http://YOUR_EC2_IP/health

# Create test tenant
curl -X POST http://YOUR_EC2_IP/admin/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"TEST001","company_name":"Test Lab"}'

# List tenants
curl http://YOUR_EC2_IP/admin/tenants
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
ssh -i terraform/tenant-lab-key.pem ubuntu@YOUR_EC2_IP
sudo systemctl status labcloud
sudo journalctl -u labcloud -n 50
```

**Database connection issues:**
```bash
# Test database connection
PGPASSWORD='your-db-password' psql -h YOUR_RDS_ENDPOINT -U postgres -d labcloud -c "SELECT 1;"
```

**Nginx configuration errors:**
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

### Service Management
```bash
# Restart application
sudo systemctl restart labcloud

# Restart Nginx
sudo systemctl restart nginx

# Check service status
sudo systemctl status labcloud
sudo systemctl status nginx
```

---

**Deployment Time**: 15-20 minutes  
**Monthly Cost**: $4-30 (Free Tier to production)  
**Tenant Capacity**: 50+ laboratories  
**Update Method**: `git pull && systemctl restart labcloud`

For questions or issues, check the application logs with `sudo journalctl -u labcloud -f`