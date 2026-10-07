"""Authorization rules for teams and projects (enforced server-side)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import forbidden, not_found
from app.models import Project, Team, TeamMember, User

ROLE_RANK = {"member": 1, "admin": 2, "owner": 3}


def team_role(db: Session, team_id: int, user_id: int) -> str | None:
    return db.scalar(select(TeamMember.role).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id))


def require_team_role(db: Session, team_id: int, user: User, min_role: str = "member") -> str:
    """Non-members get 404 (team existence is not leaked); members with too low a role get 403."""
    if db.get(Team, team_id) is None:
        raise not_found("team")
    role = team_role(db, team_id, user.id)
    if role is None:
        raise not_found("team")
    if ROLE_RANK[role] < ROLE_RANK[min_role]:
        raise forbidden()
    return role


def get_project_or_404(db: Session, user: User, project_id: int, write: bool = False) -> Project:
    """Read: owner or any team member. Write/delete: owner or team admin/owner."""
    project = db.get(Project, project_id)
    if project is None:
        raise not_found("project")
    if project.owner_id == user.id:
        return project
    if project.team_id is not None:
        role = team_role(db, project.team_id, user.id)
        if role is not None:
            if write and ROLE_RANK[role] < ROLE_RANK["admin"]:
                raise forbidden()
            return project
    raise not_found("project")
