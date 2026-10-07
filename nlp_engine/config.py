"""
config.py - central, documented configuration for the NLP engine.

Everything that is a *tunable decision* (thresholds, word lists, rewrite
rules, weights) lives here, so that it can be explained in the project report
and changed without touching the algorithms.

NOTE: all thresholds and weights below are heuristic design choices made by the
authors. They are NOT learned from data and no accuracy claim is made for them.
"""
from __future__ import annotations

import re


def _rx(pattern: str, flags: int = re.IGNORECASE) -> "re.Pattern[str]":
    return re.compile(pattern, flags)


# ---------------------------------------------------------------------------
# 1. Tokenizer configuration
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "gpt-4o"

# Fallback table used only when tiktoken does not know the model name itself.
# (model-name prefix, tiktoken encoding). Order matters: first match wins.
OPENAI_PREFIX_ENCODINGS = (
    ("gpt-4o", "o200k_base"),
    ("gpt-4.1", "o200k_base"),
    ("gpt-4.5", "o200k_base"),
    ("o1", "o200k_base"),
    ("o3", "o200k_base"),
    ("o4", "o200k_base"),
    ("gpt-4", "cl100k_base"),
    ("gpt-3.5", "cl100k_base"),
)

# ---------------------------------------------------------------------------
# 2. Detection thresholds
# ---------------------------------------------------------------------------
# Cosine similarity (on binary stem vectors) at/above which two clauses are
# reported as "similar". Removal additionally requires strict subsumption.
SIMILARITY_THRESHOLD_INSTRUCTION = 0.60
SIMILARITY_THRESHOLD_CONSTRAINT = 0.75

# Repeated phrase detection (n-gram window, in words)
REPEATED_PHRASE_MIN_WORDS = 3
REPEATED_PHRASE_MAX_WORDS = 8
REPEATED_PHRASE_MIN_COUNT = 2
REPEATED_PHRASE_MAX_REPORTED = 5

# Excessive context: flagged only if BOTH conditions hold
CONTEXT_MIN_TOKENS = 400          # absolute size of the context
CONTEXT_RATIO_THRESHOLD = 5.0     # context tokens / instruction tokens
CONTEXT_HIGH_TOKENS = 3000        # -> severity "medium"/"high"

# Formatting overload: number of DISTINCT formatting directives
FORMAT_DIRECTIVE_THRESHOLD = 3
FORMAT_DIRECTIVE_HIGH = 6

# Very long sentences
LONG_SENTENCE_WORDS = 40

# ---------------------------------------------------------------------------
# 3. Complexity score (0-100) = 100 * sum(weight_i * min(feature_i / cap_i, 1))
# ---------------------------------------------------------------------------
COMPLEXITY_CAPS = {
    "token_count": 2000.0,
    "instruction_count": 10.0,
    "constraint_count": 8.0,
    "avg_sentence_length": 30.0,
    "structure_depth": 4.0,
    "repeated_phrase_ratio": 0.30,
    "context_to_instruction_ratio": 10.0,
    "format_directive_count": 6.0,
}
COMPLEXITY_WEIGHTS = {
    "token_count": 0.20,
    "instruction_count": 0.15,
    "constraint_count": 0.15,
    "avg_sentence_length": 0.10,
    "structure_depth": 0.10,
    "repeated_phrase_ratio": 0.10,
    "context_to_instruction_ratio": 0.10,
    "format_directive_count": 0.10,
}
assert abs(sum(COMPLEXITY_WEIGHTS.values()) - 1.0) < 1e-9
COMPLEXITY_BANDS = ((33.0, "low"), (66.0, "medium"), (101.0, "high"))

# ---------------------------------------------------------------------------
# 4. Validation thresholds
# ---------------------------------------------------------------------------
KEYWORD_COVERAGE_MIN = 0.90       # share of original content stems still present
CONSTRAINT_COVERAGE_MIN = 0.85    # per constraint sentence
MIN_LEXICAL_SIMILARITY = 0.35     # TF-IDF cosine(original, optimized)

# ---------------------------------------------------------------------------
# 5. Linguistic resources
# ---------------------------------------------------------------------------
# Words ignored when comparing clauses / measuring keyword coverage.
STOPWORDS = frozenset("""
a an the this that these those it its they them their i me my we us our you your
is are was were be been being am to of in on at for with by from as and or but
so if then than also please kindly would could should must will can shall may might
like want need make sure ensure keep carefully really very just basically actually
simply essentially following there here some any do does did have has had get let
into onto such own same too
""".split())

