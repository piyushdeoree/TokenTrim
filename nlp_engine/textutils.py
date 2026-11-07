"""
textutils.py - shared, deterministic text helpers.

Everything here is rule-based (regex + Porter stemming); no model is involved.

Pipeline position:   raw prompt
                       -> protect_spans()   mask code / URLs / quotes / JSON
                       -> segment           sentences with layout information
                       -> classify          instruction | constraint | question |
                                            role | persona | context
                       -> apply_rewrites()  safe verbosity rewrites (used by the
                                            analyzer to *detect* and by the
                                            optimizer to *apply*)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Dict, FrozenSet, List, Optional, Tuple

from nltk.stem.porter import PorterStemmer

from . import config

_STEMMER = PorterStemmer()

# ---------------------------------------------------------------------------
# Protected spans (never edited by the optimizer)
# ---------------------------------------------------------------------------
PLACEHOLDER_FMT = "QZPH{}QZ"
PLACEHOLDER_RE = re.compile(r"QZPH(\d+)QZ", re.IGNORECASE)

_REGEX_SPANS = [
    re.compile(r"```.*?```", re.S),                         # fenced code
    re.compile(r'"""(?:.|\n)*?"""'),                        # triple-quoted blocks
    re.compile(r"<(\w+)[^>]*>.*?</\1>", re.S),              # <context>...</context>
    re.compile(r"`[^`\n]+`"),                               # inline code
    re.compile(r"https?://[^\s)>\]]*[^\s)>\].,;:!?]"),      # URLs
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),                # e-mail addresses
    re.compile(r'"[^"\n]{1,500}"'),                         # "quoted strings"
    re.compile(r"\u201c[^\u201d\n]{1,500}\u201d"),          # curly quotes
]


def _balanced_spans(text: str, open_ch: str, close_ch: str) -> List[Tuple[int, int]]:
    spans, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch == open_ch:
            if depth == 0:
                start = i
            depth += 1
        elif ch == close_ch and depth > 0:
            depth -= 1
            if depth == 0 and i + 1 - start >= 3:
                spans.append((start, i + 1))
    return spans


def protect_spans(text: str) -> Tuple[str, Dict[int, str]]:
    """Replace code/URLs/quotes/JSON-like blocks with placeholders.

    Returns (masked_text, {placeholder_id: original_fragment}). Identical
    fragments share one placeholder id so duplicates stay comparable.
    """
    spans: List[Tuple[int, int]] = []
    for rx in _REGEX_SPANS:
        spans.extend((m.start(), m.end()) for m in rx.finditer(text))
    spans.extend(_balanced_spans(text, "{", "}"))
    spans.extend(_balanced_spans(text, "[", "]"))
    spans.sort()

    merged: List[Tuple[int, int]] = []
    for s, e in spans:
        if merged and s < merged[-1][1]:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))

    mapping: Dict[int, str] = {}
    reverse: Dict[str, int] = {}
    out, last = [], 0
    for s, e in merged:
        out.append(text[last:s])
        frag = text[s:e]
        if frag not in reverse:
            reverse[frag] = len(mapping)
            mapping[reverse[frag]] = frag
        out.append(PLACEHOLDER_FMT.format(reverse[frag]))
        last = e
    out.append(text[last:])
    return "".join(out), mapping


def unprotect(text: str, mapping: Dict[int, str]) -> str:
    return PLACEHOLDER_RE.sub(lambda m: mapping.get(int(m.group(1)), m.group(0)), text)


# ---------------------------------------------------------------------------
# Words, stems, canonical form
# ---------------------------------------------------------------------------
_WORD_RE = re.compile(r"[a-z0-9]+(?:[.'\u2019][a-z0-9]+)*")


def words(text: str) -> List[str]:
    return _WORD_RE.findall(text.lower())


@lru_cache(maxsize=8192)
def _stem(token: str) -> str:
    return _STEMMER.stem(token)


def canonical_text(text: str) -> str:
    t = text.lower()
    for rx, rep in config.CANONICAL_PHRASES:
        t = rx.sub(rep, t)
    return t


def content_stems(text: str) -> FrozenSet[str]:
    """Stemmed, synonym-folded, stop-word-free token set of ``text``."""
    out = set()
    for tok in words(canonical_text(text)):
        tok = config.SYNONYMS.get(tok, tok)
        if tok in config.STOPWORDS or tok in config.FILLER_WORDS:
            continue
        out.add(_stem(tok))
    return frozenset(out)


def extract_numbers(text: str) -> FrozenSet[str]:
    """Numbers incl. decimals, percentages, currency (commas removed)."""
    found = re.findall(r"(?<![\w.])[-+]?[$\u20ac\u00a3\u20b9]?\d[\d,]*(?:\.\d+)?%?", text)
    return frozenset(f.replace(",", "") for f in found)


def is_negated(text: str) -> bool:
    return bool(config.NEGATION_RE.search(text.lower()))


# ---------------------------------------------------------------------------
# Sentence segmentation with layout
# ---------------------------------------------------------------------------
_ABBREV = {"e.g", "i.e", "etc", "vs", "dr", "mr", "mrs", "ms", "fig", "approx", "no", "st", "prof", "inc", "ltd"}
_BOUNDARY = re.compile(r"([.!?]+[\"')\]]*)\s+(?=[A-Z0-9\"'(\[<*#-])")
_LIST_MARKER_RE = re.compile(r"^(\s*(?:[-*\u2022+]|\d+[.)]|[A-Za-z][.)]|#{1,6})\s+)")


def split_sentences(text: str) -> List[str]:
    out, start = [], 0
    for m in _BOUNDARY.finditer(text):
        cand = text[start:m.end(1)]
        before = re.search(r"([A-Za-z.]+)\.$", cand)
        if before:
            w = before.group(1).lower().rstrip(".")
            if w in _ABBREV or (len(w) == 1 and w.isalpha()):
                continue
        out.append(cand.strip())
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return [s for s in out if s]


@dataclass
class Segment:
    text: str                 # sentence text (masked), without list marker
    prefix: str = ""          # list marker / indentation preserved on output
    suffix: str = " "         # whitespace that followed the sentence
    kind: str = "context"     # instruction|constraint|question|role|persona|context
    para: int = 0
    locked: bool = False      # inside a user-content block: never edited
    removed: bool = False


@dataclass
class PreparedPrompt:
    original: str
    masked: str
    mapping: Dict[int, str]
    segments: List[Segment]

    def unmask(self, text: str) -> str:
        return unprotect(text, self.mapping)


def strip_leadin(text: str) -> Tuple[str, bool]:
    """Strip 'I would like you to' style lead-ins if an instruction verb follows."""
    m = config.LEADIN_RE.match(text)
    if not m:
        return text, False
    rest = text[m.end():]
    toks = [w.lower() for w in re.findall(r"[A-Za-z']+", rest)[:5]]
    for k, lw in enumerate(toks):
        if lw in config.FILLER_WORDS:
            continue
        if lw in config.INSTRUCTION_VERBS or (lw == "make" and toks[k + 1:k + 2] == ["sure"]):
            return rest, True
        break
    return text, False


def head_word(text: str) -> Optional[str]:
    """First meaningful word of a sentence (after lead-ins), canonicalised."""
    t, _ = strip_leadin(text.strip())
    for w in words(canonical_text(t)):
        if w in config.FILLER_WORDS or w in config.CONNECTIVES:
            continue
        return w
    return None


_PLACEHOLDER_ONLY = re.compile(r"^[\s\W]*(?:QZPH\d+QZ[\s\W]*)+$", re.I)


def has_non_latin_letters(text: str) -> bool:
    """True if the text contains letters outside Latin scripts (CJK, Cyrillic, Arabic...)."""
    return any(ch.isalpha() and ord(ch) > 0x24F for ch in text)


def classify_sentence(text: str) -> str:
    t = text.strip()
    if not t or _PLACEHOLDER_ONLY.match(t):
        return "context"
    if has_non_latin_letters(t):      # English-only engine: never edit other scripts
        return "context"
    if config.GENERIC_PERSONA_RE.match(t):
        return "persona"
    if config.ROLE_RE.match(t):
        return "role"
    head = head_word(t)
    if head in config.CONSTRAINT_HEADS:
        return "constraint"
    if head in config.INSTRUCTION_VERBS:
        return "instruction"
    if config.CONSTRAINT_RE.search(t):
        return "constraint"
    if t.endswith("?"):
        return "question"
    return "context"


def _segment(masked: str) -> List[Segment]:
    parts = re.split(r"((?:[ \t]*\r?\n)+)", masked)
    segments: List[Segment] = []
    para = 0
    context_mode, captured = False, False
    for idx in range(0, len(parts), 2):
        line = parts[idx]
        nl = parts[idx + 1] if idx + 1 < len(parts) else ""
        if not line.strip():
            continue
        m = _LIST_MARKER_RE.match(line)
        prefix = m.group(1) if m else re.match(r"\s*", line).group(0)
        body = line[len(prefix):]

        label = config.LABEL_RE.match(body)
        locked = context_mode or bool(label)
        if label:
            context_mode = True
            captured = bool(body[label.end():].strip())
        elif context_mode:
            captured = True

        sentences = split_sentences(body)
        for k, s in enumerate(sentences):
            kind = "context" if locked else classify_sentence(s)
            segments.append(Segment(text=s, prefix=prefix if k == 0 else "", suffix=" ",
                                    kind=kind, para=para, locked=locked))
        if segments:
            segments[-1].suffix = nl

        if (not context_mode and sentences and sentences[-1].rstrip().endswith(":")
                and config.CONTEXT_INTRO_RE.search(sentences[-1])):
            context_mode, captured = True, False
        if nl.count("\n") >= 2:
            para += 1
            if context_mode and captured:
                context_mode = False
    return segments


def prepare_prompt(prompt: str) -> PreparedPrompt:
    text = prompt.strip()
    masked, mapping = protect_spans(text)
    return PreparedPrompt(original=text, masked=masked, mapping=mapping, segments=_segment(masked))


def normalize_ws(text: str) -> str:
    text = re.sub(r"(?<=\S)[ \t]{2,}", " ", text)      # keep leading indentation
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def render_segments(segments: List[Segment]) -> str:
    parts: List[List[str]] = []
    for s in segments:
        if s.removed:
            if parts and "\n" in s.suffix and "\n" not in parts[-1][2]:
                parts[-1][2] = s.suffix
            continue
        parts.append([s.prefix, s.text, s.suffix])
    return normalize_ws("".join(p + t + sfx for p, t, sfx in parts)).strip()


# ---------------------------------------------------------------------------
# Heuristic rewriting (verbosity)
# ---------------------------------------------------------------------------
@dataclass
class RewriteEvent:
    kind: str        # leadin | phrase | filler | persona
    before: str
    after: str
    label: str = ""


REWRITABLE_KINDS = {"instruction", "constraint", "question"}


def _cleanup(t: str) -> str:
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r",\s*,", ",", t)
    t = re.sub(r"^[,;:\s]+", "", t)
    return re.sub(r"[ \t]{2,}", " ", t).strip()


def capitalize_first(t: str) -> str:
    for i, ch in enumerate(t):
        if ch.isalpha():
            return t[:i] + ch.upper() + t[i + 1:]
        if ch.isdigit():
            break
    return t


def apply_rewrites(text: str) -> Tuple[str, List[RewriteEvent]]:
    """Apply deterministic verbosity rewrites to ONE instruction-like sentence."""
    events: List[RewriteEvent] = []
    t = text.strip()
    stripped = False

    t2, did = strip_leadin(t)
    if did:
        events.append(RewriteEvent("leadin", t[: len(t) - len(t2)].strip(), "", "polite/verbose lead-in"))
        t, stripped = t2, True

    for label, rx, rep in config.VERBOSE_RULES:
        for m in rx.finditer(t):
            events.append(RewriteEvent("phrase", m.group(0).strip(), rep.strip(), label))
        t = rx.sub(rep, t)

    for m in config.FILLER_RE.finditer(t):
        events.append(RewriteEvent("filler", m.group(0).strip(" ,"), "", "filler word"))
    t = config.FILLER_RE.sub("", t)

    t = _cleanup(t)
    if t != text.strip():
        t = capitalize_first(t)
        if stripped and t.endswith("?"):
            t = t[:-1] + "."
    else:
        t = text
    return t, events


def rewrite_segments(segments: List[Segment]) -> Tuple[List[Segment], List[Tuple[int, RewriteEvent]]]:
    """Copy of ``segments`` with rewrites applied; generic personas removed."""
    out: List[Segment] = []
    events: List[Tuple[int, RewriteEvent]] = []
    for i, seg in enumerate(segments):
        new = replace(seg)
        if seg.locked:
            out.append(new)
            continue
        if seg.kind == "persona":
            new.removed = True
            events.append((i, RewriteEvent("persona", seg.text.strip(), "", "generic persona statement")))
        elif seg.kind in REWRITABLE_KINDS:
            new_text, evs = apply_rewrites(seg.text)
            new.text = new_text
            events.extend((i, e) for e in evs)
        out.append(new)
    return out, events
