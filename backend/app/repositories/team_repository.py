from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.team import Team, TeamMember
from app.models.user import User


def get(db: Session, team_id: int) -> Team | None:
    return db.get(Team, team_id)


def get_membership(db: Session, team_id: int, user_id: int) -> TeamMember | None:
    return db.scalar(select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id))


def list_for_user(db: Session, user_id: int) -> list[tuple[Team, str]]:
    rows = db.execute(
        select(Team, TeamMember.role).join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user_id).order_by(Team.id)
    ).all()
    return [(t, r) for t, r in rows]


def list_members(db: Session, team_id: int) -> list[tuple[TeamMember, User]]:
    rows = db.execute(
        select(TeamMember, User).join(User, User.id == TeamMember.user_id)
        .where(TeamMember.team_id == team_id).order_by(TeamMember.id)
    ).all()
    return [(m, u) for m, u in rows]


def team_ids_for_user(db: Session, user_id: int) -> list[int]:
    return list(db.scalars(select(TeamMember.team_id).where(TeamMember.user_id == user_id)))
