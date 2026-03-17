"""
models/orm.py
SQLAlchemy ORM models — mirrors the Phase 3 PostgreSQL schema exactly.
"""
import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Integer, Numeric, SmallInteger, String, Text, Time,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.database import Base


def new_uuid():
    return str(uuid.uuid4())


# ── Users ────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    user_id            = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    email              = Column(String(255), unique=True, nullable=False, index=True)
    password_hash      = Column(Text, nullable=False)
    full_name          = Column(String(255))
    phone              = Column(String(20))
    date_of_birth      = Column(Date)
    city               = Column(String(100))
    occupation_segment = Column(String(50))
    monthly_income     = Column(Numeric(14, 2), nullable=False, default=0)
    credit_score       = Column(SmallInteger)
    risk_appetite      = Column(String(20), default="moderate")
    is_active          = Column(Boolean, nullable=False, default=True)
    last_login_at      = Column(DateTime(timezone=True))
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    updated_at         = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    transactions  = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    receipts      = relationship("Receipt",     back_populates="user", cascade="all, delete-orphan")
    voice_entries = relationship("VoiceEntry",  back_populates="user", cascade="all, delete-orphan")
    goals         = relationship("Goal",        back_populates="user", cascade="all, delete-orphan")
    budgets       = relationship("Budget",      back_populates="user", cascade="all, delete-orphan")
    predictions   = relationship("Prediction",  back_populates="user", cascade="all, delete-orphan")
    alerts        = relationship("AnomalyAlert",back_populates="user", cascade="all, delete-orphan")
    health_scores = relationship("FinancialHealthScore", back_populates="user", cascade="all, delete-orphan")


# ── Expense Categories ───────────────────────────────────────────────────────
class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    category_id  = Column(Integer, primary_key=True, autoincrement=True)
    name         = Column(String(100), unique=True, nullable=False)
    parent_id    = Column(Integer, ForeignKey("expense_categories.category_id"))
    icon         = Column(String(50))
    color_hex    = Column(String(7))
    is_essential = Column(Boolean, default=False)
    description  = Column(Text)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    subcategories = relationship("ExpenseCategory", backref="parent", remote_side="ExpenseCategory.category_id")
    transactions  = relationship("Transaction", back_populates="category")


