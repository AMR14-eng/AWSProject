# billing.py
from app.models import Tenant, TenantUsage, db, LabResult
from datetime import date, datetime, timedelta
import calendar
import json
from decimal import Decimal

RATE = {
    "base_fee": 299.0,
    "included_results": 1000,
    "overage_per_result": 0.5,
    "storage_per_gb": 0.5,
    "api_per_1000_calls": 0.10,
    "monthly_fee_professional": 299.0,
    "monthly_fee_enterprise": 599.0,
    "monthly_fee_basic": 99.0
}

def calculate_tenant_bill(tenant_id, month_date):
    """Calculate detailed bill for a tenant in a specific month"""
    usage = TenantUsage.query.filter_by(tenant_id=tenant_id, month=month_date).first()
    if not usage:
        return None
    
    tenant = Tenant.query.filter_by(tenant_id=tenant_id).first()
    if not tenant:
        return None
    
    # Get tier-based base fee
    tier_fee = {
        "basic": RATE["monthly_fee_basic"],
        "professional": RATE["monthly_fee_professional"],
        "enterprise": RATE["monthly_fee_enterprise"]
    }.get(tenant.subscription_tier, RATE["base_fee"])
    
    # Calculate usage-based charges
    overage = max(0, usage.results_processed - RATE["included_results"])
    overage_charge = Decimal(str(overage)) * Decimal(str(RATE["overage_per_result"]))
    
    storage_gb = Decimal(str(usage.storage_bytes or 0)) / Decimal('1e9')
    storage_charge = storage_gb * Decimal(str(RATE["storage_per_gb"]))
    
    api_charge = (Decimal(str(usage.api_calls or 0)) / Decimal('1000.0')) * Decimal(str(RATE["api_per_1000_calls"]))
    
    subtotal = tier_fee + float(overage_charge) + float(storage_charge) + float(api_charge)
    tax = subtotal * 0.16  # 16% IVA (ajusta según tu país)
    total = subtotal + tax
    
    invoice = {
        "tenant_id": tenant_id,
        "company_name": tenant.company_name,
        "month": month_date.isoformat(),
        "subscription_tier": tenant.subscription_tier,
        "items": [
            {
                "description": f"Suscripción {tenant.subscription_tier.capitalize()}",
                "quantity": 1,
                "unit_price": float(tier_fee),
                "total": float(tier_fee)
            },
            {
                "description": f"Resultados procesados ({usage.results_processed} total, {RATE['included_results']} incluidos)",
                "quantity": overage,
                "unit_price": float(RATE["overage_per_result"]),
                "total": float(overage_charge)
            } if overage > 0 else None,
            {
                "description": f"Almacenamiento ({storage_gb:.2f} GB)",
                "quantity": float(storage_gb),
                "unit_price": float(RATE["storage_per_gb"]),
                "total": float(storage_charge)
            } if float(storage_charge) > 0 else None,
            {
                "description": f"Llamadas API ({usage.api_calls:,} llamadas)",
                "quantity": float(usage.api_calls),
                "unit_price": float(RATE["api_per_1000_calls"] / 1000),
                "total": float(api_charge)
            } if float(api_charge) > 0 else None
        ],
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "currency": "USD",
        "invoice_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=15)).isoformat()
    }
    
    # Remove None items
    invoice["items"] = [item for item in invoice["items"] if item is not None]
    
    return invoice

def generate_invoice_for_all_tenants(month_date=None):
    """Generate invoices for all tenants for a specific month"""
    if month_date is None:
        month_date = date.today().replace(day=1)
    
    invoices = []
    tenants = Tenant.query.all()
    
    for tenant in tenants:
        invoice = calculate_tenant_bill(tenant.tenant_id, month_date)
        if invoice:
            invoices.append(invoice)
    
    return invoices

def save_invoice_to_json(invoice):
    """Save invoice as JSON file"""
    import os
    from pathlib import Path
    
    invoices_dir = Path("invoices")
    invoices_dir.mkdir(exist_ok=True)
    
    filename = f"invoice_{invoice['tenant_id']}_{invoice['month']}.json"
    filepath = invoices_dir / filename
    
    with open(filepath, 'w') as f:
        json.dump(invoice, f, indent=2, default=str)
    
    return str(filepath)

def get_monthly_usage_summary(tenant_id, year=None):
    """Get usage summary for a tenant for all months in a year"""
    if year is None:
        year = date.today().year
    
    summary = []
    for month in range(1, 13):
        month_date = date(year, month, 1)
        usage = TenantUsage.query.filter_by(
            tenant_id=tenant_id, 
            month=month_date
        ).first()
        
        if usage:
            summary.append({
                "month": month_date.strftime("%Y-%m"),
                "results_processed": usage.results_processed,
                "api_calls": usage.api_calls,
                "storage_gb": (usage.storage_bytes or 0) / 1e9
            })
    
    return summary