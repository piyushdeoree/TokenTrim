from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.project import Project
from app.models.user import User
from app.repositories import project_repository, team_repository
from app.services.team_service import RANK


def get_accessible(db: Session, project_id: int, user: User) -> Project:
    """Owner or any member of the project's team can read. 404 hides existence from others."""
    p = project_repository.get(db, project_id)
    if p is None:
        raise NotFoundError("Project not found.")
    if p.owner_id == user.id:
        return p
    if p.team_id and team_repository.get_membership(db, p.team_id, user.id):
        return p
    raise NotFoundError("Project not found.")


def _require_manage(db: Session, p: Project, user: User) -> None:
    if p.owner_id == user.id:
        return
    m = team_repository.get_membership(db, p.team_id, user.id) if p.team_id else None
    if m is None or RANK[m.role] < RANK["admin"]:
        raise ForbiddenError("Only the project owner or a team admin can modify this project.")


def create(db: Session, user: User, name: str, description: str | None, team_id: int | None) -> Project:
    if team_id is not None and not team_repository.get_membership(db, team_id, user.id):
        raise ForbiddenError("You are not a member of that team.")
    p = Project(name=name, description=description, owner_id=user.id, team_id=team_id)
    db.add(p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("You already have a project with that name.")
    return p


def update(db: Session, project_id: int, user: User, data: dict) -> Project:
    p = get_accessible(db, project_id, user)
    _require_manage(db, p, user)
    for k, v in data.items():
        setattr(p, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("You already have a project with that name.")
    return p


def delete(db: Session, project_id: int, user: User) -> None:
    p = get_accessible(db, project_id, user)
    _require_manage(db, p, user)
    db.delete(p)
    db.commit()
