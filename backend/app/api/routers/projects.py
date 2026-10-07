from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.database.session import get_db
from app.models import Project, User
from app.repositories.crud import accessible_project_ids
from app.schemas.schemas import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.access import get_project_or_404, require_team_role

router = APIRouter(prefix="/projects", tags=["Projects"])


def _commit(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "PROJECT_NAME_TAKEN", "You already have a project with this name.")


@router.post("", response_model=ProjectOut, status_code=201, summary="Create a project")
def create_project(body: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.team_id is not None:
        require_team_role(db, body.team_id, user, "member")
    project = Project(name=body.name.strip(), description=body.description, owner_id=user.id, team_id=body.team_id)
    db.add(project)
    _commit(db)
    return project


@router.get("", response_model=list[ProjectOut], summary="List projects you own or can access via a team")
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Project).where(Project.id.in_(accessible_project_ids(user))).order_by(Project.id)).all()


@router.get("/{project_id}", response_model=ProjectOut, summary="Get one project")
def get_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_project_or_404(db, user, project_id)


@router.put("/{project_id}", response_model=ProjectOut, summary="Update a project (owner or team admin)")
def update_project(project_id: int, body: ProjectUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    project = get_project_or_404(db, user, project_id, write=True)
    project.name, project.description = body.name.strip(), body.description
    _commit(db)
    return project


@router.delete("/{project_id}", status_code=204, summary="Delete a project (owner or team admin)")
def delete_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(get_project_or_404(db, user, project_id, write=True))
    db.commit()
    return Response(status_code=204)
