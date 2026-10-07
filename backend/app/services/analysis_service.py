from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, DatabaseError
from app.models.prompt import Prompt, PromptAnalysis
from app.models.usage import CostRecord, UsageRecord
from app.models.user import User
from app.repositories import model_repository
from app.schemas.prompt import AnalyzeRequest, AnalyzeResponse
from app.services import cost_service, model_service, nlp_service, project_service


def _dec(x: float) -> Decimal:
    return Decimal(str(round(x, 8)))


def analyze_prompt(db: Session, user: User, req: AnalyzeRequest) -> AnalyzeResponse:
    # 1. validate model, pricing and project access
    model = model_repository.get_by_name(db, req.model)
    if model is None:
        raise BadRequestError(f"Unknown or inactive model '{req.model}'. See GET /models.")
    pricing = model_service.current_pricing(model)
    if pricing is None:
        raise BadRequestError(f"No pricing is configured for model '{req.model}'.")
    project = project_service.get_accessible(db, req.project_id, user) if req.project_id else None

    # 2-3. NLP engine: token analysis + optimized prompt
    nlp = nlp_service.analyze(req.prompt, model.name)
    original, optimized = nlp["original_tokens"], nlp["optimized_tokens"]

    # 4-6. cost engine: predicted output, cost of original vs optimized prompt
    predicted = cost_service.predict_output_tokens(req.prompt, model.name, original)
    p_in, p_out = float(pricing.input_price_per_1k), float(pricing.output_price_per_1k)
    cost_original = cost_service.estimate_cost(original, predicted, p_in, p_out, model.name)
    cost_optimized = cost_service.estimate_cost(optimized, predicted, p_in, p_out, model.name)
    saving = max(0.0, cost_original - cost_optimized)

    saved = max(0, original - optimized)
    reduction = round(saved / original * 100, 2) if original > 0 else 0.0

    # 7. persist everything atomically
    try:
        prompt = Prompt(user_id=user.id, project_id=project.id if project else None, model_id=model.id,
                        original_text=req.prompt, optimized_text=nlp["optimized_prompt"])
        prompt.analysis = PromptAnalysis(
            original_tokens=original, optimized_tokens=optimized, tokens_saved=saved,
            reduction_percentage=reduction, predicted_output_tokens=predicted,
            issues=nlp["issues"], suggestions=nlp["suggestions"])
        db.add(prompt)
        db.flush()
        usage = UsageRecord(
            user_id=user.id, project_id=prompt.project_id, team_id=project.team_id if project else None,
            model_id=model.id, prompt_id=prompt.id, input_tokens=original, output_tokens=predicted,
            total_tokens=original + predicted)
        usage.cost = CostRecord(
            pricing_id=pricing.id, estimated_cost=_dec(cost_original), optimized_cost=_dec(cost_optimized),
            potential_saving=_dec(saving), currency=pricing.currency)
        db.add(usage)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise DatabaseError("Could not save analysis results.")

    # 8. combined response
    return AnalyzeResponse(
        original_tokens=original, optimized_tokens=optimized, tokens_saved=saved,
        reduction_percentage=reduction, predicted_output_tokens=predicted,
        estimated_cost=cost_original, potential_saving=saving,
        issues=nlp["issues"], suggestions=nlp["suggestions"], optimized_prompt=nlp["optimized_prompt"])
