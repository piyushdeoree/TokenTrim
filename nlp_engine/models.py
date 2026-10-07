"""
models.py - data structures.

Two layers:

1. The BACKEND CONTRACT  (PromptRequest, Issue, AnalysisResponse)
   Exactly the fields agreed with Person 3 / Person 4. Do not add fields here
   without discussing integration implications.

2. The DETAILED layer (DetailedAnalysis and friends)
   Richer, explainable output for the demo, the report and debugging.
   Not part of the backend contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .config import DEFAULT_MODEL
from .textutils import PreparedPrompt

Severity = Literal["low", "medium", "high"]


# ----------------------------- backend contract -----------------------------
class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: str = DEFAULT_MODEL


class Issue(BaseModel):
    type: str
    severity: Severity
    description: str


class AnalysisResponse(BaseModel):
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    reduction_percentage: float
    word_count: int
    complexity_score: float
    issues: List[Issue]
    suggestions: List[str]
    optimized_prompt: str


# ------------------------------- detailed layer -----------------------------
class TokenStats(BaseModel):
    input_tokens: int
    word_count: int
    character_count: int
    sentence_count: int
    method: str
    exact: bool
    note: str = ""


class ComplexityFeatures(BaseModel):
    token_count: int
    instruction_count: int
    constraint_count: int
    avg_sentence_length: float
    max_sentence_length: int
    structure_depth: int
    code_block_count: int
    repeated_phrase_ratio: float
    context_tokens: int
    instruction_tokens: int
    context_to_instruction_ratio: float
    format_directive_count: int


class DetailedIssue(Issue):
    evidence: List[str] = []


class OptimizationResult(BaseModel):
    optimized_prompt: str
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    reduction_percentage: float
    changes: List[str] = []
    method: str = "heuristic"          # heuristic | llm | none


class ValidationResult(BaseModel):
    is_valid: bool
    reasons: List[str] = []
    metrics: Dict[str, float] = {}


class DetailedAnalysis(BaseModel):
    token_stats: TokenStats
    features: ComplexityFeatures
    complexity_score: float
    complexity_label: str
    issues: List[DetailedIssue]
    suggestions: List[str]
    candidate: OptimizationResult       # what the optimizer proposed
    validation: ValidationResult        # verdict of the safety check
    final: OptimizationResult           # what is returned to the backend
    optimization_accepted: bool


# ------------------------------ internal state ------------------------------
@dataclass
class Finding:
    """One detector hit (turned into an Issue by the analyzer)."""
    type: str
    severity: str
    description: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class PromptAnalysis:
    """Everything the optimizer needs, produced by ``analyzer.build_analysis``."""
    prompt: str
    model: str
    prepared: PreparedPrompt
    token_stats: TokenStats
    findings: List[Finding] = field(default_factory=list)
    features: Optional[ComplexityFeatures] = None
    complexity_score: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)
