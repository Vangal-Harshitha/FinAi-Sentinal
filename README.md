# FinAI — Intelligent Personal Finance Management System
### Phase 9: Complete System Integration

A full-stack AI-powered fintech application with FastAPI backend, Next.js frontend,
and 6 integrated ML models (categorisation, anomaly detection, forecasting, health scoring,
budget optimisation, SHAP explainability).

---

## Project Structure

```
FinAI/
├── backend/                     ← FastAPI Python backend
│   ├── main.py                  ← App entry point + lifespan hooks
│   ├── .env                     ← Environment variables (git-ignored)
│   ├── api/
│   │   ├── middleware/auth.py   ← JWT bearer token dependency
│   │   └── routes/
│   │       ├── auth.py          ← Register, login, /me
│   │       ├── transactions.py  ← CRUD + AI pipeline trigger
│   │       ├── receipts.py      ← OCR upload & history
│   │       ├── voice.py         ← Whisper transcription
│   │       ├── goals.py         ← Goal CRUD + progress
│   │       └── ai.py            ← Budget, forecast, alerts, health score
│   ├── core/
│   │   ├── config.py            ← Pydantic settings from .env
│   │   └── security.py          ← bcrypt + JWT helpers
│   ├── db/
│   │   └── database.py          ← Async SQLAlchemy engine + session
│   ├── models/
│   │   └── orm.py               ← All SQLAlchemy ORM models
│   ├── schemas/
│   │   └── schemas.py           ← Pydantic request/response models
│   └── services/
│       ├── ai_service.py        ← AI inference + DB aggregations
│       ├── transaction_service.py ← Full AI pipeline (categorise→anomaly→store)
│       ├── ml_registry.py       ← Central ML model loader at startup
│       ├── ocr_service.py       ← PaddleOCR / Tesseract receipt parsing
│       └── voice_service.py     ← Whisper STT + NLP entity extraction
│
├── frontend/                    ← Next.js 14 + Tailwind CSS frontend
│   ├── .env.local               ← NEXT_PUBLIC_API_URL
│   ├── package.json
│   └── src/
│       ├── app/                 ← Next.js App Router pages
│       │   ├── dashboard/       ← Main dashboard with stats
│       │   ├── transactions/    ← Transaction list + add modal
│       │   ├── budget/          ← AI budget recommendations
│       │   ├── forecast/        ← Expense forecast charts
│       │   ├── goals/           ← Financial goals tracker
│       │   ├── receipts/        ← OCR receipt upload
│       │   ├── voice/           ← Voice expense entry
│       │   ├── fraud/           ← Anomaly alert management
│       │   ├── health/          ← Financial health score
│       │   └── auth/            ← Login / Register
│       ├── components/
│       │   ├── layout/AppShell.tsx ← Sidebar + nav wrapper
│       │   └── Providers.tsx    ← React Query provider
│       ├── lib/api.ts           ← Centralised axios API layer
│       └── store/index.ts       ← Zustand global state
│
├── ml_models/                   ← ML model implementations
│   ├── anomaly_detection/       ← IsolationForest anomaly scorer
│   ├── forecasting/             ← Time-series expense forecasting
│   ├── health_score/            ← Financial health composite model
│   ├── budget_optimizer/        ← RL-based budget recommendation
│   ├── behavior_analysis/       ← Spending pattern analysis
│   └── explainability/          ← SHAP explanation module
│
├── datasets/                    ← Synthetic CSV data for seeding
│   ├── transactions.csv
│   ├── users.csv
│   ├── goals.csv
│   └── receipts.csv
│
├── scripts/
│   ├── seed_db.py               ← Seed PostgreSQL from CSV files
│   ├── train_models.py          ← Train all ML models
│   └── schema.sql               ← Raw SQL schema reference
│
├── requirements.txt             ← Python dependencies
└── .env.example                 ← Environment variable template
```

---

## Quick Start (VS Code)

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | python.org |
| Node.js | 18+ | nodejs.org |
| PostgreSQL | 15+ | postgresql.org |
| Git | any | git-scm.com |

---

### Step 1 — Clone / Open Project

```bash
# Open the FinAI folder in VS Code
code FinAI
```

