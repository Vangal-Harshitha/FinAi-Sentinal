from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import CurrentUser
from db.database import get_db
from models.orm import AnomalyAlert, Transaction
from datetime import datetime, timedelta

from schemas.schemas import (
BudgetRecommendation,
BudgetRecommendationsResponse,
ForecastResponse,
FinancialHealthResponse,
HealthSubScores,
)

from services.ai_service import (
compute_health_score,
forecast_expenses,
get_budget_recommendations,
)

router = APIRouter(tags=["AI & Analytics"])

# ---------------- Budget Recommendations ----------------

async def _budget_recs(
  current_user: CurrentUser,
  db: Annotated[AsyncSession, Depends(get_db)]
):


    result = await get_budget_recommendations(
      user_id=str(current_user.user_id),
      monthly_income=float(current_user.monthly_income or 50000),
      db=db,
    )

    return BudgetRecommendationsResponse(
      user_id=result["user_id"],
      month=result["month"],
      total_income=Decimal(str(result["total_income"])),
      total_allocated=Decimal(str(result["total_allocated"])),
      total_spend=Decimal(str(result["total_spend"])),
      recommendations=[BudgetRecommendation(**r) for r in result["recommendations"]],
      model_version=result["model_version"],
    )


router.add_api_route(
"/budget/optimization",
_budget_recs,
methods=["GET"],
)

# ---------------- Forecast ----------------

async def _forecast(
  current_user: CurrentUser,
  db: Annotated[AsyncSession, Depends(get_db)]
):


    result = await forecast_expenses(str(current_user.user_id), db)

    return ForecastResponse(**result)


router.add_api_route(
"/forecast/expenses",
_forecast,
methods=["GET"],
)

# ---------------- Dashboard ----------------

@router.get("/forecast/dashboard-stats")
async def dashboard_stats(
  current_user: CurrentUser,
  db: Annotated[AsyncSession, Depends(get_db)]
):

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    current_spend = (
      await db.execute(
        select(func.sum(Transaction.amount)).where(
            Transaction.user_id == current_user.user_id,
            Transaction.date >= thirty_days_ago
        )
      )
    ).scalar() or 0

    total_transactions = (
      await db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.user_id == current_user.user_id)
      )
    ).scalar() or 0

    anomaly_count = (
      await db.execute(
        select(func.count())
        .select_from(AnomalyAlert)
        .where(AnomalyAlert.user_id == current_user.user_id)
      )
    ).scalar() or 0

    return {
      "total_spend_30d": float(current_spend),
      "open_alerts": anomaly_count,
      "monthly_income": float(current_user.monthly_income or 0),
      "total_transactions": total_transactions,
    }


# ---------------- Financial Health ----------------

async def _health(
  current_user: CurrentUser,
  db: Annotated[AsyncSession, Depends(get_db)]
):


    result = await compute_health_score(
      user_id=str(current_user.user_id),
      monthly_income=float(current_user.monthly_income or 50000),
      db=db,
    )

    return FinancialHealthResponse(
      user_id=result["user_id"],
      score_date=result["score_date"],
      overall_score=result["overall_score"],
      score_band=result["score_band"],
      sub_scores=HealthSubScores(**result["sub_scores"]),
      top_insights=result["top_insights"],
      previous_score=result["previous_score"],
      score_delta=result["score_delta"],
      model_version=result["model_version"],
      generated_at=result["generated_at"],
    )


router.add_api_route(
"/health-score",
_health,
methods=["GET"],
)
