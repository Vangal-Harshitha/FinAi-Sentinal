"""
api/routes/receipts.py — OCR Receipt upload & history
"""

import os
import uuid
import aiofiles

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import CurrentUser
from db.database import get_db
from models.orm import Receipt, Transaction
from schemas.schemas import ReceiptResponse
from core.config import get_settings


router = APIRouter(prefix="/receipts", tags=["Receipts"])
settings = get_settings()

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}


@router.post("/upload", status_code=201)
async def upload_receipt(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    force_engine: str = Form("auto"),
):

    ext = os.path.splitext(file.filename or "")[1].lower()

    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(upload_dir, filename)

    # Save uploaded file
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(await file.read())

    # Default OCR result
    ocr_result = {
        "merchant": None,
        "total": None,
        "date": None,
        "category": None,
        "text": "",
        "confidence": 0.5,
    }

    try:
        from services.ocr_service import process_receipt
        ocr_result = await process_receipt(filepath, engine=force_engine)
    except Exception as e:
        print("OCR ERROR:", e)

    merchant = ocr_result.get("merchant") or "Unknown merchant"
    total = ocr_result.get("total")
    date_val = ocr_result.get("date")
    category = ocr_result.get("category") or "Other"
    confidence = ocr_result.get("confidence", 0.9)

    # Convert date properly
    txn_date = date_val if date_val else datetime.utcnow().date()

    # ─────────────────────
    # SAVE RECEIPT
    # ─────────────────────

    receipt = Receipt(
        user_id=current_user.user_id,
        merchant=merchant,
        total_amount=total,
        date=date_val,
        image_url=f"/uploads/{filename}",
        extracted_text=ocr_result.get("text", ""),
        ocr_engine="Tesseract",
        ocr_confidence=confidence,
        parse_status="parsed" if total else "partial",
    )

    db.add(receipt)

    await db.flush()
    await db.refresh(receipt)

    # ─────────────────────
    # CREATE TRANSACTION
    # ─────────────────────

    if total:

        txn = Transaction(
            user_id=current_user.user_id,
            amount=total,
            merchant=merchant,
            date=txn_date,
            payment_method="receipt",
            source="receipt",
            ai_category=category,
            receipt_id=receipt.receipt_id,
        )

        db.add(txn)

    await db.commit()

    return {
        "success": True,
        "receipt": ReceiptResponse.model_validate(receipt),
        "parsed_receipt": {
            "merchant": {
                "value": merchant,
                "confidence": confidence,
            },
            "total": {
                "value": str(total) if total else "",
                "confidence": confidence,
            },
            "date": {
                "value": str(date_val) if date_val else "",
                "confidence": confidence,
            },
            "category": {
                "value": category,
                "confidence": 1,
            },
        },
    }


@router.get("/history")
async def receipt_history(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    limit: int = 20,
):

    offset = (page - 1) * limit

    rows = (
        await db.execute(
            select(Receipt)
            .where(Receipt.user_id == current_user.user_id)
            .order_by(Receipt.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()

    return {
        "total": len(rows),
        "page": page,
        "limit": limit,
        "items": [ReceiptResponse.model_validate(r) for r in rows],
    }