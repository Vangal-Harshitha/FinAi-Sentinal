"""
api/routes/goals.py  —  Financial Goals CRUD + Planning
"""
import math
from decimal import Decimal
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import CurrentUser
from db.database import get_db
from models.orm import Goal
from schemas.schemas import GoalCreate, GoalProgressResponse, GoalResponse, MessageResponse

router = APIRouter(prefix="/goals", tags=["Goals"])


@router.get("", response_model=dict)
async def list_goals(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Optional[str] = Query(None, alias="status"),
):
    q = select(Goal).where(Goal.user_id == current_user.user_id)
    if status_filter:
        q = q.where(Goal.status == status_filter)
    q = q.order_by(Goal.created_at.desc())
    items = (await db.execute(q)).scalars().all()
    return {"total": len(items), "items": [GoalResponse.model_validate(g) for g in items]}


@router.post("", response_model=GoalResponse, status_code=201)
async def create_goal(
    payload: GoalCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    goal = Goal(
        user_id         = current_user.user_id,
        goal_name       = payload.goal_name,
        goal_category   = payload.goal_category,
        target_amount   = payload.target_amount,
        current_savings = payload.current_savings,
        deadline_months = payload.deadline_months,
        priority        = payload.priority,
        notes           = payload.notes,
    )
    db.add(goal)
    await db.flush()
    await db.refresh(goal)
    return GoalResponse.model_validate(goal)


@router.get("/dashboard")
async def goals_dashboard(current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    q = select(Goal).where(Goal.user_id == current_user.user_id, Goal.status == "active")
    goals = (await db.execute(q)).scalars().all()
    total_target = sum(float(g.target_amount) for g in goals)
    total_saved  = sum(float(g.current_savings) for g in goals)
    return {
        "total_goals": len(goals),
        "total_target": total_target,
        "total_saved":  total_saved,
        "overall_progress": round(total_saved / total_target * 100, 1) if total_target else 0,
        "goals": [GoalResponse.model_validate(g) for g in goals],
    }


@router.get("/categories")
async def goal_categories():
    return [
        {"value": "emergency_fund", "label": "Emergency Fund"},
        {"value": "retirement",     "label": "Retirement"},
        {"value": "home_purchase",  "label": "Home Purchase"},
        {"value": "vehicle",        "label": "Vehicle"},
        {"value": "education",      "label": "Education"},
        {"value": "travel",         "label": "Travel"},
        {"value": "debt_payoff",    "label": "Debt Payoff"},
        {"value": "investment",     "label": "Investment"},
        {"value": "wedding",        "label": "Wedding"},
        {"value": "custom",         "label": "Custom"},
    ]


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(goal_id: str, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    row = await db.execute(select(Goal).where(Goal.goal_id == goal_id, Goal.user_id == current_user.user_id))
    goal = row.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return GoalResponse.model_validate(goal)


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    payload: dict,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row  = await db.execute(select(Goal).where(Goal.goal_id == goal_id, Goal.user_id == current_user.user_id))
    goal = row.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    for k, v in payload.items():
        if hasattr(goal, k):
            setattr(goal, k, v)
    await db.flush()
    await db.refresh(goal)
    return GoalResponse.model_validate(goal)


@router.delete("/{goal_id}", response_model=MessageResponse)
async def delete_goal(goal_id: str, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    row  = await db.execute(select(Goal).where(Goal.goal_id == goal_id, Goal.user_id == current_user.user_id))
    goal = row.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    await db.delete(goal)
    return MessageResponse(message="Goal deleted")


@router.get("/{goal_id}/progress", response_model=GoalProgressResponse)
async def goal_progress(goal_id: str, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    row  = await db.execute(select(Goal).where(Goal.goal_id == goal_id, Goal.user_id == current_user.user_id))
    goal = row.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    remaining = float(goal.target_amount) - float(goal.current_savings)
    monthly_req = remaining / goal.deadline_months if goal.deadline_months else 0
    progress = float(goal.current_savings) / float(goal.target_amount) if goal.target_amount else 0
    return GoalProgressResponse(
        goal_id           = goal.goal_id,
        goal_name         = goal.goal_name,
        target_amount     = goal.target_amount,
        current_savings   = goal.current_savings,
        progress_pct      = round(progress, 4),
        monthly_required  = Decimal(str(round(monthly_req, 2))),
        months_remaining  = goal.deadline_months,
        on_track          = monthly_req < float(goal.target_amount) * 0.1,
        projected_completion_months = goal.deadline_months,
    )


@router.post("/{goal_id}/deposit", response_model=GoalResponse)
async def deposit(
    goal_id: str,
    body: dict,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row  = await db.execute(select(Goal).where(Goal.goal_id == goal_id, Goal.user_id == current_user.user_id))
    goal = row.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    goal.current_savings = Decimal(str(float(goal.current_savings) + float(body.get("amount", 0))))
    if float(goal.current_savings) >= float(goal.target_amount):
        goal.status = "completed"
    await db.flush()
    await db.refresh(goal)
    return GoalResponse.model_validate(goal)