# ── Transactions ─────────────────────────────────────────────────────────────
class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id         = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id                = Column(UUID(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    category_id            = Column(Integer, ForeignKey("expense_categories.category_id"))
    date                   = Column(Date, nullable=False, index=True)
    time_of_day            = Column(Time)
    merchant               = Column(String(255), index=True)
    merchant_city          = Column(String(100))
    amount                 = Column(Numeric(14, 2), nullable=False)
    currency               = Column(String(3), default="INR")
    payment_method         = Column(String(50), nullable=False)
    source                 = Column(String(30), default="manual")
    notes                  = Column(Text)
    ai_category            = Column(String(100))
    ai_category_confidence = Column(Numeric(5, 4))
    is_recurring           = Column(Boolean, default=False)
    recurrence_pattern     = Column(String(50))
    is_anomaly             = Column(Boolean, default=False)
    anomaly_score          = Column(Numeric(6, 4))
    receipt_id             = Column(UUID(as_uuid=False), ForeignKey("receipts.receipt_id", ondelete="SET NULL"), nullable=True)
    voice_entry_id         = Column(UUID(as_uuid=False), ForeignKey("voice_entries.voice_entry_id", ondelete="SET NULL"), nullable=True)
    created_at             = Column(DateTime(timezone=True), server_default=func.now())
    updated_at             = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user     = relationship("User",            back_populates="transactions")
    category = relationship("ExpenseCategory", back_populates="transactions")
    alerts   = relationship("AnomalyAlert",    back_populates="transaction")


# ── Receipts ─────────────────────────────────────────────────────────────────
class Receipt(Base):
    __tablename__ = "receipts"

    receipt_id      = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id         = Column(UUID(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id  = Column(UUID(as_uuid=False), ForeignKey("transactions.transaction_id"), nullable=True)
    merchant        = Column(String(255))
    merchant_gstin  = Column(String(20))
    total_amount    = Column(Numeric(14, 2))
    tax_amount      = Column(Numeric(14, 2))
    date            = Column(Date)
    image_url       = Column(Text)
    extracted_text  = Column(Text)
    ocr_engine      = Column(String(50), default="PaddleOCR")
    ocr_confidence  = Column(Numeric(5, 4))
    parse_status    = Column(String(30), default="pending")
    line_items      = Column(JSON)
    payment_mode    = Column(String(50))
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="receipts")


# ── Voice Entries ────────────────────────────────────────────────────────────
class VoiceEntry(Base):
    __tablename__ = "voice_entries"

    voice_entry_id   = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id          = Column(UUID(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id   = Column(UUID(as_uuid=False), ForeignKey("transactions.transaction_id"), nullable=True)
    audio_url        = Column(Text)
    duration_seconds = Column(Numeric(6, 2))
    transcript       = Column(Text)
    stt_engine       = Column(String(50), default="Whisper")
    stt_confidence   = Column(Numeric(5, 4))
    parsed_amount    = Column(Numeric(14, 2))
    parsed_merchant  = Column(String(255))
    parsed_category  = Column(String(100))
    parsed_date      = Column(Date)
    parse_status     = Column(String(30), default="pending")
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="voice_entries")


# ── Goals ────────────────────────────────────────────────────────────────────
class Goal(Base):
    __tablename__ = "goals"

    goal_id          = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id          = Column(UUID(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    goal_name        = Column(String(255), nullable=False)
    goal_category    = Column(String(100))
    target_amount    = Column(Numeric(14, 2), nullable=False)
    current_savings  = Column(Numeric(14, 2), nullable=False, default=0)
    deadline_months  = Column(Integer, nullable=False)
    priority         = Column(String(20), default="medium")
    status           = Column(String(30), default="active")
    notes            = Column(Text)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="goals")


# ── Budgets ──────────────────────────────────────────────────────────────────
class Budget(Base):
    __tablename__ = "budgets"

    budget_id             = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id               = Column(UUID(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    category_id           = Column(Integer, ForeignKey("expense_categories.category_id"))
    month                 = Column(Date, nullable=False)
    allocated_amount      = Column(Numeric(14, 2), nullable=False)
    spent_amount          = Column(Numeric(14, 2), default=0)
    ai_recommended_amount = Column(Numeric(14, 2))
    rl_model_version      = Column(String(50))
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user     = relationship("User", back_populates="budgets")
    category = relationship("ExpenseCategory")


# ── Predictions ──────────────────────────────────────────────────────────────
class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id    = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id          = Column(UUID(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_type  = Column(String(60), nullable=False)
    prediction_value = Column(JSON, nullable=False)
    model_used       = Column(String(100), nullable=False)
    model_version    = Column(String(50))
    horizon_days     = Column(Integer)
    confidence_score = Column(Numeric(5, 4))
    feature_hash     = Column(Text)
    valid_until      = Column(DateTime(timezone=True))
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="predictions")


# ── Anomaly Alerts ────────────────────────────────────────────────────────────
class AnomalyAlert(Base):
    __tablename__ = "anomaly_alerts"

    alert_id        = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id         = Column(UUID(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id  = Column(UUID(as_uuid=False), ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    alert_type      = Column(String(50), nullable=False)
    severity        = Column(String(20), default="medium")
    anomaly_score   = Column(Numeric(6, 4))
    description     = Column(Text)
    model_used      = Column(String(100))
    model_version   = Column(String(50))
    status          = Column(String(30), default="open")
    shap_values     = Column(JSON)
    resolved_at     = Column(DateTime(timezone=True))
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user        = relationship("User",        back_populates="alerts")
    transaction = relationship("Transaction", back_populates="alerts")


# ── Financial Health Scores ───────────────────────────────────────────────────
class FinancialHealthScore(Base):
    __tablename__ = "financial_health_scores"

    score_id         = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id          = Column(UUID(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    score_date       = Column(Date, nullable=False)
    overall_score    = Column(Numeric(5, 2), nullable=False)
    sub_scores       = Column(JSON, nullable=False)
    score_band       = Column(String(20))
    model_version    = Column(String(50))
    shap_explanation = Column(JSON)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="health_scores")
