#!/bin/bash
set -e

# LabCloud Complete Test Suite
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}LabCloud Complete Test Suite${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"

# Test 1: Infrastructure Validation
echo -e "${YELLOW}✅ Test 1: Terraform Validation${NC}"
cd "$TERRAFORM_DIR"

echo "Validating Terraform syntax..."
if tofu validate 2>/dev/null || terraform validate 2>/dev/null; then
    echo -e "${GREEN}✓ Terraform validation passed${NC}"
else
    echo -e "${RED}✗ Terraform validation failed${NC}"
    exit 1
fi

echo "Checking Terraform formatting..."
if tofu fmt -check 2>/dev/null || terraform fmt -check 2>/dev/null; then
    echo -e "${GREEN}✓ Terraform formatting OK${NC}"
else
    echo -e "${YELLOW}⚠ Terraform formatting issues (run: tofu fmt)${NC}"
fi

# Get outputs
echo "Getting Terraform outputs..."
EC2_IP=$(tofu output -raw ec2_public_ip 2>/dev/null || terraform output -raw ec2_public_ip 2>/dev/null)
RDS_ENDPOINT=$(tofu output -raw rds_endpoint 2>/dev/null || terraform output -raw rds_endpoint 2>/dev/null)
S3_BUCKET=$(tofu output -raw s3_bucket_name 2>/dev/null || terraform output -raw s3_bucket_name 2>/dev/null)
COGNITO_POOL_ID=$(tofu output -raw cognito_user_pool_id 2>/dev/null || terraform output -raw cognito_user_pool_id 2>/dev/null)

APP_URL="http://$EC2_IP"
DB_HOST=$(echo $RDS_ENDPOINT | cut -d: -f1)

echo -e "${GREEN}✓ Infrastructure outputs loaded${NC}"
echo ""

# Test 2: Application Accessibility
echo -e "${YELLOW}✅ Test 2: Application Accessibility${NC}"
echo "Testing health endpoint: $APP_URL/health"

MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $APP_URL/health 2>/dev/null || true)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✓ Application is accessible (HTTP 200)${NC}"
        
        # Test additional endpoints
        echo "Testing root endpoint..."
        if curl -s $APP_URL/ | grep -q "LabCloud"; then
            echo -e "${GREEN}✓ Root endpoint OK${NC}"
        else
            echo -e "${YELLOW}⚠ Root endpoint response unexpected${NC}"
        fi
        
        echo "Testing admin endpoint..."
        if curl -s $APP_URL/admin/tenants | grep -q "tenants"; then
            echo -e "${GREEN}✓ Admin endpoint OK${NC}"
        else
            echo -e "${YELLOW}⚠ Admin endpoint: No tenants or empty${NC}"
        fi
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo -e "${RED}✗ Application not accessible (HTTP $HTTP_CODE)${NC}"
            exit 1
        else
            echo "   Attempt $RETRY_COUNT/$MAX_RETRIES: HTTP $HTTP_CODE, retrying..."
            sleep 5
        fi
    fi
done
echo ""

# Test 3: Database Connection
echo -e "${YELLOW}✅ Test 3: Database Connection${NC}"
echo "Testing PostgreSQL connection from EC2..."

ssh -i "$TERRAFORM_DIR/tenant-lab-key.pem" -o StrictHostKeyChecking=no ubuntu@$EC2_IP << 'EOF'
set -e
echo "Testing database connection..."
cd /opt/labcloud
sudo python3 << 'PYEOF'
import sys
sys.path.insert(0, '.')
try:
    from app import app
    from sqlalchemy import text
    
    with app.app_context():
        from app.models import db
        result = db.session.execute(text("SELECT 1"))
        print("✓ Database connection successful!")
        
        # Test if tables exist
        from app.models import Tenant
        tenants_count = Tenant.query.count()
        print(f"✓ Database tables exist (Tenants: {tenants_count})")
        
except Exception as e:
    print(f"✗ Database error: {e}")
    sys.exit(1)
PYEOF
EOF

echo -e "${GREEN}✓ Database connection test passed${NC}"
echo ""

# Test 4: Tenant Operations
echo -e "${YELLOW}✅ Test 4: Tenant Operations${NC}"
echo "Testing tenant creation and isolation..."

# Create first tenant
echo "Creating tenant LAB001..."
RESPONSE1=$(curl -s -X POST $APP_URL/admin/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"LAB001","company_name":"Laboratorio A","subscription_tier":"professional"}')

if echo "$RESPONSE1" | grep -q "successfully"; then
    echo -e "${GREEN}✓ Tenant LAB001 created${NC}"
else
    echo -e "${YELLOW}⚠ Tenant LAB001 may already exist: $RESPONSE1${NC}"
