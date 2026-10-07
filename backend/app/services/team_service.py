from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.team import Team, TeamMember
from app.models.user import User
from app.repositories import team_repository, user_repository

RANK = {"member": 1, "admin": 2, "owner": 3}


def require_role(db: Session, team_id: int, user: User, minimum: str) -> TeamMember:
    """Returns the caller's membership, or raises 404 (not a member) / 403 (role too low)."""
    if team_repository.get(db, team_id) is None:
        raise NotFoundError("Team not found.")
    m = team_repository.get_membership(db, team_id, user.id)
    if m is None:
        raise NotFoundError("Team not found.")  # don't reveal teams the caller can't see
    if RANK[m.role] < RANK[minimum]:
        raise ForbiddenError(f"Requires {minimum} role or higher.")
    return m


def create_team(db: Session, user: User, name: str) -> tuple[Team, str]:
    team = Team(name=name, owner_id=user.id)
    team.members.append(TeamMember(user_id=user.id, role="owner"))
    db.add(team)
    db.commit()
    return team, "owner"


def invite_member(db: Session, team_id: int, caller: User, email: str, role: str):
    caller_m = require_role(db, team_id, caller, "admin")
    if role == "admin" and caller_m.role != "owner":
        raise ForbiddenError("Only the owner can add admins.")
    target = user_repository.get_by_email(db, email)
    if target is None:
        raise NotFoundError("No registered user with that email.")
    if team_repository.get_membership(db, team_id, target.id):
        raise ConflictError("User is already a team member.")
    m = TeamMember(team_id=team_id, user_id=target.id, role=role)
    db.add(m)
    db.commit()
    return m, target


def remove_member(db: Session, team_id: int, caller: User, target_user_id: int) -> None:
    caller_m = require_role(db, team_id, caller, "member")
    target = team_repository.get_membership(db, team_id, target_user_id)
    if target is None:
        raise NotFoundError("Member not found.")
    if target.role == "owner":
        raise BadRequestError("The owner cannot be removed. Delete the team instead.")
    if target_user_id != caller.id:  # removing someone else needs authority over them
        if caller_m.role == "member":
            raise ForbiddenError("Requires admin role or higher.")
        if caller_m.role == "admin" and target.role != "member":
            raise ForbiddenError("Admins can only remove regular members.")
    db.delete(target)
    db.commit()


def change_role(db: Session, team_id: int, caller: User, target_user_id: int, role: str) -> TeamMember:
    require_role(db, team_id, caller, "owner")
    target = team_repository.get_membership(db, team_id, target_user_id)
    if target is None:
        raise NotFoundError("Member not found.")
    if target.role == "owner":
        raise BadRequestError("The owner's role cannot be changed.")
    target.role = role
    db.commit()
    return target


def delete_team(db: Session, team_id: int, caller: User) -> None:
    require_role(db, team_id, caller, "owner")
    db.delete(team_repository.get(db, team_id))
    db.commit()
