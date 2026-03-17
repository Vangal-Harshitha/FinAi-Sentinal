"""
services/transaction_service.py
Full transaction lifecycle: create → categorize → anomaly → store
"""
from __future__ import annotations
import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.orm import AnomalyAlert, ExpenseCategory, Transaction
from schemas.schemas import TransactionCreate, TransactionFilters

logger = logging.getLogger("finai.transaction_service")


# ── Public API ────────────────────────────────────────────────────────────────

async def create_transaction(
    db: AsyncSession,
    user_id: str,
    payload: TransactionCreate,
    monthly_income: float = 50000.0,
) -> Transaction:
    """
    Full pipeline:
      1. Persist transaction skeleton
      2. AI categorisation (FinBERT / keyword fallback)
      3. Anomaly detection (IsolationForest / rule-based)
      4. Update transaction fields
      5. Create AnomalyAlert if flagged
    """
    # Step 1: build ORM object
    txn = Transaction(
        user_id        = user_id,
        date           = payload.date,
        merchant       = payload.merchant,
        amount         = payload.amount,
        currency       = payload.currency,
        payment_method = payload.payment_method,
        notes          = payload.notes,
        source         = payload.source,
        merchant_city  = payload.merchant_city,
    )
    db.add(txn)
    await db.flush()  # get transaction_id

    # Step 2: AI categorisation
    try:
        from services.ai_service import classify_transaction
        category_label, confidence = await classify_transaction(
            merchant=payload.merchant,
            amount=float(payload.amount),
        )
        txn.ai_category             = category_label
        txn.ai_category_confidence  = Decimal(str(round(confidence, 4)))

        # Resolve category_id from label
        if payload.category_id:
            txn.category_id = payload.category_id
        else:
            cat_row = await db.execute(
                select(ExpenseCategory).where(ExpenseCategory.name == category_label)
            )
            cat = cat_row.scalar_one_or_none()
            if cat:
                txn.category_id = cat.category_id
    except Exception as e:
        logger.warning(f"Categorisation failed for txn {txn.transaction_id}: {e}")

    # Step 3: Anomaly detection
    try:
        from services.ml_registry import model_registry
        features = {
            "amount":           float(payload.amount),
            "monthly_income":   monthly_income,
            "merchant":         payload.merchant or "",
            "payment_method":   payload.payment_method,
        }
        result = model_registry.detect_anomaly(features)
        txn.is_anomaly    = result.get("is_anomaly", False)
        txn.anomaly_score = Decimal(str(result.get("score", 0.0)))

        if txn.is_anomaly:
            alert = AnomalyAlert(
                user_id        = user_id,
                transaction_id = txn.transaction_id,
                alert_type     = "unusual_amount",
                severity       = result.get("severity", "medium"),
                anomaly_score  = txn.anomaly_score,
                description    = (
                    f"Transaction of ₹{payload.amount} at {payload.merchant} "
                    "flagged as anomalous by AI model."
                ),
                model_used     = "IsolationForest_v1",
                model_version  = "1.0",
                status         = "open",
            )
            db.add(alert)
            logger.info(f"🚨 Anomaly alert created for txn {txn.transaction_id}")
    except Exception as e:
        logger.warning(f"Anomaly detection failed for txn {txn.transaction_id}: {e}")

    await db.flush()
    await db.refresh(txn)
    logger.info(
        f"✅ Transaction {txn.transaction_id} created "
        f"(category={txn.ai_category}, anomaly={txn.is_anomaly})"
    )
    return txn


async def list_transactions(
    db: AsyncSession,
    user_id: str,
    filters: TransactionFilters,
) -> tuple[list[Transaction], int]:
    q = select(Transaction).where(Transaction.user_id == user_id)

    if filters.start_date:
        q = q.where(Transaction.date >= filters.start_date)
    if filters.end_date:
        q = q.where(Transaction.date <= filters.end_date)
    if filters.category_id:
        q = q.where(Transaction.category_id == filters.category_id)
    if filters.payment_method:
        q = q.where(Transaction.payment_method == filters.payment_method)
    if filters.is_anomaly is not None:
        q = q.where(Transaction.is_anomaly == filters.is_anomaly)
    if filters.min_amount:
        q = q.where(Transaction.amount >= filters.min_amount)
    if filters.max_amount:
        q = q.where(Transaction.amount <= filters.max_amount)

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total   = (await db.execute(count_q)).scalar_one()

    # Paginate
    offset = (filters.page - 1) * filters.size
    q = q.order_by(Transaction.date.desc(), Transaction.created_at.desc())
    q = q.offset(offset).limit(filters.size)

    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def delete_transaction(db: AsyncSession, user_id: str, transaction_id: str) -> bool:
    row = await db.execute(
        select(Transaction).where(
            Transaction.transaction_id == transaction_id,
            Transaction.user_id == user_id,
        )
    )
    txn = row.scalar_one_or_none()
    if not txn:
        return False
    await db.delete(txn)
    await db.flush()
    return True
