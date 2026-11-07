from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import AIModel, ModelPricing, Project, TeamMember, UsageRecord, User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_model_by_name(db: Session, name: str) -> AIModel | None:
    return db.scalar(select(AIModel).where(AIModel.name == name))


def current_pricing(db: Session, model_id: int) -> ModelPricing | None:
    return db.scalar(
        select(ModelPricing)
        .where(ModelPricing.model_id == model_id, ModelPricing.effective_from <= datetime.now(timezone.utc))
        .order_by(ModelPricing.effective_from.desc())
        .limit(1)
    )


def accessible_project_ids(user: User):
    """Subquery: projects the user owns or can see through a team membership."""
    my_teams = select(TeamMember.team_id).where(TeamMember.user_id == user.id)
    return select(Project.id).where(or_(Project.owner_id == user.id, Project.team_id.in_(my_teams)))


def usage_scope(user: User):
    return or_(UsageRecord.user_id == user.id, UsageRecord.project_id.in_(accessible_project_ids(user)))
