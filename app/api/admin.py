from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from app.models.base import get_db
from app.models.client import Client, LeadStatus
from app.models.scan import Scan, ScanStatus
from app.models.admin_user import AdminUser
from app.security.auth import verify_password, create_session_token, verify_session_token

router = APIRouter(prefix="/api/admin")
SESSION_COOKIE = "op_admin_session"


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    data = verify_session_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    user = db.get(AdminUser, data["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateClientRequest(BaseModel):
    lead_status: Optional[LeadStatus] = None
    notes: Optional[str] = None


@router.post("/login")
def admin_login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = create_session_token(user.id)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
    return {"ok": True}


@router.post("/logout")
def admin_logout(response: Response):
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/dashboard")
def dashboard(
    request: Request,
    lead_status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    query = db.query(Client)
    query = query.filter(Client.is_demo == False)
    if lead_status:
        try:
            query = query.filter(Client.lead_status == LeadStatus(lead_status))
        except ValueError:
            pass
    clients = query.order_by(desc(Client.created_at)).all()

    result = []
    for c in clients:
        latest_scan = (
            db.query(Scan)
            .filter(Scan.client_id == c.id)
            .order_by(desc(Scan.created_at))
            .first()
        )
        result.append({
            "id": c.id,
            "company_name": c.company_name,
            "contact_name": c.contact_name,
            "contact_email": c.contact_email,
            "lead_status": c.lead_status,
            "created_at": c.created_at.isoformat(),
            "latest_scan": {
                "id": latest_scan.id,
                "status": latest_scan.status,
                "score": latest_scan.score,
                "score_label": latest_scan.score_label,
                "public_token": latest_scan.public_token,
                "created_at": latest_scan.created_at.isoformat(),
            } if latest_scan else None,
        })
    return result


@router.get("/clients/{client_id}")
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    scans = (
        db.query(Scan)
        .filter(Scan.client_id == c.id)
        .order_by(desc(Scan.created_at))
        .all()
    )
    return {
        "id": c.id,
        "company_name": c.company_name,
        "contact_name": c.contact_name,
        "contact_email": c.contact_email,
        "odoo_url": c.odoo_url,
        "odoo_db_name": c.odoo_db_name,
        "odoo_username": c.odoo_username,
        "lead_status": c.lead_status,
        "notes": c.notes,
        "created_at": c.created_at.isoformat(),
        "scans": [
            {
                "id": s.id,
                "status": s.status,
                "score": s.score,
                "score_label": s.score_label,
                "public_token": s.public_token,
                "is_paid_report": s.is_paid_report,
                "created_at": s.created_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "error_message": s.error_message,
            }
            for s in scans
        ],
    }


@router.patch("/clients/{client_id}")
def update_client(
    client_id: int,
    body: UpdateClientRequest,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if body.lead_status is not None:
        c.lead_status = body.lead_status
    if body.notes is not None:
        c.notes = body.notes
    db.commit()
    return {"ok": True}


@router.post("/scans/{scan_id}/rerun")
def rerun_scan_ai(
    scan_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """Re-run the full scan (re-connects to Odoo + re-runs AI analysis)."""
    from app.api.public import _run_scan
    from app.models.base import SessionLocal
    from concurrent.futures import ThreadPoolExecutor

    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Escaneo no encontrado")

    scan.status = ScanStatus.pendiente
    scan.error_message = None
    db.commit()

    bg_db = SessionLocal()
    with ThreadPoolExecutor() as executor:
        executor.submit(_run_scan, scan.id, bg_db)

    return {"ok": True, "scan_id": scan.id}


@router.delete("/clients/{client_id}")
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    db.delete(c)
    db.commit()
    return {"ok": True}
