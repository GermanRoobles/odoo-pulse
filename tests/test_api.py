import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.models.base import Base, get_db
from app.models.client import Client
from app.models.scan import Scan
from app.models.finding import Finding
from app.models.admin_user import AdminUser
from app.security.auth import hash_password

# StaticPool forces all sessions to share one connection → shared in-memory DB
# Never touches odoo_pulse.db
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_client(client):
    db = TestSessionLocal()
    admin = AdminUser(email="admin@test.com", password_hash=hash_password("testpass"))
    db.add(admin)
    db.commit()
    db.close()
    client.post("/api/admin/login", json={"email": "admin@test.com", "password": "testpass"})
    return client


def test_landing_page_loads(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Odoo Pulse" in res.text


def test_report_not_found(client):
    res = client.get("/report/nonexistent-token-xyz")
    assert res.status_code == 404


def test_admin_login_wrong_password(client):
    db = TestSessionLocal()
    admin = AdminUser(email="admin2@test.com", password_hash=hash_password("correct"))
    db.add(admin)
    db.commit()
    db.close()
    res = client.post("/api/admin/login", json={"email": "admin2@test.com", "password": "wrong"})
    assert res.status_code == 401


def test_admin_dashboard_unauthenticated(client):
    res = client.get("/admin/dashboard", follow_redirects=False)
    assert res.status_code in (302, 401)


def test_admin_dashboard_authenticated(admin_client):
    res = admin_client.get("/admin/dashboard")
    assert res.status_code == 200


def test_create_lead_connection_failure(client):
    from app.scanner.odoo_client import OdooConnectionError
    with patch("app.api.public.OdooClient") as MockOdoo:
        MockOdoo.return_value.authenticate.side_effect = OdooConnectionError("Timeout")
        res = client.post("/api/leads", json={
            "company_name": "Test Corp",
            "contact_name": "Test User",
            "contact_email": "test@corp.com",
            "odoo_url": "https://test.odoo.com",
            "odoo_db_name": "testdb",
            "odoo_username": "user@test.com",
            "odoo_password": "pass",
        })
        assert res.status_code == 422
        assert "Timeout" in res.json()["detail"]


def test_scan_status_not_found(client):
    res = client.get("/api/scans/99999/status")
    assert res.status_code == 404


def test_admin_clients_requires_auth(client):
    res = client.get("/admin/clients/1", follow_redirects=False)
    assert res.status_code in (302, 401)
