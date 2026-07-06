from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json
from pathlib import Path
from app.models.base import get_db
from app.models.scan import Scan, ScanStatus
from app.models.finding import Finding
from app.models.admin_user import AdminUser
from app.security.auth import verify_session_token

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
router = APIRouter()
SESSION_COOKIE = "op_admin_session"


def _get_admin_or_none(request: Request, db: Session):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    data = verify_session_token(token)
    if not data:
        return None
    return db.get(AdminUser, data["user_id"])


@router.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse(request, "landing.html")


@router.get("/report/{public_token}", response_class=HTMLResponse)
def public_report(public_token: str, request: Request, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.public_token == public_token).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    if scan.status != ScanStatus.completado:
        return templates.TemplateResponse(request, "report_pending.html", {
            "scan_id": scan.id,
            "status": scan.status,
            "error_message": scan.error_message,
        })
    findings = db.query(Finding).filter(Finding.scan_id == scan.id).all()
    ai_data = json.loads(scan.ai_response_json) if scan.ai_response_json else {}
    is_teaser = not scan.is_paid_report

    # Compute summary stats — estimated_hours_month is a string like "10-18" or "8"
    def _parse_hours(val: str) -> int:
        try:
            parts = str(val).split("-")
            return int(parts[0].strip())
        except Exception:
            return 0

    total_hours = sum(_parse_hours(f.estimated_hours_month) for f in findings)
    high_count = sum(1 for f in findings if f.severity == "high")

    return templates.TemplateResponse(request, "report.html", {
        "scan": scan,
        "client": scan.client,
        "findings": findings,
        "all_findings_count": len(findings),
        "teaser_from": 1 if is_teaser else len(findings),
        "quick_win": ai_data.get("quick_win", ""),
        "is_teaser": is_teaser,
        "total_hours": total_hours,
        "high_count": high_count,
    })


@router.get("/admin", response_class=HTMLResponse)
@router.get("/admin/", response_class=HTMLResponse)
def admin_home(request: Request, db: Session = Depends(get_db)):
    admin = _get_admin_or_none(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)
    return RedirectResponse("/admin/dashboard", status_code=302)


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse(request, "admin_login.html")


@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    admin = _get_admin_or_none(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)
    return templates.TemplateResponse(request, "admin_dashboard.html", {
        "admin_email": admin.email,
    })


@router.get("/admin/clients/{client_id}", response_class=HTMLResponse)
def admin_client_detail(client_id: int, request: Request, db: Session = Depends(get_db)):
    admin = _get_admin_or_none(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)
    from app.models.client import Client
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    scans = (
        db.query(Scan)
        .filter(Scan.client_id == c.id)
        .order_by(desc(Scan.created_at))
        .all()
    )
    return templates.TemplateResponse(request, "admin_client.html", {
        "client": c,
        "scans": scans,
        "admin_email": admin.email,
        "lead_statuses": ["nuevo", "contactado", "en_negociacion", "cliente", "descartado"],
    })
