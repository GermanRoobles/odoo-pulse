import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.models.base import get_db, SessionLocal
from app.models.client import Client
from app.models.scan import Scan, ScanStatus
from app.models.finding import Finding
from app.security.crypto import encrypt_credentials, decrypt_credentials
from app.scanner.odoo_client import OdooClient, OdooConnectionError, OdooPermissionError
from app.scanner.checks import run_all_checks
from app.ai.analyzer import analyze_checks, AIAnalysisError
from app.notifications.email import send_new_lead_notification

router = APIRouter()


class LeadRequest(BaseModel):
    company_name: str
    contact_name: str
    contact_email: EmailStr
    odoo_url: str
    odoo_db_name: str
    odoo_username: str
    odoo_password: str
    sector: str = ""


def _run_scan(scan_id: int, db: Session):
    """Background task: connect to Odoo, run checks, analyze with AI, persist results."""
    scan = db.get(Scan, scan_id)
    if not scan:
        db.close()
        return
    client_record = db.get(Client, scan.client_id)
    if not client_record:
        db.close()
        return

    scan.status = ScanStatus.en_progreso
    db.commit()

    try:
        password = decrypt_credentials(client_record.odoo_credentials_encrypted)
        odoo = OdooClient(
            url=client_record.odoo_url,
            db=client_record.odoo_db_name,
            username=client_record.odoo_username,
            password=password,
        )
        odoo.authenticate()
        checks = run_all_checks(odoo)
        scan.raw_checks_json = json.dumps(checks, ensure_ascii=False)

        result = analyze_checks(checks, client_record.company_name, sector=client_record.sector or "")
        scan.ai_response_json = result.model_dump_json()
        scan.score = result.score
        scan.score_label = result.score_label
        scan.summary = result.summary
        scan.status = ScanStatus.completado
        scan.completed_at = datetime.now(timezone.utc)

        for f in result.findings:
            finding = Finding(
                scan_id=scan.id,
                title=f.title,
                description=f.description,
                severity=f.severity,
                estimated_hours_month=f.estimated_hours_month,
                recommended_tool=f.recommended_tool,
                category=f.category,
            )
            db.add(finding)

        db.commit()

        # Notify owner — fire and forget, never block the scan
        try:
            from app.config import settings
            send_new_lead_notification(
                company_name=client_record.company_name,
                contact_name=client_record.contact_name,
                contact_email=client_record.contact_email,
                sector=client_record.sector or "",
                score=result.score,
                score_label=result.score_label,
                summary=result.summary,
                findings=result.findings,
                report_url=f"{settings.app_url}/report/{scan.public_token}",
            )
        except Exception:
            pass  # never fail the scan because of a notification error

    except (OdooConnectionError, OdooPermissionError) as e:
        scan.status = ScanStatus.error
        scan.error_message = str(e)
    except AIAnalysisError as e:
        scan.status = ScanStatus.error
        scan.error_message = f"Error de análisis IA: {str(e)}"
    except Exception as e:
        scan.status = ScanStatus.error
        scan.error_message = f"Error inesperado: {str(e)}"
    finally:
        db.commit()
        db.close()


@router.post("/api/leads")
def create_lead(
    body: LeadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        odoo = OdooClient(
            body.odoo_url, body.odoo_db_name, body.odoo_username, body.odoo_password
        )
        odoo.authenticate()
    except (OdooConnectionError, OdooPermissionError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    encrypted = encrypt_credentials(body.odoo_password)
    client_record = Client(
        company_name=body.company_name,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        odoo_url=body.odoo_url,
        odoo_db_name=body.odoo_db_name,
        odoo_username=body.odoo_username,
        odoo_credentials_encrypted=encrypted,
        sector=body.sector,
    )
    db.add(client_record)
    db.commit()
    db.refresh(client_record)

    scan = Scan(
        client_id=client_record.id,
        status=ScanStatus.pendiente,
        public_token=str(uuid.uuid4()),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    bg_db = SessionLocal()
    background_tasks.add_task(_run_scan, scan.id, bg_db)

    return {
        "scan_id": scan.id,
        "status": scan.status,
        "public_token": scan.public_token,
    }


@router.get("/api/scans/{scan_id}/status")
def get_scan_status(scan_id: int, db: Session = Depends(get_db)):
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Escaneo no encontrado")
    return {
        "status": scan.status,
        "score": scan.score,
        "score_label": scan.score_label,
        "public_token": scan.public_token,
        "error_message": scan.error_message if scan.status == ScanStatus.error else None,
    }


@router.post("/api/scans/{scan_id}/unlock")
def unlock_report(scan_id: int, db: Session = Depends(get_db)):
    """Stub for Fase 2 payment integration — manually unlock a report."""
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Escaneo no encontrado")
    scan.is_paid_report = True
    db.commit()
    return {"ok": True}
