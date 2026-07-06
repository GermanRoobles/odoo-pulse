# Odoo Pulse

Herramienta de auditoría automática para instancias Odoo. Se conecta en modo solo lectura,
analiza procesos con IA y genera un informe con puntuación de madurez de automatización,
hallazgos priorizados y estimación de horas ahorrables.

## Requisitos

- Python 3.11+

## Instalación y puesta en marcha

### 1. Crear entorno virtual e instalar dependencias

```bash
cd /Applications/MAMP/htdocs/OdooPulse
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env`:

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | SQLite por defecto. MySQL en producción: `mysql+pymysql://user:pass@host/db` |
| `ANTHROPIC_API_KEY` | API key de Anthropic (Claude) |
| `ENCRYPTION_MASTER_KEY` | Clave Fernet. Generar con: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `ADMIN_SESSION_SECRET` | String aleatorio para firmar cookies de sesión admin |
| `ENVIRONMENT` | `development` (permite URLs locales) o `production` |

### 3. Crear primer administrador

```bash
python create_admin.py
```

### 4. Arrancar el servidor

```bash
uvicorn app.main:app --reload --port 8000
```

- Landing pública: http://localhost:8000
- Panel admin: http://localhost:8000/admin

## Tests

```bash
pytest tests/ -v
```

## Estructura del proyecto

```
app/
  main.py              # Entrypoint FastAPI
  config.py            # Variables de entorno (pydantic-settings)
  models/              # SQLAlchemy models (clients, scans, findings, admin_users)
  scanner/             # Conector XML-RPC + 9 checks independientes
  ai/                  # Integración Claude API + validación Pydantic
  api/                 # Endpoints REST (públicos y admin)
  views/               # Rutas de páginas HTML (Jinja2)
  security/            # Cifrado Fernet + autenticación de sesión
  templates/           # HTML templates
static/
  css/base.css         # Sistema de diseño oscuro (Space Grotesk + teal)
  js/app.js
tests/                 # Tests unitarios pytest
create_admin.py        # CLI para crear el primer admin
alembic/               # Migraciones de base de datos
```

## Flujo completo

1. El cliente potencial rellena el formulario en `/`
2. El backend valida la conexión Odoo y lanza el escaneo en background
3. El frontend hace polling a `/api/scans/{id}/status` cada 3 segundos
4. Al completar, redirige a `/report/{token}` — informe público sin login
5. Germán ve el lead en `/admin/dashboard`, actualiza el estado y copia el link

## Monetización (MVP)

- Informes nuevos muestran solo 1 hallazgo + CTA (modo teaser)
- Germán desbloquea el informe completo desde el panel admin tras cobrar
- `POST /api/scans/{id}/unlock` — stub preparado para Stripe en Fase 2

## Despliegue en producción

1. Usar MySQL en `DATABASE_URL`
2. `ENVIRONMENT=production`
3. Nginx + uvicorn con HTTPS obligatorio
4. Ejecutar migraciones: `alembic upgrade head`
5. Generar `ENCRYPTION_MASTER_KEY` única, guardar fuera del repositorio

## Fase 2 (no implementado)

- Integración Stripe (estructura ya preparada)
- Re-escaneos periódicos automáticos
- Multi-usuario (tabla `admin_users` ya creada)
