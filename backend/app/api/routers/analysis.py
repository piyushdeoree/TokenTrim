from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import analyze_limit
from app.database.session import get_db
from app.models import User
from app.schemas.schemas import AnalyzeRequest, AnalyzeResponse
from app.services import analysis_service

router = APIRouter(tags=["Analysis"])


@router.post("/api/analyze-prompt", response_model=AnalyzeResponse, dependencies=[Depends(analyze_limit)],
             summary="Analyze + optimize a prompt and estimate its cost",
             description="Orchestrates the NLP engine and the cost/ML engine, stores the result and returns a combined "
                         "response. `estimated_cost` is the predicted cost of the ORIGINAL prompt; `potential_saving` "
                         "is how much cheaper the optimized prompt would be.",
             responses={401: {"description": "Not authenticated"}, 404: {"description": "Unknown model or project"},
                        422: {"description": "Invalid prompt / missing model"},
                        429: {"description": "Rate limit exceeded"},
                        502: {"description": "NLP or ML service failure"}})
def analyze_prompt(body: AnalyzeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analysis_service.analyze_prompt(db, user, body)
