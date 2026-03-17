"""
schemas/schemas.py
Pydantic v2 request/response models for all API endpoints.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ── Shared base ──────────────────────────────────────────────────────────────
class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════════════
class RegisterRequest(BaseModel):
    email:             EmailStr
    password:          str       = Field(min_length=8, max_length=128)
    full_name:         Optional[str] = None
    phone:             Optional[str] = None
    monthly_income:    Decimal   = Field(ge=0)
    city:              Optional[str] = None
    occupation_segment: Optional[str] = None
    risk_appetite:     Optional[str] = "moderate"

    @field_validator("occupation_segment")
    @classmethod
    def valid_segment(cls, v):
        allowed = {None, "student", "junior_prof", "mid_prof", "senior_prof", "self_employed", "retiree"}
        if v not in allowed:
            raise ValueError(f"occupation_segment must be one of {allowed - {None}}")
        return v


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int   # seconds


class UserProfileResponse(OrmBase):
    user_id:            str
    email:              str
    full_name:          Optional[str]
    phone:              Optional[str]
    city:               Optional[str]
    occupation_segment: Optional[str]
    monthly_income:     Decimal
    credit_score:       Optional[int]
    risk_appetite:      Optional[str]
    is_active:          bool
    created_at:         datetime


class UserUpdateRequest(BaseModel):
    full_name:         Optional[str] = None
    phone:             Optional[str] = None
    city:              Optional[str] = None
    monthly_income:    Optional[Decimal] = None
    risk_appetite:     Optional[str] = None
    credit_score:      Optional[int] = Field(None, ge=300, le=900)


# ════════════════════════════════════════════════════════════════
#  TRANSACTIONS
# ════════════════════════════════════════════════════════════════
class TransactionCreate(BaseModel):
    date:           date
    merchant:       str           = Field(max_length=255)
    amount:         Decimal       = Field(gt=0)
    payment_method: str
    category_id:    Optional[int] = None
    notes:          Optional[str] = None
    source:         str           = "manual"
    time_of_day:    Optional[str] = None   # "HH:MM"
    merchant_city:  Optional[str] = None
    currency:       str           = "INR"

    @field_validator("payment_method")
    @classmethod
    def valid_payment(cls, v):
        allowed = {"UPI", "Credit Card", "Debit Card", "Net Banking", "Cash", "Wallet", "Other"}
        if v not in allowed:
            raise ValueError(f"payment_method must be one of {allowed}")
        return v


class TransactionResponse(OrmBase):
    transaction_id:          str
    user_id:                 str
    date:                    date
    merchant:                Optional[str]
    amount:                  Decimal
    payment_method:          str
    source:                  str
    ai_category:             Optional[str]
    ai_category_confidence:  Optional[Decimal]
    is_recurring:            bool
    is_anomaly:              bool
    anomaly_score:           Optional[Decimal]
    category_id:             Optional[int]
    notes:                   Optional[str]
    created_at:              datetime


class TransactionListResponse(BaseModel):
    items:   list[TransactionResponse]
    total:   int
    page:    int
    size:    int
    pages:   int


class TransactionFilters(BaseModel):
    start_date:    Optional[date]  = None
    end_date:      Optional[date]  = None
    category_id:   Optional[int]   = None
    payment_method: Optional[str]  = None
    is_anomaly:    Optional[bool]  = None
    min_amount:    Optional[Decimal] = None
    max_amount:    Optional[Decimal] = None
    page:          int             = Field(1, ge=1)
    size:          int             = Field(20, ge=1, le=100)


# ════════════════════════════════════════════════════════════════
#  RECEIPTS
# ════════════════════════════════════════════════════════════════
class ReceiptResponse(OrmBase):
    receipt_id:     str
    user_id:        str
    merchant:       Optional[str]
    total_amount:   Optional[Decimal]
    date:           Optional[date]
    parse_status:   str
    ocr_engine:     Optional[str]
    ocr_confidence: Optional[Decimal]
    line_items:     Optional[list[dict]]
    image_url:      Optional[str]
    created_at:     datetime


class ReceiptOCRResult(BaseModel):
    receipt_id:    str
    merchant:      Optional[str]
    total_amount:  Optional[Decimal]
    date:          Optional[date]
    line_items:    list[dict]
    raw_text:      str
    confidence:    Optional[float]


# ════════════════════════════════════════════════════════════════
#  VOICE ENTRIES
# ════════════════════════════════════════════════════════════════
class VoiceEntryResponse(OrmBase):
    voice_entry_id:  str
    user_id:         str
    transcript:      Optional[str]
    parsed_amount:   Optional[Decimal]
    parsed_merchant: Optional[str]
    parsed_category: Optional[str]
    parsed_date:     Optional[date]
    parse_status:    str
    stt_confidence:  Optional[Decimal]
    created_at:      datetime


class VoiceParseResult(BaseModel):
    transcript:   str
    amount:       Optional[Decimal]
    merchant:     Optional[str]
    category:     Optional[str]
    date:         Optional[date]
    confidence:   Optional[float]


# ════════════════════════════════════════════════════════════════
#  GOALS
# ════════════════════════════════════════════════════════════════
class GoalCreate(BaseModel):
    goal_name:      str     = Field(max_length=255)
    goal_category:  Optional[str] = None
    target_amount:  Decimal = Field(gt=0)
    current_savings: Decimal = Field(ge=0, default=Decimal("0"))
    deadline_months: int    = Field(gt=0)
    priority:       str     = "medium"
    notes:          Optional[str] = None

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v not in {"high", "medium", "low"}:
            raise ValueError("priority must be high, medium, or low")
        return v


class GoalResponse(OrmBase):
    goal_id:         str
    user_id:         str
    goal_name:       str
    goal_category:   Optional[str]
    target_amount:   Decimal
    current_savings: Decimal
    deadline_months: int
    priority:        str
    status:          str
    created_at:      datetime


class GoalProgressResponse(BaseModel):
    goal_id:          str
    goal_name:        str
    target_amount:    Decimal
    current_savings:  Decimal
    progress_pct:     float       # 0.0 – 1.0
    monthly_required: Decimal
    months_remaining: int
    on_track:         bool
    projected_completion_months: Optional[int]


# ════════════════════════════════════════════════════════════════
#  BUDGET
# ════════════════════════════════════════════════════════════════
class BudgetRecommendation(BaseModel):
    category:             str
    category_id:          int
    current_spend_avg:    Decimal
    recommended_budget:   Decimal
    ai_suggested_budget:  Decimal
    utilisation_pct:      float
    saving_opportunity:   Decimal
    insight:              str


class BudgetRecommendationsResponse(BaseModel):
    user_id:         str
    month:           str              # "YYYY-MM"
    total_income:    Decimal
    total_allocated: Decimal
    total_spend:     Decimal
    recommendations: list[BudgetRecommendation]
    model_version:   str


# ════════════════════════════════════════════════════════════════
#  PREDICTIONS / FORECAST
# ════════════════════════════════════════════════════════════════
class CategoryForecast(BaseModel):
    category:          str
    current_month:     Decimal
    forecast_amount:   Decimal
    change_pct:        float
    confidence:        float


class ForecastResponse(BaseModel):
    user_id:           str
    forecast_month:    str        # "YYYY-MM"
    total_forecast:    Decimal
    previous_total:    Decimal
    change_pct:        float
    by_category:       list[CategoryForecast]
    model_used:        str
    confidence:        float
    generated_at:      datetime


# ════════════════════════════════════════════════════════════════
#  ANOMALY ALERTS
# ════════════════════════════════════════════════════════════════
class AnomalyAlertResponse(OrmBase):
    alert_id:       str
    user_id:        str
    transaction_id: str
    alert_type:     str
    severity:       str
    anomaly_score:  Optional[Decimal]
    description:    Optional[str]
    status:         str
    shap_values:    Optional[dict]
    created_at:     datetime

    # Joined transaction fields
    txn_amount:      Optional[Decimal] = None
    txn_merchant:    Optional[str]     = None
    txn_date:        Optional[date]    = None
    txn_payment:     Optional[str]     = None


class AlertUpdateRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in {"acknowledged", "resolved", "false_positive"}:
            raise ValueError("status must be acknowledged, resolved, or false_positive")
        return v


# ════════════════════════════════════════════════════════════════
#  FINANCIAL HEALTH SCORE
# ════════════════════════════════════════════════════════════════
class HealthSubScores(BaseModel):
    savings_rate:        float   # 0–100
    expense_control:     float
    goal_progress:       float
    debt_ratio:          float
    investment_diversity: float


class FinancialHealthResponse(BaseModel):
    user_id:         str
    score_date:      date
    overall_score:   float
    score_band:      str        # Excellent / Good / Fair / Poor
    sub_scores:      HealthSubScores
    top_insights:    list[str]  # NL explanations from SHAP
    previous_score:  Optional[float]
    score_delta:     Optional[float]
    model_version:   str
    generated_at:    datetime


# ════════════════════════════════════════════════════════════════
#  GENERIC
# ════════════════════════════════════════════════════════════════
class MessageResponse(BaseModel):
    message: str
    detail:  Optional[Any] = None


class ErrorResponse(BaseModel):
    error:   str
    detail:  Optional[Any] = None
    code:    Optional[int] = None
