# invoice_cron.py
import schedule
import time
from datetime import date, timedelta
from app.billing import generate_invoice_for_all_tenants, save_invoice_to_json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_monthly_invoices():
    """Generate invoices for all tenants for previous month"""
    try:
        # Get first day of previous month
        today = date.today()
        first_day_current = date(today.year, today.month, 1)
        previous_month = first_day_current - timedelta(days=1)
        invoice_month = date(previous_month.year, previous_month.month, 1)
        
        logger.info(f"Generating invoices for {invoice_month.strftime('%Y-%m')}")
        
        invoices = generate_invoice_for_all_tenants(invoice_month)
        
        # Save each invoice
        saved_files = []
        for invoice in invoices:
            if invoice:
                filepath = save_invoice_to_json(invoice)
                saved_files.append(filepath)
        
        logger.info(f"✅ Generated {len(saved_files)} invoices")
        
        # TODO: Send invoices via email
        # send_invoices_by_email(invoices)
        
        return saved_files
        
    except Exception as e:
        logger.error(f"❌ Failed to generate invoices: {e}")
        return []

if __name__ == "__main__":
    # Ejecutar inmediatamente para pruebas
    generate_monthly_invoices()
    
    # Para producción: Programar ejecución el día 1 de cada mes
    # schedule.every().month.at("00:01").do(generate_monthly_invoices)
    
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)