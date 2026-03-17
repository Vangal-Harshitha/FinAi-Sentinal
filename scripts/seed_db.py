"""
scripts/seed_db.py
Seed the PostgreSQL database with demo data.

Usage:
    cd FinAI
    python scripts/seed_db.py
"""

import sys
import asyncio
import uuid
import logging
from pathlib import Path
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("seed")


async def seed():

    from core.config import get_settings
    from models.orm import Base
    from core.security import hash_password

    settings = get_settings()

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    log.info("✅ Tables created/verified")

    async with SessionLocal() as db:

        # ───────── Seed Categories ─────────

        categories = [
            (1, "Food & Dining", "🍽️", "#FF6B6B", True),
            (2, "Transport", "🚗", "#4ECDC4", True),
            (3, "Bills & Utilities", "💡", "#45B7D1", True),
            (4, "Shopping", "🛍️", "#96CEB4", False),
            (5, "Entertainment", "🎬", "#FFEAA7", False),
            (6, "Healthcare", "🏥", "#DDA0DD", True),
            (7, "Education", "📚", "#98D8C8", True),
            (8, "Finance & EMI", "💳", "#F7DC6F", False),
            (9, "Travel", "✈️", "#BB8FCE", False),
            (10, "Other", "📦", "#AEB6BF", False),
        ]

        for cid, name, icon, color, essential in categories:

            await db.execute(text("""
                INSERT INTO expense_categories
                (category_id, name, icon, color_hex, is_essential)
                VALUES (:cid, :name, :icon, :color, :ess)
                ON CONFLICT (category_id) DO NOTHING
            """), {
                "cid": cid,
                "name": name,
                "icon": icon,
                "color": color,
                "ess": essential
            })

        log.info("✅ Categories seeded")

        # ───────── Seed Demo User ─────────

        demo_user_id = str(uuid.uuid4())

        await db.execute(text("""
            INSERT INTO users
            (user_id, email, password_hash, full_name, monthly_income, city)
            VALUES (:uid, :email, :pw, :name, :income, :city)
            ON CONFLICT (email) DO NOTHING
        """), {
            "uid": demo_user_id,
            "email": "demo@finai.com",
            "pw": hash_password("Demo@1234"),
            "name": "Demo User",
            "income": 75000,
            "city": "Bangalore"
        })

        log.info("✅ Demo user created")

        # ───────── Seed Transactions ─────────

        merchants = [
            "Amazon", "Flipkart", "Swiggy", "Zomato", "Uber",
            "Netflix", "Spotify", "Big Bazaar", "Reliance Smart",
            "Petrol Pump"
        ]

        payment_methods = ["UPI", "Credit Card", "Debit Card", "Cash"]

        txn_count = 0

        for i in range(500):

            await db.execute(text("""
                INSERT INTO transactions
                (transaction_id, user_id, date, merchant, amount,
                 payment_method, source, ai_category, is_anomaly, category_id)
                VALUES
                (:tid, :uid, :dt, :merchant, :amount,
                 :pm, :src, :cat, :anom, :cid)
            """), {
                "tid": str(uuid.uuid4()),
                "uid": demo_user_id,
                "dt": str(date.today()),
                "merchant": merchants[i % len(merchants)],
                "amount": float(100 + (i * 5)),
                "pm": payment_methods[i % len(payment_methods)],
                "src": "manual",
                "cat": "Shopping",
                "anom": False,
                "cid": (i % 10) + 1
            })

            txn_count += 1

        log.info(f"✅ Seeded {txn_count} transactions")

        await db.commit()

        log.info("🎉 Database seeding complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())