---

### Step 2 — PostgreSQL Setup

#### Option A: Local PostgreSQL

```sql
-- Open psql as superuser and run:
CREATE USER finai_user WITH PASSWORD 'finai_pass';
CREATE DATABASE finai_db OWNER finai_user;
GRANT ALL PRIVILEGES ON DATABASE finai_db TO finai_user;
```

#### Option B: Docker (fastest)

```bash
docker run -d \
  --name finai-postgres \
  -e POSTGRES_USER=finai_user \
  -e POSTGRES_PASSWORD=finai_pass \
  -e POSTGRES_DB=finai_db \
  -p 5432:5432 \
  postgres:15-alpine
```

---

### Step 3 — Backend Setup

Open a new VS Code terminal and run:

```bash
# Navigate to project root
cd FinAI

# Create and activate virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify backend .env exists (already configured with defaults)
cat backend/.env
```

**If you need to customise the database connection**, edit `backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://finai_user:finai_pass@localhost:5432/finai_db
```

---

### Step 4 — Seed the Database

```bash
# Still from FinAI/ root with venv active:
python scripts/seed_db.py
```

Expected output:
```
INFO: ✅ Tables created/verified
INFO: ✅ Seeded 10 expense categories
INFO: ✅ Created demo user: demo@finai.com / Demo@1234
INFO: ✅ Seeded 500 transactions from CSV
INFO: 🎉 Database seeding complete!
```

---

### Step 5 — (Optional) Train ML Models

```bash
python scripts/train_models.py
```

> Models use IsolationForest, Ridge Regression, and gradient boosting.
> This requires scikit-learn (already in requirements.txt).
> Training takes ~2-5 minutes. If skipped, intelligent rule-based fallbacks are used.

---

### Step 6 — Start the Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's running:
- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

### Step 7 — Frontend Setup

Open a **second VS Code terminal**:

```bash
cd FinAI/frontend
npm install
npm run dev
```

Frontend runs at: **http://localhost:3000**

---

### Step 8 — Login & Test

1. Open http://localhost:3000
2. Login with: `demo@finai.com` / `Demo@1234`
3. Navigate to **Transactions** → Add a transaction
4. Watch the dashboard update with AI predictions

---

## AI Pipeline — How It Works

### Transaction Flow (Add Transaction → Dashboard Updates)

```
User submits transaction form
        ↓
POST /api/v1/transactions
        ↓
transaction_service.create_transaction()
        ↓
 ┌─────────────────────────────────────────────┐
 │  Step 1: Persist transaction skeleton        │
 │  Step 2: AI Categorisation                  │
 │          classify_transaction(merchant)      │
 │          → ai_category + confidence stored  │
 │  Step 3: Anomaly Detection                  │
 │          model_registry.detect_anomaly()    │
 │          → is_anomaly + anomaly_score stored│
 │          → AnomalyAlert created if flagged  │
 └─────────────────────────────────────────────┘
        ↓
Response returned to frontend
        ↓
React Query invalidates:
  ['transactions'], ['dashboard-stats'],
  ['fraud-alerts']
        ↓
Dashboard re-fetches and updates live
```

### ML Models & Endpoints

| Model | Endpoint | Trigger |
|-------|----------|---------|
| FinBERT / keyword categoriser | POST /transactions | Every new transaction |
| IsolationForest anomaly detector | POST /transactions | Every new transaction |
| ARIMA / TFT forecaster | GET /forecast/expenses | On demand |
| RL budget optimizer | GET /budget/optimization | On demand |
| Composite health scorer | GET /health-score | On demand |
| SHAP explainer | GET /health-score | Alongside health score |

---

## API Reference

All endpoints are prefixed with `/api/v1`. Full interactive docs at `/docs`.

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/register | Create account |
| POST | /auth/login | Login → JWT tokens |
| GET | /auth/me | Current user profile |
| PATCH | /auth/me | Update profile |

### Transactions
| Method | Path | Description |
|--------|------|-------------|
| POST | /transactions | Add transaction (triggers AI pipeline) |
| GET | /transactions | List with filters & pagination |
| DELETE | /transactions/{id} | Delete transaction |
| GET | /transactions/categories | All expense categories |
| GET | /transactions/monthly-summary | Monthly totals |

