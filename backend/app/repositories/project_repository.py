from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories import team_repository


def get(db: Session, project_id: int) -> Project | None:
    return db.get(Project, project_id)


def list_accessible(db: Session, user_id: int) -> list[Project]:
    team_ids = team_repository.team_ids_for_user(db, user_id)
    return list(db.scalars(
        select(Project).where(or_(Project.owner_id == user_id, Project.team_id.in_(team_ids))).order_by(Project.id)
    ))


def accessible_ids(db: Session, user_id: int) -> list[int]:
    return [p.id for p in list_accessible(db, user_id)]
