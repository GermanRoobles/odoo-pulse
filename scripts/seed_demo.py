#!/usr/bin/env python3
"""
Seed the demo report for Distribuciones Altaviva.
Idempotent — safe to run multiple times.
Usage: python scripts/seed_demo.py
"""
import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.models.base import Base, engine, SessionLocal
from app.models.client import Client, LeadStatus
from app.models.scan import Scan, ScanStatus
from app.models.finding import Finding
from app.security.crypto import encrypt_credentials

DEMO_TOKEN = "demo-altaviva"

RAW_CHECKS = {
    "sector": "distribucion",
    "checks": [
        {"check_id": "sale_orders_stuck", "raw_metric": 97,
         "context": {"total_orders_90d": 812, "pct": 11.9}, "applicable": True},
        {"check_id": "stock_pickings_overdue", "raw_metric": 26,
         "context": {"total_pending": 145, "pct": 17.9}, "applicable": True},
        {"check_id": "invoices_draft_stuck", "raw_metric": 34,
         "context": {"total_invoices_90d": 430, "pct": 7.9}, "applicable": True},
        {"check_id": "crm_leads_no_followup", "raw_metric": 61,
         "context": {"total_open_leads": 156, "pct": 39.1}, "applicable": True},
        {"check_id": "cron_jobs_status", "raw_metric": 7,
         "context": {"total_crons": 22, "active": 15, "inactive": 7}, "applicable": True},
        {"check_id": "studio_automations", "raw_metric": 5,
         "context": {"models_covered": ["sale.order", "stock.picking"]}, "applicable": True},
        {"check_id": "overdue_activities", "raw_metric": 112,
         "context": {"total_activities": 340, "pct": 32.9}, "applicable": True},
        {"check_id": "partners_incomplete", "raw_metric": 68,
         "context": {"total_partners": 540, "pct": 12.6}, "applicable": True},
        {"check_id": "products_no_barcode", "raw_metric": 186,
         "context": {"total_products": 1240, "pct": 15.0}, "applicable": True},
    ],
}

