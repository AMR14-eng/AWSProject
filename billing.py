from models import Tenant, TenantUsage, db
from datetime import date

RATE = {
    "base_fee": 299.0,
    "included_results": 1000,
    "overage_per_result": 0.5,
    "storage_per_gb": 0.5,
    "api_per_1000_calls": 0.10
}

def calculate_tenant_bill(tenant_id, month_date):
    usage = TenantUsage.query.filter_by(tenant_id=tenant_id, month=month_date).first()
    if not usage:
        return None
    base = RATE["base_fee"]
    overage = max(0, usage.results_processed - RATE["included_results"])
    overage_charge = overage * RATE["overage_per_result"]
    storage_gb = (usage.storage_bytes or 0)/1e9
    storage_charge = storage_gb * RATE["storage_per_gb"]
    api_charge = (usage.api_calls or 0) / 1000.0 * RATE["api_per_1000_calls"]
    total = base + overage_charge + storage_charge + api_charge
    invoice = {
        "tenant_id": tenant_id,
        "month": month_date.isoformat(),
        "base": base,
        "overage_charge": overage_charge,
        "storage_charge": storage_charge,
        "api_charge": api_charge,
        "total": total
    }
    return invoice
