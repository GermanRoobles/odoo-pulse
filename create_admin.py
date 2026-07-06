#!/usr/bin/env python3
"""
Utility to create an admin user for the Odoo Pulse panel.
Usage: python create_admin.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.models.base import Base, engine, SessionLocal
from app.models.admin_user import AdminUser
from app.security.auth import hash_password


def main():
    print("=== Crear usuario administrador de Odoo Pulse ===\n")
    email = input("Email: ").strip()
    if not email:
        print("Email requerido.")
        sys.exit(1)
    import getpass
    password = getpass.getpass("Contraseña: ")
    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.")
        sys.exit(1)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    existing = db.query(AdminUser).filter(AdminUser.email == email).first()
    if existing:
        print(f"Ya existe un usuario con ese email.")
        db.close()
        sys.exit(1)

    admin = AdminUser(email=email, password_hash=hash_password(password))
    db.add(admin)
    db.commit()
    db.close()
    print(f"\nAdministrador creado correctamente: {email}")


if __name__ == "__main__":
    main()
