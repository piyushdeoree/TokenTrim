from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import AIModel, CostRecord, UsageRecord, User
from app.repositories.crud import usage_scope
from app.schemas.schemas import UsageOut
from app.services.access import get_project_or_404

router = APIRouter(prefix="/usage", tags=["Usage"])


def _query(db: Session, where, limit: int, offset: int) -> list[UsageOut]:
    rows = db.execute(
        select(UsageRecord, AIModel.name, CostRecord)
        .join(AIModel, AIModel.id == UsageRecord.model_id)
        .join(CostRecord, CostRecord.usage_id == UsageRecord.id)
        .where(where).order_by(UsageRecord.created_at.desc(), UsageRecord.id.desc()).limit(limit).offset(offset)
    ).all()
    return [UsageOut(id=u.id, timestamp=u.created_at, model=name, input_tokens=u.input_tokens,
                     output_tokens=u.output_tokens, total_tokens=u.total_tokens, estimated_cost=c.estimated_cost,
                     potential_saving=c.potential_saving, project_id=u.project_id, user_id=u.user_id,
                     team_id=u.team_id) for u, name, c in rows]


@router.get("", response_model=list[UsageOut], summary="Usage history across everything you can access")
def list_usage(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _query(db, usage_scope(user), limit, offset)


@router.get("/{project_id}", response_model=list[UsageOut], summary="Usage history for one project")
def project_usage(project_id: int, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_project_or_404(db, user, project_id)
    return _query(db, UsageRecord.project_id == project_id, limit, offset)