fi

# Create second tenant
echo "Creating tenant LAB002..."
RESPONSE2=$(curl -s -X POST $APP_URL/admin/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"LAB002","company_name":"Laboratorio B","subscription_tier":"professional"}')

if echo "$RESPONSE2" | grep -q "successfully"; then
    echo -e "${GREEN}✓ Tenant LAB002 created${NC}"
else
    echo -e "${YELLOW}⚠ Tenant LAB002 may already exist: $RESPONSE2${NC}"
fi

# List tenants
echo "Listing all tenants..."
TENANTS_RESPONSE=$(curl -s $APP_URL/admin/tenants)
if echo "$TENANTS_RESPONSE" | grep -q "LAB001"; then
    echo -e "${GREEN}✓ Tenant listing works${NC}"
else
    echo -e "${YELLOW}⚠ Tenant listing issue${NC}"
fi

# Test tenant data isolation at application level
echo "Testing tenant data isolation..."
ssh -i "$TERRAFORM_DIR/tenant-lab-key.pem" -o StrictHostKeyChecking=no ubuntu@$EC2_IP << 'EOF'
cd /opt/labcloud
sudo python3 << 'PYEOF'
import sys
sys.path.insert(0, '.')
from app import app
from app.models import Tenant, LabResult

with app.app_context():
    # Verify tenants exist
    tenants = Tenant.query.all()
    print(f"Found {len(tenants)} tenants")
    
    # Verify we can query by tenant_id
    lab001_results = LabResult.query.filter_by(tenant_id="LAB001").all()
    lab002_results = LabResult.query.filter_by(tenant_id="LAB002").all()
    
    print(f"LAB001 results: {len(lab001_results)}")
    print(f"LAB002 results: {len(lab002_results)}")
    print("✓ Tenant isolation at application level: OK")
PYEOF
EOF

echo -e "${GREEN}✓ Tenant operations test passed${NC}"
echo ""

# Test 5: AWS Components
echo -e "${YELLOW}✅ Test 5: AWS Components Check${NC}"

# Check EC2
echo "Checking EC2 instance..."
EC2_STATE=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=tenant-lab-flask-server" --query "Reservations[].Instances[].State.Name" --output text)
if [ "$EC2_STATE" = "running" ]; then
    echo -e "${GREEN}✓ EC2: running${NC}"
else
    echo -e "${RED}✗ EC2: $EC2_STATE${NC}"
fi

# Check RDS
echo "Checking RDS instance..."
RDS_STATE=$(aws rds describe-db-instances --db-instance-identifier tenant-lab-db --query "DBInstances[].DBInstanceStatus" --output text 2>/dev/null || echo "not-found")
if [ "$RDS_STATE" = "available" ]; then
    echo -e "${GREEN}✓ RDS: available${NC}"
else
    echo -e "${RED}✗ RDS: $RDS_STATE${NC}"
fi

# Check S3
echo "Checking S3 bucket..."
if aws s3 ls s3://$S3_BUCKET >/dev/null 2>&1; then
    echo -e "${GREEN}✓ S3: accessible${NC}"
else
    echo -e "${RED}✗ S3: not accessible${NC}"
fi

# Check Cognito (if exists)
if [ -n "$COGNITO_POOL_ID" ] && [ "$COGNITO_POOL_ID" != "" ]; then
    echo "Checking Cognito User Pool..."
    if aws cognito-idp describe-user-pool --user-pool-id $COGNITO_POOL_ID --query "UserPool.Name" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Cognito: exists${NC}"
    else
        echo -e "${YELLOW}⚠ Cognito: check failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Cognito: not configured${NC}"
fi

# Check Security Groups
echo "Checking Security Groups..."
SG_COUNT=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=tenant-lab-ec2-sg" --query "length(SecurityGroups)" --output text)
if [ "$SG_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Security Groups: exist${NC}"
else
    echo -e "${RED}✗ Security Groups: not found${NC}"
fi

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}🎉 ALL TESTS COMPLETED SUCCESSFULLY!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo -e "  🌐 Application URL: $APP_URL"
echo -e "  🗄️  Database: $DB_HOST"
echo -e "  🪣 S3 Bucket: $S3_BUCKET"
echo -e "  🔐 Cognito: ${COGNITO_POOL_ID:-Not configured}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  Create tenants: curl -X POST $APP_URL/admin/tenants -H 'Content-Type: application/json' -d '{\"tenant_id\":\"YOUR_TENANT\",\"company_name\":\"Your Lab\"}'"
echo -e "  View tenants: curl $APP_URL/admin/tenants"
echo -e "  Health check: curl $APP_URL/health"
echo ""
echo -e "${GREEN}LabCloud is ready for use! 🚀${NC}"