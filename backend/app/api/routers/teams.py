"""Permission matrix
  owner : everything (add admin/member, change roles, remove anyone but themselves, delete team)
  admin : add/remove plain members, list members
  member: list members, leave the team
Exactly one owner (the creator); ownership cannot be assigned or removed through the API."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError, forbidden, not_found
from app.database.session import get_db
from app.models import Team, TeamMember, User
from app.repositories.crud import get_user_by_email
from app.schemas.schemas import MemberAdd, MemberOut, MemberRoleUpdate, TeamCreate, TeamOut
from app.services.access import ROLE_RANK, require_team_role

router = APIRouter(prefix="/teams", tags=["Teams"])


def _member_out(m: TeamMember, u: User) -> MemberOut:
    return MemberOut(user_id=u.id, email=u.email, full_name=u.full_name, role=m.role, joined_at=m.joined_at)


@router.post("", response_model=TeamOut, status_code=201, summary="Create a team (you become the owner)")
def create_team(body: TeamCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team = Team(name=body.name.strip(), created_by=user.id)
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=user.id, role="owner"))
    db.commit()
    return TeamOut(id=team.id, name=team.name, created_at=team.created_at, my_role="owner")


@router.get("", response_model=list[TeamOut], summary="Teams you belong to")
def list_teams(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Team, TeamMember.role).join(TeamMember, TeamMember.team_id == Team.id)
                      .where(TeamMember.user_id == user.id).order_by(Team.id)).all()
    return [TeamOut(id=t.id, name=t.name, created_at=t.created_at, my_role=r) for t, r in rows]


@router.delete("/{team_id}", status_code=204, summary="Delete a team (owner only)")
def delete_team(team_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_team_role(db, team_id, user, "owner")
    db.delete(db.get(Team, team_id))
    db.commit()
    return Response(status_code=204)


@router.get("/{team_id}/members", response_model=list[MemberOut], summary="List members (any member)")
def list_members(team_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_team_role(db, team_id, user, "member")
    rows = db.execute(select(TeamMember, User).join(User, User.id == TeamMember.user_id)
                      .where(TeamMember.team_id == team_id).order_by(TeamMember.id)).all()
    return [_member_out(m, u) for m, u in rows]


@router.post("/{team_id}/members", response_model=MemberOut, status_code=201,
             summary="Add/invite a registered user by email (owner/admin; only the owner can add admins)")
def add_member(team_id: int, body: MemberAdd, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    actor = require_team_role(db, team_id, user, "admin")
    if body.role == "admin" and actor != "owner":
        raise forbidden("Only the team owner can add admins.")
    target = get_user_by_email(db, body.email)
    if target is None:
        raise not_found("user")
    if db.scalar(select(TeamMember.id).where(TeamMember.team_id == team_id, TeamMember.user_id == target.id)):
        raise AppError(409, "ALREADY_MEMBER", "This user is already a member of the team.")
    m = TeamMember(team_id=team_id, user_id=target.id, role=body.role)
    db.add(m)
    db.commit()
    return _member_out(m, target)


@router.patch("/{team_id}/members/{user_id}", response_model=MemberOut, summary="Change a member's role (owner only)")
def change_role(team_id: int, user_id: int, body: MemberRoleUpdate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    require_team_role(db, team_id, user, "owner")
    m = db.scalar(select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id))
    if m is None:
        raise not_found("member")
    if m.role == "owner":
        raise forbidden("The owner's role cannot be changed.")
    m.role = body.role
    db.commit()
    return _member_out(m, db.get(User, user_id))


@router.delete("/{team_id}/members/{user_id}", status_code=204,
               summary="Remove a member (owner: anyone but self; admin: plain members; anyone: leave)")
def remove_member(team_id: int, user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    actor = require_team_role(db, team_id, user, "member")
    m = db.scalar(select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id))
    if m is None:
        raise not_found("member")
    if m.role == "owner":
        raise forbidden("The owner cannot be removed. Delete the team instead.")
    if user_id != user.id and not (actor == "owner" or (actor == "admin" and ROLE_RANK[m.role] == 1)):
        raise forbidden()
    db.delete(m)
    db.commit()
    return Response(status_code=204)
