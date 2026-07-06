import enum
from datetime import datetime
from sqlalchemy import String, Text, Enum, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ScanStatus(str, enum.Enum):
    pendiente = "pendiente"
    en_progreso = "en_progreso"
    completado = "completado"
    error = "error"


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id"), nullable=False)
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus), default=ScanStatus.pendiente, nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=True)
    score_label: Mapped[str] = mapped_column(String(100), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    raw_checks_json: Mapped[str] = mapped_column(Text, nullable=True)
    ai_response_json: Mapped[str] = mapped_column(Text, nullable=True)
    public_token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_paid_report: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    client: Mapped["Client"] = relationship("Client", back_populates="scans")
    findings: Mapped[list] = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
