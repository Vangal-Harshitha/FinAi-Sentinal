"""
services/voice_service.py — Whisper STT + NLP expense parsing
"""
import re
from datetime import date
from typing import Optional


async def transcribe_audio(filepath: str) -> str:
    """Whisper STT — falls back to stub."""
    try:
        import whisper
        model  = whisper.load_model("base")
        result = model.transcribe(filepath)
        return result["text"].strip()
    except ImportError:
        return "Whisper not installed. Add openai-whisper to requirements."
    except Exception as e:
        return f"Transcription failed: {e}"


async def parse_expense(transcript: str) -> dict:
    """NLP entity extraction from transcript."""
    amount   = _parse_amount(transcript)
    merchant = _parse_merchant(transcript)
    return {
        "amount":   amount,
        "merchant": merchant,
        "category": None,
        "date":     date.today(),
    }


def _parse_amount(text: str) -> Optional[float]:
    patterns = [
        r"(?:rs\.?|rupees?|₹)\s*(\d+(?:[.,]\d+)?)",
        r"(\d+(?:[.,]\d+)?)\s*(?:rs\.?|rupees?|₹)",
        r"\b(\d{2,6})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return None


def _parse_merchant(text: str) -> Optional[str]:
    patterns = [r"(?:at|from|paid|@)\s+([A-Za-z\s]+)", r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)"]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()[:100]
    return None
