from app.models import TenantUsage, db
from datetime import date

def incr_results_processed(tenant_id, n=1):
    month = date.today().replace(day=1)
    usage = TenantUsage.query.get((tenant_id, month))
    if not usage:
        usage = TenantUsage(tenant_id=tenant_id, month=month, results_processed=0, api_calls=0, storage_bytes=0)
        db.session.merge(usage)
    usage.results_processed += n
    db.session.commit()

def incr_api_calls(tenant_id, n=1):
    month = date.today().replace(day=1)
    usage = TenantUsage.query.get((tenant_id, month))
    if not usage:
        usage = TenantUsage(tenant_id=tenant_id, month=month, results_processed=0, api_calls=0, storage_bytes=0)
        db.session.merge(usage)
    usage.api_calls += n
    db.session.commit()
