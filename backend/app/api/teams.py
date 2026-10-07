from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories import team_repository
from app.schemas.team import MemberInvite, MemberOut, MemberRoleUpdate, TeamCreate, TeamOut
from app.services import team_service

router = APIRouter(prefix="/teams", tags=["Teams"])


def _team_out(team, role) -> TeamOut:
    return TeamOut(id=team.id, name=team.name, owner_id=team.owner_id, my_role=role, created_at=team.created_at)


def _member_out(m, u) -> MemberOut:
    return MemberOut(user_id=u.id, email=u.email, full_name=u.full_name, role=m.role, joined_at=m.joined_at)


@router.post("", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(body: TeamCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _team_out(*team_service.create_team(db, user, body.name))


@router.get("", response_model=list[TeamOut], summary="Teams you belong to")
def list_teams(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_team_out(t, r) for t, r in team_repository.list_for_user(db, user.id)]


@router.get("/{team_id}", response_model=TeamOut)
def get_team(team_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = team_service.require_role(db, team_id, user, "member")
    return _team_out(m.team, m.role)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete team (owner only)")
def delete_team(team_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team_service.delete_team(db, team_id, user)


@router.get("/{team_id}/members", response_model=list[MemberOut])
def list_members(team_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team_service.require_role(db, team_id, user, "member")
    return [_member_out(m, u) for m, u in team_repository.list_members(db, team_id)]


@router.post("/{team_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED,
             summary="Invite a registered user by email (admin+; only the owner can add admins)")
def invite_member(team_id: int, body: MemberInvite, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return _member_out(*team_service.invite_member(db, team_id, user, body.email, body.role))


@router.patch("/{team_id}/members/{user_id}", response_model=MemberOut, summary="Change a member's role (owner only)")
def change_role(team_id: int, user_id: int, body: MemberRoleUpdate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    m = team_service.change_role(db, team_id, user, user_id, body.role)
    return _member_out(m, m.user)


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Remove a member (admin+), or leave the team yourself")
def remove_member(team_id: int, user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team_service.remove_member(db, team_id, user, user_id)
