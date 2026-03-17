from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated

from db.database import get_db
from api.middleware.auth import CurrentUser
from models.orm import AnomalyAlert

router = APIRouter(tags=["Fraud Alerts"])


@router.get("/fraud/alerts")
async def get_alerts(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):

    result = await db.execute(
        select(AnomalyAlert)
        .where(AnomalyAlert.user_id == current_user.user_id)
        .order_by(AnomalyAlert.created_at.desc())
    )

    alerts = result.scalars().all()

    return alerts