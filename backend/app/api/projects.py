from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories import project_repository
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return project_service.create(db, user, body.name, body.description, body.team_id)


@router.get("", response_model=list[ProjectOut], summary="Projects you own or can access through a team")
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return project_repository.list_accessible(db, user.id)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return project_service.get_accessible(db, project_id, user)


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return project_service.update(db, project_id, user, body.model_dump(exclude_unset=True))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project_service.delete(db, project_id, user)
