"""
api/routes/transactions.py
POST /add-transaction  GET /transactions  DELETE /transaction/{id}
GET /transactions/categories  GET /transactions/monthly-summary
GET /transactions/category-breakdown
"""
import math
from typing import Annotated, Optional
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import CurrentUser
from db.database import get_db
from models.orm import ExpenseCategory, Transaction
from schemas.schemas import (
    MessageResponse, TransactionCreate, TransactionFilters,
    TransactionListResponse, TransactionResponse,
)
from services.transaction_service import create_transaction, delete_transaction, list_transactions

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/add-transaction", response_model=TransactionResponse, status_code=201)
async def add_transaction(
    payload: TransactionCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    txn = await create_transaction(
        db, current_user.user_id, payload,
        monthly_income=float(current_user.monthly_income or 50000),
    )
    return TransactionResponse.model_validate(txn)


# Also support POST /transactions (frontend uses this)
@router.post("", response_model=TransactionResponse, status_code=201)
async def add_transaction_v2(
    payload: TransactionCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    txn = await create_transaction(
        db, current_user.user_id, payload,
        monthly_income=float(current_user.monthly_income or 50000),
    )
    return TransactionResponse.model_validate(txn)


@router.get("", response_model=TransactionListResponse)
async def get_transactions(
    current_user: CurrentUser,
    db:           Annotated[AsyncSession, Depends(get_db)],
    start_date:   Optional[date]    = Query(None),
    end_date:     Optional[date]    = Query(None),
    category_id:  Optional[int]     = Query(None),
    payment_method: Optional[str]   = Query(None),
    is_anomaly:   Optional[bool]    = Query(None),
    min_amount:   Optional[Decimal] = Query(None),
    max_amount:   Optional[Decimal] = Query(None),
    page:         int               = Query(1, ge=1),
    size:         int               = Query(20, ge=1, le=100),
    limit:        Optional[int]     = Query(None),
    search:       Optional[str]     = Query(None),
    category:     Optional[str]     = Query(None),
):
    effective_size = limit or size
    filters = TransactionFilters(
        start_date=start_date, end_date=end_date,
        category_id=category_id, payment_method=payment_method,
        is_anomaly=is_anomaly, min_amount=min_amount, max_amount=max_amount,
        page=page, size=effective_size,
    )
    items, total = await list_transactions(db, current_user.user_id, filters)
    pages = math.ceil(total / effective_size) if effective_size else 1
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in items],
        total=total, page=page, size=effective_size, pages=pages,
    )


@router.delete("/transaction/{transaction_id}", response_model=MessageResponse)
async def delete_txn(
    transaction_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted = await delete_transaction(db, current_user.user_id, transaction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return MessageResponse(message="Transaction deleted successfully")


@router.delete("/{transaction_id}", response_model=MessageResponse)
async def delete_txn_v2(
    transaction_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted = await delete_transaction(db, current_user.user_id, transaction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return MessageResponse(message="Transaction deleted successfully")


@router.get("/categories")
async def list_categories(db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser):
    rows = (await db.execute(select(ExpenseCategory.name).order_by(ExpenseCategory.name))).scalars().all()
    if not rows:
        return ["Food & Dining", "Transport", "Shopping", "Bills & Utilities",
                "Entertainment", "Healthcare", "Education", "Finance & EMI", "Other"]
    return rows


@router.get("/monthly-summary")
async def monthly_summary(current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    q = select(
        func.date_trunc("month", Transaction.date).label("month"),
        func.sum(Transaction.amount).label("total"),
    ).where(Transaction.user_id == current_user.user_id
    ).group_by("month").order_by("month")
    rows = (await db.execute(q)).all()
    return [{"month": str(r.month)[:7], "total": float(r.total)} for r in rows]


@router.get("/category-breakdown")
async def category_breakdown(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    months: int = Query(1, ge=1, le=12),
):
    from datetime import timedelta
    from date import date as _date
    cutoff = _date.today() - timedelta(days=30 * months)
    q = select(
        ExpenseCategory.name.label("category"),
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.transaction_id).label("count"),
    ).join(ExpenseCategory, Transaction.category_id == ExpenseCategory.category_id
    ).where(Transaction.user_id == current_user.user_id, Transaction.date >= cutoff
    ).group_by(ExpenseCategory.name)
    rows = (await db.execute(q)).all()
    return [{"category": r.category, "total": float(r.total), "count": r.count} for r in rows]
