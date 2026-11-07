from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import check_rate_limit
from app.database.session import get_db
from app.models.user import User
from app.schemas.prompt import AnalyzeRequest, AnalyzeResponse
from app.services import analysis_service

router = APIRouter(prefix="/api", tags=["Prompt analysis"])


@router.post("/analyze-prompt", response_model=AnalyzeResponse,
             summary="Analyze and optimize a prompt, estimate cost, and record usage")
def analyze_prompt(body: AnalyzeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_rate_limit(f"analyze:{user.id}")
    return analysis_service.analyze_prompt(db, user, body)
