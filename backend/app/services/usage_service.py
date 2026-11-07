from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.llm_model import LLMModel
from app.models.usage import CostRecord, UsageRecord
from app.models.user import User
from app.repositories import project_repository
from app.schemas.usage import UsageOut, UsagePage
from app.services import project_service


def scope_clause(db: Session, user: User):
    """Usage visible to a user: their own records plus records in projects they can access (team projects)."""
    ids = project_repository.accessible_ids(db, user.id)
    return or_(UsageRecord.user_id == user.id, UsageRecord.project_id.in_(ids))


def list_usage(db: Session, user: User, project_id: int | None = None, model: str | None = None,
               limit: int = 50, offset: int = 0) -> UsagePage:
    if project_id is not None:
        project_service.get_accessible(db, project_id, user)  # 404 if no access
        where = [UsageRecord.project_id == project_id]
    else:
        where = [scope_clause(db, user)]
    if model:
        where.append(LLMModel.name == model)

    base = (select(UsageRecord, LLMModel.name, CostRecord.estimated_cost)
            .join(LLMModel, LLMModel.id == UsageRecord.model_id)
            .outerjoin(CostRecord, CostRecord.usage_record_id == UsageRecord.id).where(*where))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(UsageRecord.created_at.desc(), UsageRecord.id.desc())
                      .limit(limit).offset(offset)).all()
    items = [UsageOut(id=u.id, timestamp=u.created_at, model=name, project_id=u.project_id, user_id=u.user_id,
                      team_id=u.team_id, input_tokens=u.input_tokens, output_tokens=u.output_tokens,
                      total_tokens=u.total_tokens, estimated_cost=float(cost or 0))
             for u, name, cost in rows]
    return UsagePage(items=items, total=total, limit=limit, offset=offset)
