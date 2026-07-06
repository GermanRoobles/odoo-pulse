import enum
from datetime import datetime
from sqlalchemy import String, Text, Enum, DateTime, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class LeadStatus(str, enum.Enum):
    nuevo = "nuevo"
    contactado = "contactado"
    en_negociacion = "en_negociacion"
    cliente = "cliente"
    descartado = "descartado"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    odoo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    odoo_db_name: Mapped[str] = mapped_column(String(255), nullable=False)
    odoo_username: Mapped[str] = mapped_column(String(255), nullable=False)
    odoo_credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    lead_status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), default=LeadStatus.nuevo, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")
    sector: Mapped[str] = mapped_column(String(100), nullable=True, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    scans: Mapped[list] = relationship("Scan", back_populates="client", cascade="all, delete-orphan")
