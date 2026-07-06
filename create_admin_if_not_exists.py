import os
import sys

email = os.getenv("ADMIN_EMAIL", "")
password = os.getenv("ADMIN_PASSWORD", "")

if not email or not password:
    print("ADMIN_EMAIL/ADMIN_PASSWORD not set — skipping admin creation.")
    sys.exit(0)

from app.models.client import Client
from app.models.scan import Scan
from app.models.finding import Finding
from app.models.admin_user import AdminUser
from app.models.base import SessionLocal
from app.security.auth import hash_password

db = SessionLocal()
existing = db.query(AdminUser).filter(AdminUser.email == email).first()
if existing:
    print(f"Admin '{email}' already exists — skipping.")
else:
    admin = AdminUser(email=email, password_hash=hash_password(password))
    db.add(admin)
    db.commit()
    print(f"Admin '{email}' created.")
db.close()
