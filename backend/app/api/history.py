from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import LLMModel, Prompt, PromptAnalysis, Project, User
from app.models import UsageRecord
from app.services import project_service

router = APIRouter(prefix="/history", tags=["Prompt history"])


class ProjectAssignment(BaseModel):
    project_id: int = Field(gt=0)


def _item(prompt: Prompt, analysis: PromptAnalysis, model: str, project: str | None):
    return {
        "id": prompt.id, "created_at": prompt.created_at,
        "original_prompt": prompt.original_text, "optimized_prompt": prompt.optimized_text,
        "model": model, "project_id": prompt.project_id, "project": project,
        "original_tokens": analysis.original_tokens, "optimized_tokens": analysis.optimized_tokens,
        "tokens_saved": analysis.tokens_saved, "reduction_percentage": analysis.reduction_percentage,
        "complexity_score": analysis.complexity_score,
        "issues": analysis.issues, "suggestions": analysis.suggestions,
    }


def _base_query(user: User):
    return (select(Prompt, PromptAnalysis, LLMModel.name, Project.name)
            .join(PromptAnalysis, PromptAnalysis.prompt_id == Prompt.id)
            .join(LLMModel, LLMModel.id == Prompt.model_id)
            .outerjoin(Project, Project.id == Prompt.project_id)
            .where(Prompt.user_id == user.id))


@router.get("")
def list_history(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), project_id: int | None = None,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = _base_query(user)
    if project_id is not None:
        project_service.get_accessible(db, project_id, user)
        query = query.where(Prompt.project_id == project_id)
    rows = db.execute(query.order_by(Prompt.created_at.desc(), Prompt.id.desc())
                      .limit(limit).offset(offset)).all()
    return [_item(*row) for row in rows]


@router.get("/{prompt_id}")
def get_history_item(prompt_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.execute(_base_query(user).where(Prompt.id == prompt_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _item(*row)


@router.patch("/{prompt_id}/project")
def assign_project(prompt_id: int, body: ProjectAssignment, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project_id = body.project_id
    prompt = db.scalar(select(Prompt).where(Prompt.id == prompt_id, Prompt.user_id == user.id))
    if prompt is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    project = project_service.get_accessible(db, project_id, user)
    prompt.project_id = project.id
    usage = db.scalar(select(UsageRecord).where(UsageRecord.prompt_id == prompt.id, UsageRecord.user_id == user.id))
    if usage:
        usage.project_id = project.id
        usage.team_id = project.team_id
    db.commit()
    return {"prompt_id": prompt.id, "project_id": project.id}