AI_RESPONSE = {
    "score": 58,
    "score_label": "Automatización parcial — bases sólidas con oportunidades claras",
    "summary": "Distribuciones Altaviva tiene una adopción de Odoo razonable, con automatizaciones activas en ventas y logística, pero el seguimiento comercial y las alertas operativas siguen dependiendo en gran medida de revisión manual. El mayor margen de mejora está en el CRM y en el control de incidencias logísticas.",
    "findings": [
        {
            "title": "CRM sin seguimiento estructurado",
            "description": "El 39% de los leads abiertos no tiene una próxima actividad asignada, lo que significa que se pierden de vista sin que nadie lo note hasta que es tarde. Sin un flujo automático de recordatorio, el equipo comercial depende de acordarse manualmente de cada contacto.",
            "severity": "high",
            "estimated_hours_month": "15-25",
            "recommended_tool": "Make.com + Odoo Studio",
            "category": "crm",
        },
        {
            "title": "18% de envíos con retraso sin alerta",
            "description": "Una parte relevante de los envíos pendientes supera el plazo esperado sin que exista ninguna notificación automática al equipo de logística ni al cliente. Esto genera llamadas reactivas en lugar de gestión proactiva.",
            "severity": "medium",
            "estimated_hours_month": "10-18",
            "recommended_tool": "Odoo Studio",
            "category": "logistica",
        },
        {
            "title": "112 actividades vencidas acumuladas",
            "description": "Un tercio de las actividades registradas en el sistema están vencidas sin resolver, lo que indica que Odoo se está usando parcialmente como repositorio de tareas más que como herramienta activa de gestión diaria.",
            "severity": "medium",
            "estimated_hours_month": "8-12",
            "recommended_tool": "Make.com",
            "category": "operaciones",
        },
        {
            "title": "12% de pedidos de venta estancados en borrador",
            "description": "Casi 100 pedidos de los últimos 90 días permanecen sin confirmar más de una semana, probablemente por falta de un paso de aprobación automatizado o de aviso al responsable.",
            "severity": "medium",
            "estimated_hours_month": "10-15",
            "recommended_tool": "Odoo Studio",
            "category": "ventas",
        },
        {
            "title": "15% del catálogo sin código de barras",
            "description": "Una parte del catálogo activo carece de código de barras, lo que obliga a identificación manual en almacén y aumenta el riesgo de error en picking, aunque el impacto es menor que en los hallazgos anteriores.",
            "severity": "low",
            "estimated_hours_month": "6-10",
            "recommended_tool": "Script Python",
            "category": "catalogo",
        },
        {
            "title": "68 contactos sin email registrado",
            "description": "Un grupo reducido de clientes y proveedores no tiene email registrado, lo que impide incluirlos en comunicaciones automatizadas como confirmaciones o recordatorios de pago.",
            "severity": "low",
            "estimated_hours_month": "4-6",
            "recommended_tool": "Script Python",
            "category": "datos",
        },
    ],
    "quick_win": "Automatizar el seguimiento de leads en CRM: crear una regla en Odoo que asigne automáticamente una próxima actividad al crear un lead, combinada con un recordatorio vía Make.com si no hay respuesta en 48 horas. Recupera visibilidad comercial inmediata con menos de 3 horas de implementación.",
}


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Upsert client
        demo_client = db.query(Client).filter(
            Client.company_name == "Distribuciones Altaviva",
            Client.is_demo == True,
        ).first()

        if not demo_client:
            demo_client = Client(
                company_name="Distribuciones Altaviva",
                contact_name="Demo",
                contact_email="demo@example.com",
                odoo_url="https://demo-instance.invalid",
                odoo_db_name="demo",
                odoo_username="demo@example.com",
                odoo_credentials_encrypted=encrypt_credentials("demo-placeholder"),
                lead_status=LeadStatus.cliente,
                sector="distribucion",
                is_demo=True,
            )
            db.add(demo_client)
            db.flush()
            print(f"Created demo client: {demo_client.company_name}")
        else:
            print(f"Demo client already exists (id={demo_client.id})")

        # Upsert scan
        demo_scan = db.query(Scan).filter(Scan.public_token == DEMO_TOKEN).first()

        if not demo_scan:
            demo_scan = Scan(
                client_id=demo_client.id,
                status=ScanStatus.completado,
                public_token=DEMO_TOKEN,
                score=AI_RESPONSE["score"],
                score_label=AI_RESPONSE["score_label"],
                summary=AI_RESPONSE["summary"],
                raw_checks_json=json.dumps(RAW_CHECKS, ensure_ascii=False),
                ai_response_json=json.dumps(AI_RESPONSE, ensure_ascii=False),
                is_paid_report=True,
                is_demo=True,
                completed_at=datetime.now(timezone.utc),
            )
            db.add(demo_scan)
            db.flush()
            print(f"Created demo scan (token: {DEMO_TOKEN})")
        else:
            # Update content in case it changed
            demo_scan.score = AI_RESPONSE["score"]
            demo_scan.score_label = AI_RESPONSE["score_label"]
            demo_scan.summary = AI_RESPONSE["summary"]
            demo_scan.raw_checks_json = json.dumps(RAW_CHECKS, ensure_ascii=False)
            demo_scan.ai_response_json = json.dumps(AI_RESPONSE, ensure_ascii=False)
            demo_scan.is_paid_report = True
            demo_scan.is_demo = True
            print(f"Updated demo scan (token: {DEMO_TOKEN})")

        # Upsert findings
        existing = db.query(Finding).filter(Finding.scan_id == demo_scan.id).all()
        for f in existing:
            db.delete(f)

        for f in AI_RESPONSE["findings"]:
            db.add(Finding(
                scan_id=demo_scan.id,
                title=f["title"],
                description=f["description"],
                severity=f["severity"],
                estimated_hours_month=f["estimated_hours_month"],
                recommended_tool=f["recommended_tool"],
                category=f["category"],
            ))

        db.commit()
        print(f"\nDemo report ready at: http://localhost:8000/report/{DEMO_TOKEN}")
        print(f"Public link (production): https://yourdomain.com/report/{DEMO_TOKEN}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
