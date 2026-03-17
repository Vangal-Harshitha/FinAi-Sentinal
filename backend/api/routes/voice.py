"""
api/routes/voice.py — Voice-to-expense transcription
"""

import os
import uuid
import aiofiles

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import CurrentUser
from db.database import get_db
from models.orm import VoiceEntry, Transaction
from schemas.schemas import VoiceEntryResponse
from core.config import get_settings


router = APIRouter(prefix="/voice", tags=["Voice Entries"])
settings = get_settings()


@router.post("/transcribe")
async def transcribe_voice(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    audio: UploadFile = File(...),
):

    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    fname = f"voice_{uuid.uuid4()}.webm"
    fpath = os.path.join(upload_dir, fname)

    async with aiofiles.open(fpath, "wb") as f:
        await f.write(await audio.read())

    transcript = ""
    parsed = {}

    try:
        from services.voice_service import transcribe_audio, parse_expense

        transcript = await transcribe_audio(fpath)
        parsed = await parse_expense(transcript)

    except Exception:
        transcript = "Voice transcription unavailable — Whisper not configured."

    amount = parsed.get("amount")
    merchant = parsed.get("merchant")
    category = parsed.get("category")
    date_val = parsed.get("date")

    # Convert date
    txn_date = date_val if date_val else datetime.utcnow().date()

    # ─────────────────────
    # SAVE VOICE ENTRY
    # ─────────────────────

    entry = VoiceEntry(
        user_id=current_user.user_id,
        audio_url=f"/uploads/{fname}",
        transcript=transcript,
        stt_engine="Whisper",
        parsed_amount=amount,
        parsed_merchant=merchant,
        parsed_category=category,
        parsed_date=date_val,
        parse_status="parsed" if amount else "partial",
    )

    db.add(entry)

    await db.flush()
    await db.refresh(entry)

    # ─────────────────────
    # CREATE TRANSACTION
    # ─────────────────────

    if amount:

        txn = Transaction(
            user_id=current_user.user_id,
            amount=amount,
            merchant=merchant,
            date=txn_date,
            payment_method="voice",
            source="voice",
            ai_category=category,
            voice_entry_id=entry.voice_entry_id,
        )

        db.add(txn)

    await db.commit()

    return {
        "text": transcript,
        "transaction": {
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "date": str(date_val or ""),
        } if amount else None,
        "voice_entry": VoiceEntryResponse.model_validate(entry),
    }