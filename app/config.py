from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "sqlite:///./odoo_pulse.db"
    anthropic_api_key: str = ""
    encryption_master_key: str = ""
    admin_session_secret: str = "dev-secret-change-in-production"
    environment: str = "development"
    allowed_odoo_hosts: Optional[str] = None
    resend_api_key: str = ""
    notification_email: str = "germanroobles@gmail.com"
    app_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()
