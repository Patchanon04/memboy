import os
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

ENGINE = create_engine(os.environ.get("DATABASE_URL", "sqlite:///data/dev.db"))


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    line_user_id: Mapped[str] = mapped_column(String(64), unique=True)
    active_profile_id: Mapped[int | None] = mapped_column(ForeignKey("profiles.id"), nullable=True)


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(120))


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"))
    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft | confirmed
    doc_type: Mapped[str] = mapped_column(String(16), default="receipt")  # receipt | transfer_slip
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    vendor: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    subtotal: Mapped[float | None] = mapped_column(Float, nullable=True)
    vat: Mapped[float | None] = mapped_column(Float, nullable=True)
    total: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="THB")
    fx_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_thb: Mapped[float | None] = mapped_column(Float, nullable=True)
    transfer_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payee: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_status: Mapped[str | None] = mapped_column(String(12), nullable=True)  # verified | mismatch | unverified
    reimbursed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_llm: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(12))  # user | model | tool
    content: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(60))


class VendorPref(Base):
    """Learned from user corrections: next time this vendor shows up, apply the same category/profile."""
    __tablename__ = "vendor_prefs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    vendor_key: Mapped[str] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("profiles.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProcessedEvent(Base):
    __tablename__ = "processed_events"  # webhook idempotency (LINE redelivers on retry)
    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(ENGINE)


def session() -> Session:
    return Session(ENGINE)
