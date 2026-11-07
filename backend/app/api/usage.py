from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.usage import UsagePage
from app.services import usage_service

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("", response_model=UsagePage, summary="Usage history across everything you can access")
def list_usage(model: str | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return usage_service.list_usage(db, user, model=model, limit=limit, offset=offset)


@router.get("/{project_id}", response_model=UsagePage, summary="Usage history for one project")
def list_project_usage(project_id: int, model: str | None = None, limit: int = Query(50, ge=1, le=200),
                       offset: int = Query(0, ge=0), user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    return usage_service.list_usage(db, user, project_id=project_id, model=model, limit=limit, offset=offset)
