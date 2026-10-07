from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.dashboard import (CostByModel, CostByProject, DailyUsage, Forecast, MonthlyUsage, Overview,
                                   ProjectHistory, RecentActivity)
from app.services import dashboard_service as svc

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=Overview)
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.overview(db, user)


@router.get("/daily-usage", response_model=list[DailyUsage])
def daily_usage(days: int = Query(30, ge=1, le=365), user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return svc.daily_usage(db, user, days)


@router.get("/monthly-usage", response_model=list[MonthlyUsage])
def monthly_usage(months: int = Query(12, ge=1, le=36), user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return svc.monthly_usage(db, user, months)


@router.get("/cost-by-model", response_model=list[CostByModel])
def cost_by_model(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.cost_by_model(db, user)


@router.get("/cost-by-project", response_model=list[CostByProject])
def cost_by_project(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.cost_by_project(db, user)


@router.get("/recent-activity", response_model=list[RecentActivity])
def recent_activity(limit: int = Query(10, ge=1, le=100), user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return svc.recent_activity(db, user, limit)


@router.get("/project-history", response_model=list[ProjectHistory])
def project_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.project_history(db, user)


@router.get("/forecast", response_model=Forecast, summary="Spend forecast from Person 2's cost engine")
def forecast(days: int = Query(7, ge=1, le=90), user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    return svc.forecast(db, user, days)