# Words treated as filler (removed by the rewriter, ignored by the matcher)
FILLER_WORDS = frozenset(
    ["please", "kindly", "carefully", "basically", "essentially", "really", "actually", "simply"]
)
FILLER_RE = _rx(r"\b(?:" + "|".join(sorted(FILLER_WORDS)) + r")\b[,]?\s*")

CONNECTIVES = frozenset(
    ["now", "then", "also", "next", "so", "and", "first", "finally", "afterwards",
     "additionally", "lastly", "second", "third", "firstly", "secondly"]
)

# Verbs that make a sentence an instruction when they are its first word.
INSTRUCTION_VERBS = frozenset("""
analyze summarize explain write list generate create return give provide describe
translate extract classify compare identify tell show find rewrite improve fix debug
implement build design develop convert calculate compute determine evaluate review
suggest recommend outline draft answer respond reply output format include use produce
check paraphrase rank sort predict assess critique edit proofread simplify expand
define discuss illustrate demonstrate propose plan solve reason justify categorize
categorise tag label parse generate select choose complete continue fill refactor
optimize optimise test document annotate transcribe
""".split())

# Safer subset used to split "do A and do B" inside one sentence. Words that are
# very commonly nouns ("use", "list", "output", "format"...) are deliberately excluded.
SPLIT_VERBS = frozenset("""
analyze summarize explain write generate create provide describe translate extract
classify compare identify rewrite convert calculate determine evaluate suggest
recommend return give tell paraphrase categorize categorise
""".split())

# Words that start a constraint-style sentence.
CONSTRAINT_HEADS = frozenset(
    ["not", "never", "always", "only", "avoid", "keep", "limit", "stay", "be", "ensure", "remember"]
)

CONSTRAINT_RE = _rx(
    r"\b(?:must|should|shall|ensure|do not|don't|never|always|avoid|without|only)\b"
    r"|\b(?:at most|at least|no more than|no fewer than|maximum of|minimum of|exactly|under|within|up to)\s+\d+"
    r"|\b\d+\s*(?:words?|sentences?|paragraphs?|bullet points?|bullets?|characters?|lines?|items?|tokens?)\b"
)

# Pairwise clause comparison is O(n^2). A prompt with more comparable clauses than
# this is almost certainly data, not instructions, so pairwise de-duplication is skipped.
MAX_CLAUSES_FOR_PAIRWISE = 300

NEGATION_RE = _rx(
    r"\b(?:not|no|never|without|avoid|except|exclude|excluding|don't|dont|doesn't|cannot|can't|"
    r"shouldn't|mustn't|won't)\b"
)
NEGATION_WORDS = ("not", "no", "never", "without", "avoid", "except", "exclude", "don't", "cannot", "can't")

# Canonicalisation applied (in this order) to lower-cased text before comparison.
CANONICAL_PHRASES = [
    (_rx(r"\bmake sure(?: that)?\b"), " ensure "),
    (_rx(r"(?:(?:do|must|should|shall|can|could)\s*(?:not|n't)\s+)?(?:not\s+)?\bexceed(?:ing|s)?\b"), " maxlimit "),
    (_rx(r"\b(?:no more than|at most|up to|less than|fewer than|under|below|within|maximum of|"
         r"maximum|max|limit(?:ed)? it to|limit(?:ed)? to|limit|capped at)\b"), " maxlimit "),
    (_rx(r"\b(?:at least|no fewer than|no less than|minimum of|minimum|min|more than)\b"), " minlimit "),
    (_rx(r"\b(?:do not|don't|dont|doesn't|does not|never|cannot|can't|can not|shouldn't|"
         r"should not|mustn't|must not|won't|will not|isn't|aren't)\b"), " not "),
    (_rx(r"\bstep[- ]by[- ]step\b"), " stepbystep "),
    (_rx(r"\bbullet(?:ed)?\s+(?:points?|lists?)\b|\bbullets\b"), " bulletpoints "),
    (_rx(r"\bplain[- ]text\b"), " plaintext "),
]

# Light synonym folding so that "response"/"answer"/"output" compare equal.
SYNONYMS = {
    "response": "answer", "responses": "answer", "reply": "answer", "replies": "answer",
    "output": "answer", "result": "answer", "results": "answer",
    "summary": "summarize", "summaries": "summarize", "summarise": "summarize",
    "summarization": "summarize", "summarisation": "summarize",
    "explanation": "explain", "explanations": "explain",
    "analysis": "analyze", "analyse": "analyze", "analyses": "analyze",
    "description": "describe", "descriptions": "describe",
    "brief": "concise", "succinct": "concise", "terse": "concise", "short": "concise",
    "comprehensive": "detailed", "thorough": "detailed", "elaborate": "detailed",
}

