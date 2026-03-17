"""
services/ocr_service.py — Smart Receipt OCR (Images + PDF + Category Detection)
"""

import re
import os
import pytesseract
from PIL import Image
from datetime import date, datetime
from typing import Optional
from pdf2image import convert_from_path

# Windows path for tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


async def process_receipt(filepath: str, engine: str = "auto") -> dict:

    text = ""
    confidence = 0.9

    try:

        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".pdf":
            pages = convert_from_path(filepath)
            img = pages[0]
        else:
            img = Image.open(filepath)

        # Improve OCR accuracy
        img = img.convert("L")

        text = pytesseract.image_to_string(img)

        print("\n========= OCR TEXT =========")
        print(text)
        print("============================\n")

    except Exception as e:
        print("OCR ERROR:", e)

    merchant = _extract_merchant(text)
    total = _extract_total(text)
    dt = _extract_date(text)
    category = _detect_category(merchant)

    return {
        "merchant": merchant,
        "total": total,
        "date": dt,
        "category": category,
        "text": text,
        "confidence": confidence,
    }


# ---------------- MERCHANT DETECTION ---------------- #

KNOWN_MERCHANTS = {
    "swiggy": "Swiggy",
    "swigay": "Swiggy",
    "zomato": "Zomato",
    "amazon": "Amazon",
    "flipkart": "Flipkart",
    "uber": "Uber",
    "ola": "Ola",
}


def _extract_merchant(text: str) -> str:

    if not text:
        return "Unknown merchant"

    lower = text.lower()

    # Known merchant detection
    for key, value in KNOWN_MERCHANTS.items():
        if key in lower:
            return value

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    for line in lines[:12]:

        if len(line) < 3:
            continue

        if "@" in line:
            continue

        if re.search(r"\d{5,}", line):
            continue

        cleaned = re.sub(r"[^A-Za-z0-9 &\-]", "", line)

        return cleaned[:80]

    return "Unknown merchant"


# ---------------- TOTAL DETECTION ---------------- #

def _extract_total(text: str) -> Optional[float]:

    if not text:
        return None

    patterns = [

        r"(?:total|grand\s+total|amount\s+payable)[^\d]{0,10}([\d,.]+)",
        r"price[^\d]{0,10}([\d,.]+)",
        r"quantity\s*price[^\d]{0,10}([\d,.]+)",
        r"=+\s*([\d,.]+)",
        r"₹\s*([\d,.]+)",
    ]

    for pat in patterns:

        m = re.search(pat, text, re.I)

        if m:
            try:
                val = float(m.group(1).replace(",", ""))
                if 10 < val < 50000:
                    return val
            except:
                pass

    nums = re.findall(r"\b\d{3,6}\b", text)

    values = []

    for n in nums:
        try:
            v = int(n)

            if 50 < v < 20000:
                values.append(v)

        except:
            pass

    if values:
        values.sort()
        return float(values[len(values) // 2])

    return None


# ---------------- DATE DETECTION ---------------- #

def _extract_date(text: str) -> Optional[date]:

    if not text:
        return None

    # numeric formats
    patterns = [
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
        r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
    ]

    for pat in patterns:

        m = re.search(pat, text)

        if m:
            try:
                g = m.groups()

                if len(g[0]) == 4:
                    return date(int(g[0]), int(g[1]), int(g[2]))
                else:
                    return date(int(g[2]), int(g[1]), int(g[0]))

            except:
                pass


    # format: May 25, 2022
    m = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}",
        text,
        re.I,
    )

    if m:
        try:
            return datetime.strptime(m.group(0), "%B %d, %Y").date()
        except:
            pass


    # format: Wednesday, May 25, 2022
    m = re.search(
        r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}",
        text,
        re.I,
    )

    if m:
        try:
            clean = re.sub(
                r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+",
                "",
                m.group(0),
                flags=re.I,
            )
            return datetime.strptime(clean, "%B %d, %Y").date()
        except:
            pass

    return None


# ---------------- CATEGORY DETECTION ---------------- #

def _detect_category(merchant: str) -> str:

    if not merchant:
        return "Other"

    m = merchant.lower()

    food = ["swiggy", "zomato"]
    travel = ["uber", "ola"]
    shopping = ["amazon", "flipkart"]

    if any(x in m for x in food):
        return "Food"

    if any(x in m for x in travel):
        return "Travel"

    if any(x in m for x in shopping):
        return "Shopping"

    return "Other"