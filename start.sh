#!/bin/bash
set -e

echo "==> Initializing database tables..."
python -c "
from app.models.client import Client
from app.models.scan import Scan
from app.models.finding import Finding
from app.models.admin_user import AdminUser
from app.models.base import Base, engine
Base.metadata.create_all(bind=engine)
print('Tables ready.')
"

echo "==> Seeding demo data..."
python scripts/seed_demo.py

echo "==> Creating admin user if needed..."
python create_admin_if_not_exists.py

echo "==> Starting server on port ${PORT:-8000}..."
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