# ---------------------------------------------------------------------------
# 6. Rewrite rules (heuristic optimisation)
# ---------------------------------------------------------------------------
# Polite / verbose lead-ins. Only stripped when the next content word is an
# instruction verb, so "I would like to know..." is never touched.
LEADIN_RE = _rx(
    r"^(?:(?:so|now|then|also|next|and)[,]?\s+)?(?:(?:please|kindly)[,]?\s+)*"
    r"(?:"
    r"(?:i|we)\s+(?:would|'d|will)\s+(?:like|love|appreciate)\s+(?:it\s+if\s+)?(?:you\s+)?(?:to\s+|would\s+)?"
    r"|(?:i|we)\s+(?:want|need|require|expect)\s+you\s+to\s+"
    r"|(?:could|can|would|will)\s+you\s+(?:please\s+|kindly\s+)*(?:also\s+)?"
    r"|(?:i\s+am|i'm)\s+(?:looking|asking)\s+(?:for\s+)?you\s+to\s+"
    r")"
)

# (label, compiled pattern, replacement). Applied in order on instruction-like
# sentences only (never on context, code, quotes, URLs, JSON...).
VERBOSE_RULES = [
    ("'provide me with an explanation of' -> 'explain'",
     _rx(r"\b(?:provide|give)\s+me\s+(?:with\s+)?(?:an?\s+)?explanation\s+of\b"), "explain"),
    ("'provide me with a summary of' -> 'summarize'",
     _rx(r"\b(?:provide|give)\s+me\s+(?:with\s+)?(?:an?\s+)?summary\s+of\b"), "summarize"),
    ("'provide me with a description of' -> 'describe'",
     _rx(r"\b(?:provide|give)\s+me\s+(?:with\s+)?(?:an?\s+)?description\s+of\b"), "describe"),
    ("'provide me with an analysis of' -> 'analyze'",
     _rx(r"\b(?:provide|give)\s+me\s+(?:with\s+)?(?:an?\s+)?analysis\s+of\b"), "analyze"),
    ("'provide me with' -> 'provide'", _rx(r"\bprovide\s+me\s+(?:with\s+)?"), "provide "),
    ("'make sure that' -> 'ensure'", _rx(r"\bmake\s+sure\s+(?:that\s+)?(?!to\b)"), "ensure "),
    ("'in order to' -> 'to'", _rx(r"\bin\s+order\s+to\b"), "to"),
    ("'due to the fact that' -> 'because'", _rx(r"\bdue\s+to\s+the\s+fact\s+that\b"), "because"),
    ("'in spite of the fact that' -> 'although'", _rx(r"\bin\s+spite\s+of\s+the\s+fact\s+that\b"), "although"),
    ("'at this point in time' -> 'now'", _rx(r"\bat\s+this\s+point\s+in\s+time\b"), "now"),
    ("'for the purpose of' -> 'for'", _rx(r"\bfor\s+the\s+purpose\s+of\b"), "for"),
    ("'a large number of' -> 'many'", _rx(r"\ban?\s+(?:large|great|good)\s+number\s+of\b"), "many"),
    ("'the majority of' -> 'most'", _rx(r"\bthe\s+majority\s+of\b"), "most"),
    ("'in the event that' -> 'if'", _rx(r"\bin\s+the\s+event\s+that\b"), "if"),
    ("'with regard/respect to' -> 'about'", _rx(r"\bwith\s+(?:regard|respect)\s+to\b"), "about"),
    ("'is/are able to' -> 'can'", _rx(r"\b(?:is|are)\s+able\s+to\b"), "can"),
    ("'each and every' -> 'every'", _rx(r"\beach\s+and\s+every\b"), "every"),
    ("'first and foremost' -> 'first'", _rx(r"\bfirst\s+and\s+foremost\b"), "first"),
    ("'and also' -> 'and'", _rx(r"\band\s+also\b"), "and"),
    ("'it is important to note that' -> (removed)",
     _rx(r"\bit\s+(?:is\s+important\s+to\s+(?:note|remember)|should\s+be\s+noted)\s+that\s+"), ""),
    ("'feel free to' -> (removed)", _rx(r"\bfeel\s+free\s+to\s+"), ""),
]