### AI & Analytics
| Method | Path | Description |
|--------|------|-------------|
| GET | /budget/optimization | RL budget recommendations |
| GET | /forecast/expenses | Next-month forecast |
| GET | /forecast/dashboard-stats | Spend summary for dashboard |
| GET | /fraud/alerts | Anomaly alerts |
| POST | /fraud/alerts/{id}/resolve | Resolve an alert |
| GET | /health-score | Financial health score + SHAP insights |

### Goals
| Method | Path | Description |
|--------|------|-------------|
| GET | /goals | List all goals |
| POST | /goals | Create goal |
| GET | /goals/{id}/progress | Progress tracking |
| POST | /goals/{id}/deposit | Add savings |

---

## Frontend Pages

| URL | Page | Features |
|-----|------|----------|
| /dashboard | Dashboard | Live stats, AI insights, quick nav |
| /transactions | Transactions | Add/delete/paginate, anomaly badges |
| /budget | Budget Optimizer | RL recommendations, utilisation bars |
| /forecast | Expense Forecast | Bar charts, category breakdown |
| /goals | Financial Goals | Create goals, progress tracking |
| /receipts | Receipt OCR | Upload → auto-extract → store |
| /voice | Voice Entry | Record → Whisper → parse expense |
| /fraud | Fraud Alerts | View/resolve anomaly alerts |
| /health | Health Score | Radar chart, SHAP insights |
| /profile | Profile | User info, logout |

---

## Database Schema

Tables automatically created on first backend start:

- `users` — User accounts and financial profile
- `expense_categories` — Category taxonomy (seeded on startup)
- `transactions` — All transactions with AI predictions
- `receipts` — OCR receipt data and metadata
- `voice_entries` — Whisper transcriptions
- `goals` — Financial goals and savings
- `budgets` — AI-recommended budget allocations
- `predictions` — Stored model predictions cache
- `anomaly_alerts` — Flagged unusual transactions
- `financial_health_scores` — Historical health scores

---

## Troubleshooting

### "Connection refused" on port 5432
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Or with Docker:
docker ps | grep postgres
docker start finai-postgres
```

### "Module not found" in backend
```bash
# Make sure you're running from FinAI/backend/ with venv active
cd FinAI/backend
source ../venv/bin/activate  # or ..\venv\Scripts\activate on Windows
uvicorn main:app --reload
```

### Frontend "Network Error" / 401
```bash
# Check CORS: frontend .env.local should match backend port
cat frontend/.env.local
# Should be: NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Check backend CORS config in backend/.env
# ALLOWED_ORIGINS=http://localhost:3000
```

### ML models not loading
Models fall back to rule-based implementations if `.joblib` files are absent.
To train models:
```bash
cd FinAI
python scripts/train_models.py
```

### "Tables don't exist"
```bash
# Re-run seeding (also creates tables)
python scripts/seed_db.py
```

---

## Optional: Heavy ML Features

Uncomment in `requirements.txt` and install for full AI power:

```bash
# FinBERT transaction categorisation
pip install torch transformers

# Voice transcription (Whisper)
pip install openai-whisper

# Receipt OCR (PaddleOCR)
pip install paddlepaddle paddleocr

# RL budget optimizer
pip install stable-baselines3
```

---

## VS Code Recommended Extensions

Install for best experience:
- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **ESLint** (dbaeumer.vscode-eslint)
- **Tailwind CSS IntelliSense** (bradlc.vscode-tailwindcss)
- **REST Client** (humao.rest-client) — for testing API
- **Thunder Client** — alternative API tester

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI 0.115 + Python 3.11 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 15 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| ML Models | scikit-learn, numpy, pandas, SHAP |
| OCR | PaddleOCR (+ Tesseract fallback) |
| STT | OpenAI Whisper |
| Frontend | Next.js 14 (App Router) + TypeScript |
| Styling | Tailwind CSS 3 |
| State | Zustand + React Query v5 |
| Charts | Recharts |
| HTTP Client | Axios |

---

*FinAI Phase 9 — Complete System Integration*
