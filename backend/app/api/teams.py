import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.team import TeamInvitation, TeamMember
from app.repositories import team_repository
from app.schemas.team import InvitationAccept, InvitationCreate, MemberInvite, MemberOut, MemberRoleUpdate, TeamCreate, TeamOut
from app.services import team_service

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.post("/invitations/accept", summary="Accept an invitation (recipient must be signed in with the invited email)")
def accept_invitation(body: InvitationAccept, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    invitation = db.scalar(select(TeamInvitation).where(TeamInvitation.token_hash == token_hash))
    now = datetime.now(timezone.utc)
    if invitation is None or invitation.revoked_at or invitation.accepted_at:
        raise HTTPException(status_code=404, detail="Invitation is invalid or no longer active")
    expires = invitation.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= now:
        raise HTTPException(status_code=410, detail="Invitation has expired")
    if user.email.lower() != invitation.email.lower():
        raise HTTPException(status_code=403, detail="Sign in with the email address that was invited")
    exists = db.scalar(select(TeamMember.id).where(TeamMember.team_id == invitation.team_id, TeamMember.user_id == user.id))
    if exists:
        raise HTTPException(status_code=409, detail="You are already a member of this team")
    db.add(TeamMember(team_id=invitation.team_id, user_id=user.id, role=invitation.role))
    invitation.accepted_at = now
    db.commit()
    return {"team_id": invitation.team_id, "role": invitation.role, "accepted": True}


@router.post("/invitations/reject", summary="Reject an invitation (recipient must be signed in with the invited email)")
def reject_invitation(body: InvitationAccept, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    invitation = db.scalar(select(TeamInvitation).where(TeamInvitation.token_hash == token_hash))
    if invitation is None or invitation.revoked_at or invitation.accepted_at:
        raise HTTPException(status_code=404, detail="Invitation is invalid or no longer active")
    if user.email.lower() != invitation.email.lower():
        raise HTTPException(status_code=403, detail="Sign in with the email address that was invited")
    invitation.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return {"rejected": True}


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


@router.post("/{team_id}/invitations", status_code=201, summary="Create a secure, expiring invitation (token shown once; no email is sent)")
def create_invitation(team_id: int, body: InvitationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = team_service.require_role(db, team_id, user, "admin")
    if body.role == "admin" and membership.role != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can invite admins")
    existing = db.scalar(select(TeamInvitation.id).where(
        TeamInvitation.team_id == team_id, TeamInvitation.email == body.email.lower(),
        TeamInvitation.accepted_at.is_(None), TeamInvitation.revoked_at.is_(None),
        TeamInvitation.expires_at > datetime.now(timezone.utc)))
    if existing:
        raise HTTPException(status_code=409, detail="An active invitation already exists for this email")
    raw = secrets.token_urlsafe(32)
    invitation = TeamInvitation(team_id=team_id, email=body.email.lower(), role=body.role,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(), created_by=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7))
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return {"id": invitation.id, "team_id": team_id, "email": invitation.email, "role": invitation.role,
        "created_at": invitation.created_at, "expires_at": invitation.expires_at,
        "token": raw, "delivery": "not_sent"}


@router.get("/{team_id}/invitations", summary="List invitation metadata (never returns token hashes)")
def list_invitations(team_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team_service.require_role(db, team_id, user, "admin")
    invitations = db.scalars(select(TeamInvitation).where(TeamInvitation.team_id == team_id)
        .order_by(TeamInvitation.created_at.desc())).all()
    return [{"id": i.id, "email": i.email, "role": i.role, "created_at": i.created_at,
        "expires_at": i.expires_at, "accepted_at": i.accepted_at, "revoked_at": i.revoked_at}
        for i in invitations]


@router.delete("/{team_id}/invitations/{invitation_id}", status_code=204, summary="Revoke a pending invitation")
def revoke_invitation(team_id: int, invitation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team_service.require_role(db, team_id, user, "admin")
    invitation = db.scalar(select(TeamInvitation).where(TeamInvitation.id == invitation_id, TeamInvitation.team_id == team_id))
    if invitation is None or invitation.accepted_at is not None:
        raise HTTPException(status_code=404, detail="Pending invitation not found")
    invitation.revoked_at = datetime.now(timezone.utc)
    db.commit()


@router.patch("/{team_id}/members/{user_id}", response_model=MemberOut, summary="Change a member's role (owner only)")
def change_role(team_id: int, user_id: int, body: MemberRoleUpdate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    m = team_service.change_role(db, team_id, user, user_id, body.role)
    return _member_out(m, m.user)


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Remove a member (admin+), or leave the team yourself")
def remove_member(team_id: int, user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team_service.remove_member(db, team_id, user, user_id)