# A *generic* persona sentence carries no task information, so it may be dropped.
# Specific personas ("You are an expert Python developer.") never match this.
GENERIC_PERSONA_RE = _rx(
    r"^\s*you\s+are\s+(?:an?|the)\s+(?:(?:very|highly|extremely)\s+)?"
    r"(?:(?:expert|helpful|friendly|professional|intelligent|smart|knowledgeable|useful|capable|"
    r"skilled|experienced|world[- ]class|great|good|honest|harmless)\s*,?\s*(?:and\s+)?)*"
    r"(?:ai\s+)?(?:assistant|ai|chatbot|language\s+model|llm|bot|helper)\s*[.!]?\s*$"
)
ROLE_RE = _rx(r"^\s*(?:you\s+are|act\s+as|as\s+an?|your\s+role\s+is|pretend\s+(?:to\s+be|you\s+are)|imagine\s+you\s+are)\b")

# Label lines that introduce a block of user content ("Text: ...", "Context: ...")
LABEL_RE = _rx(
    r"^\s*(?:text|context|document|article|passage|input|data|content|email|code|transcript|report|"
    r"review|story|background|source|excerpt|essay|paragraph|message|conversation|notes?)\s*[:\-]\s*"
)
CONTEXT_INTRO_RE = _rx(
    r"\b(?:following|below|here\s+is|here's|here\s+are|attached|given)\b.*:\s*$"
)

# ---------------------------------------------------------------------------
# 7. Conflict / formatting detection
# ---------------------------------------------------------------------------
# Pairs of words that usually pull a response in opposite directions.
OPPOSING_TERMS = (
    (("detailed", "in-depth", "thorough", "comprehensive", "elaborate"),
     ("concise", "brief", "short", "succinct", "terse")),
    (("formal",), ("informal", "casual", "colloquial")),
    (("technical",), ("non-technical", "layman", "layperson", "beginner-friendly")),
)

# Mutually exclusive *output* formats (one directive normally implies one format)
EXCLUSIVE_FORMATS = ("json", "xml", "yaml", "csv", "html", "plain text", "table", "bullet points")
OUTPUT_DIRECTIVE_RE = _rx(
    r"\b(?:respond|answer|reply|output|return|format|write|present|provide|give)\b[^.?!]*?"
    r"\b(?:in|as|using)\s+(?:a\s+|an\s+|the\s+)?(" + "|".join(re.escape(f) for f in EXCLUSIVE_FORMATS) + r")\b"
)

# Distinct formatting directives (counted once each).
FORMAT_DIRECTIVES = {
    "bullet points": _rx(r"\bbullet(?:ed)?\s+(?:points?|lists?)\b|\bbullets\b"),
    "numbered list": _rx(r"\bnumbered\s+(?:list|steps|points)\b"),
    "markdown": _rx(r"\bmarkdown\b"),
    "bold/italic": _rx(r"\b(?:bold|italic|italicize|italicise|underline)\b"),
    "headings": _rx(r"\b(?:headings?|headers?|sub-?headings?)\b"),
    "table": _rx(r"\btables?\b"),
    "emoji": _rx(r"\bemojis?\b"),
    "step-by-step": _rx(r"\bstep[- ]by[- ]step\b"),
    "sections": _rx(r"\bsections?\b"),
    "capitalization": _rx(r"\b(?:capitali[sz]e|uppercase|lowercase|title case)\b"),
}

# Keywords describing the REQUIRED OUTPUT FORMAT; the validator insists that
# every one present in the original is still present in the optimized prompt.
FORMAT_KEYWORDS = (
    "json", "xml", "yaml", "csv", "tsv", "markdown", "html", "latex", "sql", "table",
    "bullet", "numbered", "step by step", "step-by-step", "plain text",
)

LENGTH_UNITS = {
    "word": "words", "words": "words", "sentence": "sentences", "sentences": "sentences",
    "paragraph": "paragraphs", "paragraphs": "paragraphs", "bullet": "bullets",
    "bullets": "bullets", "bullet point": "bullets", "bullet points": "bullets",
    "character": "characters", "characters": "characters", "char": "characters",
    "chars": "characters", "line": "lines", "lines": "lines", "item": "items",
    "items": "items", "token": "tokens", "tokens": "tokens", "step": "steps",
    "steps": "steps", "example": "examples", "examples": "examples",
}
