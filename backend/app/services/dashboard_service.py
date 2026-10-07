from datetime import datetime, timedelta, timezone

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models.llm_model import LLMModel
from app.models.project import Project
from app.models.prompt import PromptAnalysis
from app.models.usage import CostRecord, UsageRecord
from app.models.user import User
from app.schemas.dashboard import (CostByModel, CostByProject, DailyUsage, Forecast, MonthlyUsage, Overview,
                                   ProjectHistory, RecentActivity)
from app.services import cost_service
from app.services.usage_service import scope_clause

_tokens = func.coalesce(func.sum(UsageRecord.total_tokens), 0)
_cost = func.coalesce(func.sum(CostRecord.estimated_cost), 0)
_count = func.count(UsageRecord.id)


def _with_cost(stmt):
    return stmt.select_from(UsageRecord).outerjoin(CostRecord, CostRecord.usage_record_id == UsageRecord.id)


def overview(db: Session, user: User) -> Overview:
    stmt = _with_cost(select(
        _tokens, _cost, _count,
        func.coalesce(func.sum(CostRecord.potential_saving), 0),
        func.coalesce(func.avg(PromptAnalysis.reduction_percentage), 0),
    )).outerjoin(PromptAnalysis, PromptAnalysis.prompt_id == UsageRecord.prompt_id).where(scope_clause(db, user))
    tokens, cost, count, savings, avg_red = db.execute(stmt).one()
    return Overview(total_tokens=int(tokens), total_cost=float(cost), total_prompts=int(count),
                    total_savings=float(savings), average_reduction=round(float(avg_red), 2))


def daily_usage(db: Session, user: User, days: int = 30) -> list[DailyUsage]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    day = func.date(UsageRecord.created_at)
    stmt = (_with_cost(select(day, _tokens, _cost, _count))
            .where(scope_clause(db, user), UsageRecord.created_at >= since).group_by(day).order_by(day))
    return [DailyUsage(date=str(d), tokens=int(t), cost=float(c), requests=int(n)) for d, t, c, n in db.execute(stmt)]


def monthly_usage(db: Session, user: User, months: int = 12) -> list[MonthlyUsage]:
    since = datetime.now(timezone.utc) - timedelta(days=31 * months)
    y, m = extract("year", UsageRecord.created_at), extract("month", UsageRecord.created_at)
    stmt = (_with_cost(select(y, m, _tokens, _cost, _count))
            .where(scope_clause(db, user), UsageRecord.created_at >= since).group_by(y, m).order_by(y, m))
    return [MonthlyUsage(month=f"{int(yy):04d}-{int(mm):02d}", tokens=int(t), cost=float(c), requests=int(n))
            for yy, mm, t, c, n in db.execute(stmt)]


def cost_by_model(db: Session, user: User) -> list[CostByModel]:
    stmt = (_with_cost(select(LLMModel.name, _tokens, _cost, _count))
            .join(LLMModel, LLMModel.id == UsageRecord.model_id)
            .where(scope_clause(db, user)).group_by(LLMModel.name).order_by(_cost.desc()))
    return [CostByModel(model=n, tokens=int(t), cost=float(c), requests=int(r)) for n, t, c, r in db.execute(stmt)]


def cost_by_project(db: Session, user: User) -> list[CostByProject]:
    stmt = (_with_cost(select(UsageRecord.project_id, Project.name, _tokens, _cost, _count))
            .outerjoin(Project, Project.id == UsageRecord.project_id)
            .where(scope_clause(db, user)).group_by(UsageRecord.project_id, Project.name).order_by(_cost.desc()))
    return [CostByProject(project_id=pid, project=name or "Unassigned", tokens=int(t), cost=float(c), requests=int(r))
            for pid, name, t, c, r in db.execute(stmt)]


def recent_activity(db: Session, user: User, limit: int = 10) -> list[RecentActivity]:
    stmt = (select(UsageRecord, LLMModel.name, Project.name, CostRecord.estimated_cost, CostRecord.potential_saving)
            .join(LLMModel, LLMModel.id == UsageRecord.model_id)
            .outerjoin(Project, Project.id == UsageRecord.project_id)
            .outerjoin(CostRecord, CostRecord.usage_record_id == UsageRecord.id)
            .where(scope_clause(db, user)).order_by(UsageRecord.created_at.desc(), UsageRecord.id.desc()).limit(limit))
    return [RecentActivity(usage_id=u.id, timestamp=u.created_at, model=m, project_id=u.project_id, project=p,
                           total_tokens=u.total_tokens, estimated_cost=float(c or 0), potential_saving=float(s or 0))
            for u, m, p, c, s in db.execute(stmt)]


def project_history(db: Session, user: User) -> list[ProjectHistory]:
    stmt = (_with_cost(select(Project.id, Project.name, _count, _tokens, _cost,
                              func.coalesce(func.sum(CostRecord.potential_saving), 0), func.max(UsageRecord.created_at)))
            .join(Project, Project.id == UsageRecord.project_id)
            .where(scope_clause(db, user)).group_by(Project.id, Project.name).order_by(func.max(UsageRecord.created_at).desc()))
    return [ProjectHistory(project_id=pid, project=name, requests=int(n), tokens=int(t), cost=float(c),
                           savings=float(s), last_activity=last)
            for pid, name, n, t, c, s, last in db.execute(stmt)]


def forecast(db: Session, user: User, horizon_days: int = 7) -> Forecast:
    history = [d.cost for d in daily_usage(db, user, days=30)]
    values = cost_service.forecast_cost(history, horizon_days) if history else [0.0] * horizon_days
    return Forecast(horizon_days=horizon_days, daily_forecast=values, total_forecast=sum(values))
