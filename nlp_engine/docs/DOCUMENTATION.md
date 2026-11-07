# NLP Prompt Analysis & Optimization Engine - Technical Documentation

Written for the final-year project report. It separates four things that must not be confused:

| layer | nature | claim we make |
|---|---|---|
| 1. Token counting | deterministic | exact for OpenAI models (via `tiktoken`); **estimate** otherwise |
| 2. Prompt analysis | rule-based NLP | measurable features and detectors; no learned model |
| 3. Optimization | heuristic, rule-based | meaning-*preserving by construction* for the rules used; not proven |
| 4. LLM rewriting | optional, off by default | validated by the same checks; no guarantee |

---

## 1. Problem definition

LLM APIs are billed per token. Prompts written by people tend to contain tokens that add cost
without adding information: polite lead-ins ("I would like you to please..."), filler words,
instructions repeated in different words, constraints stated three times, generic personas,
and so on. The goal of this module is:

> **Reduce unnecessary tokens while preserving the original intent and important constraints.**

The module takes `{prompt, model}`, measures the prompt, detects inefficiencies, proposes a shorter
prompt, **checks that nothing important was lost**, and reports the token saving. Cost conversion
(tokens -> money), output-token prediction and model recommendation belong to Person 2.

Design principles: *conservative* (when unsure, keep the text), *explainable* (every issue and
change has a stated rule), *modular* (each concern in its own file), *honest* (estimates are
labelled; no fake accuracy numbers).

## 2. Architecture

```
prompt
  |  textutils.protect_spans      mask code, URLs, e-mails, "quotes", JSON/brackets -> placeholders
  |  textutils.segment            sentences / list items with their layout (indent, markers, newlines)
  |  textutils.classify           instruction | constraint | question | role | persona | context
  v
analyzer.build_analysis ----> detectors (redundancy.py, analyzer.py) + complexity.py
  v
optimizer.optimize_prompt  -->  candidate prompt
  v
validator.validate_optimization --> accept (if valid AND saves tokens) or fall back to the original
  v
analyzer.analyze_prompt  -->  the agreed JSON contract
```

### Why masking and classification come first

The safest way to "never edit code, URLs, quoted strings, JSON schemas, numbers" is to make them
*unreachable* by the optimizer: they are replaced by opaque placeholders (`QZPH3QZ`) before any
analysis and restored verbatim afterwards. Identical fragments share a placeholder, so duplicates remain
comparable.

Sentences are then classified so that only **instruction-like** text is ever rewritten:

* `instruction` - starts (after lead-ins) with an instruction verb (`analyze`, `summarize`, `write`...)
* `constraint` - starts with `do not / never / always / only / avoid / keep / be / ensure`, or contains
  `must / should / only ...`, or a length limit like `under 100 words`
* `question` - ends with `?`
* `role` - specific persona ("You are an expert Python developer") - never removed
* `persona` - *generic* persona ("You are a helpful assistant") - removable
* `context` - everything else, **plus** everything inside user-content blocks (see below). Never edited.

User-content blocks are recognised by a label (`Text:`, `Context:`, `Document:`, `Article:`...) or by
an introducing sentence ending in a colon ("Here is the report:"); everything up to the next blank
line after content has started is locked.

## 3. Tokenization (`tokenizer.py`)

```python
count_tokens(prompt, model) -> {"input_tokens", "word_count", "character_count", "sentence_count"}
```

* A **registry** maps model names to *counter* objects (`BaseTokenCounter`). New tokenizers are added
  with `register_tokenizer(...)` without touching other modules.
* **OpenAI models:** `tiktoken.encoding_for_model(model)` (falls back to a prefix table for
  `gpt-4o`, `gpt-4.1`, `o1/o3/o4` -> `o200k_base`; `gpt-4`, `gpt-3.5` -> `cl100k_base`). Exact.
* **Claude, Gemini, unknown models:** no offline tokenizer exists (exact counts need the vendors' web
  APIs). We use `heuristic_token_estimate`: pre-tokenise into alphabetic runs, digit runs and symbols;
  `ceil(len/4)` tokens per alphabetic run, `ceil(len/3)` per digit run, 1 per symbol, 1 per non-ASCII
  character. It is an approximation with **no stated error bound** and is always labelled
  (`method="heuristic_estimate"`, `exact=False`).
* `tokenizer_info(model)` tells callers which method was used. Original and optimized prompts are
  always counted with the same counter, so *differences* are consistent.
* `word_count` counts `\w+` words (with internal hyphens/apostrophes); `sentence_count` is the number of
  sentence/list-item segments produced by the rule-based segmenter (abbreviation-aware).

## 4. Analysis (`redundancy.py`, `analyzer.py`, `complexity.py`)

All detectors return `Finding(type, severity, description, evidence)`; `evidence` is exposed in
`analyze_prompt_detailed`.

### 4.1 Clause representation

Each instruction/constraint sentence is split into *clauses* before instruction verbs
("analyze it **and** provide a summary" -> two clauses; only a safe subset of verbs triggers splitting).
A clause is represented by:

* **stems** - lower-cased, canonicalised, stop-word-free, Porter-stemmed tokens
  (canonicalisation folds `response/reply/output -> answer`, `summary -> summarize`,
  `no more than / at most / under / limit to -> maxlimit`, `do not / never / can't -> not`...)
* **head verb**, **negation flag**, **set of numbers**.

### 4.2 Repeated instructions (A) and duplicate constraints (D)

Two kinds of comparison, deliberately asymmetric:

| purpose | test | consequence |
|---|---|---|
| **reporting** | cosine similarity (scikit-learn `CountVectorizer(binary)` + `cosine_similarity`) >= 0.60 (instructions) / 0.75 (constraints), same numbers, same polarity | *issue reported* (low severity) |
| **removal** | clause A's stems are a **subset** of clause B's, same polarity, A's numbers ⊆ B's, same head verb (instructions) | A is *removed*, B is kept; medium severity |

Example: `"Analyze this. ... Analyze the data."` -> `{analyz}` ⊆ `{analyz, data}`, same head verb -> the vaguer
clause is dropped. `"Summarize the text in French. Summarize the report in German."` -> neither is a subset ->
both kept (a naive similarity-only approach would have merged them and lost information).
`"Include X. Do not include X."` -> polarity differs -> never merged; reported as a **conflict**.

### 4.3 Repeated phrases (B)

Word n-grams (3-8 words) are counted per sentence, ignoring stop-word-only/number/placeholder n-grams.
Only *maximal* repeated phrases are kept. `repeated_phrase_ratio = sum((count-1) * length) / total_words`
(capped at 1). This is *reported only*; phrase-level repetition is not auto-edited because repeating a
phrase is sometimes intentional.

### 4.4 Verbosity (C)

Uses the same rewrite rules as the optimizer, so detection and optimization cannot disagree:
polite lead-ins (`I would like you to`, `Could you please`, `I want you to`...), filler words
(`please, kindly, carefully, basically, really, actually, simply, essentially`), wordy phrases
(`in order to -> to`, `due to the fact that -> because`, `provide me with an explanation of -> explain`...),
generic personas, and instruction sentences longer than 40 words. Lead-ins are only rewritten when an
instruction verb follows, so `"I would like to know..."` is untouched.
Severity depends on the number of possible simplifications (<=2 low, <=5 medium, else high).

### 4.5 Excessive context (E)

`context_tokens` = tokens of `context` segments (incl. code blocks, labelled blocks);
`instruction_tokens` = all other segments. Flagged only if `context_tokens >= 400` **and** the ratio is `>= 5`.
Duplicate sentences inside the context are reported too. **Context is never removed automatically.**

### 4.6 Formatting overload (F)

Counts *distinct* formatting directives (bullet points, numbered list, markdown, bold/italic, headings,
tables, emojis, step-by-step, sections, capitalisation). Flagged when `>= 3` (medium at `>= 6`).
Reported only - formatting instructions are often the required output format.

### 4.7 Conflicts (G)

1. direct polarity contradiction: same stems, opposite negation (**high**)
2. opposing style words (`detailed` vs `concise`, `formal` vs `casual`, ...) (**medium**, "possibly")
3. impossible length limits (`at least 200 words` + `under 100 words`; different exact counts) (**medium**)
4. mutually exclusive output formats in different directives (`in JSON` + `as plain text`) (**medium**)

Conflicts are never auto-resolved: resolving them would change the user's intent. (Note: the spec's
summarization example contains both "detailed" and "concise"; the engine keeps both and warns.)

### 4.8 Complexity (H)

Features: token count, instruction count, constraint count, average/max sentence length (words),
structure depth (max bracket nesting or indented-list depth, fenced code excluded), code-block count,
repeated-phrase ratio, context-to-instruction ratio, distinct formatting directives.

```
complexity_score = 100 * sum_i  w_i * min(feature_i / cap_i, 1)
```

| feature | cap | weight |
|---|---:|---:|
| token_count | 2000 | 0.20 |
| instruction_count | 10 | 0.15 |
| constraint_count | 8 | 0.15 |
| avg_sentence_length | 30 | 0.10 |
| structure_depth | 4 | 0.10 |
| repeated_phrase_ratio | 0.30 | 0.10 |
| context_to_instruction_ratio | 10 | 0.10 |
| format_directive_count | 6 | 0.10 |

Caps and weights are **design choices** (in `config.py`), not fitted to data. The score is a relative
indicator (bands: <33 low, <66 medium, else high), not a calibrated measurement.

## 5. Optimization methodology (`optimizer.py`)

`optimize_prompt(prompt, analysis)` applies, in order, only these rules:

1. drop **generic persona** sentences;
2. in instruction-like sentences: strip polite lead-ins, rewrite wordy phrases (rule table in
   `config.VERBOSE_RULES`), delete filler words, tidy punctuation/capitalisation;
3. split sentences into clauses and drop clauses **fully covered** by another clause (section 4.2);
4. rebuild the prompt with the original layout (paragraphs, list markers, indentation), restore the masked spans.

It never edits: code, URLs, e-mails, quoted strings, JSON/bracket blocks, labelled context, specific
personas, conflicting instructions, formatting requirements, or non-Latin text.
It does **not** hard-code outputs: results depend on the matched rules and the clause structure.

Example (spec scenario, tokens are model-dependent):

```
IN : You are an expert assistant. I would like you to carefully analyze the following text.
     Please analyze it carefully and provide me with a detailed summary.
     Make sure that the summary is clear, concise, and easy to understand.
OUT: Analyze the following text. Provide a detailed summary.
     Ensure the summary is clear, concise, and easy to understand.
```

Deliberate difference from the example in the project brief ("...provide a clear, concise summary"):
the brief's version silently drops "detailed", which contradicts "concise". Choosing between them
changes the user's intent, so the engine keeps both and reports a `conflict` warning instead.

The optimizer returns a **candidate** (`OptimizationResult` with the list of `changes` for explainability).
It is only accepted after validation *and* only if it actually saves tokens.

### Optional LLM-assisted rewriting (layer 4)

`analyze_prompt(..., llm_rewriter=fn)` lets the backend supply any `str -> str` function. Its output
becomes a second candidate, subject to the same validator. Default is off, so the system is fully
deterministic and reproducible; the analysis features never depend on an LLM.

## 6. Validation methodology (`validator.py`)

`validate_optimization(original, optimized)` -> `ValidationResult(is_valid, reasons, metrics)`.

| check | type | rule |
|---|---|---|
| numbers | hard | every number/percentage/amount in the original appears in the optimized prompt |
| protected spans | hard | every code/URL/e-mail/quoted/JSON fragment appears verbatim |
| output format | hard | every format keyword (json, xml, yaml, csv, markdown, html, table, bullet, numbered, step-by-step...) still present |
| named items | hard | capitalised names, acronyms, camelCase/snake_case identifiers still present |
| constraints | hard | each constraint sentence >= 85 % covered by the optimized stems; negations (`do not`) still present |
| keyword coverage | soft | >= 90 % of original content stems remain (stems of words deliberately removed by the rewrite rules are excluded) |
| lexical similarity | soft | TF-IDF cosine(original, optimized) >= 0.35 |

Generic persona sentences are excluded from the comparison (they carry no task information).
Any failed check -> optimization rejected, original returned, reasons available in the detailed output.
All metrics are surfaced in `analyze_prompt_detailed(...).validation.metrics`.

**What a pass means:** no detectable loss according to the checks above. It does **not** prove semantic
equivalence - two prompts can share all numbers/keywords and still differ in meaning.

## 7. Testing and measurement

`tests/` contains 46 pytest tests: the 10 required scenarios (simple question, long verbose prompt,
repeated instructions, duplicate constraints, large context, code generation, summarization, JSON output,
important numbers, already-tight prompt), tokenizer tests (including that non-exact counts are labelled),
validator rejection tests, detector tests, regression tests (list layout, non-English text, 68k-token prompt),
and a test that a second optimization pass changes nothing.

`python -m nlp_engine.tests.run_evaluation` prints and saves, per scenario: original tokens, optimized tokens,
tokens saved, reduction %, whether the optimization was accepted, and an independent check that required
strings (numbers, names, code, JSON schema, constraints, context) are still present verbatim.

> The numbers in `tests/evaluation_results.md` as shipped were produced in an environment where `tiktoken`
> could not download its vocabulary, so they are **estimates**. Re-run the script on your machine with
> `tiktoken` working to obtain exact OpenAI counts for the report. The 10 scenarios are hand-written
> illustrations, not a benchmark: no accuracy, F1 or generalisation figure is claimed.

## 8. Limitations

* **English only.** Non-Latin text is detected and left untouched; other Latin-script languages are analysed with English rules (not recommended).
* **Rule-based, no real language understanding.** No POS tagging or parsing; verbs are recognised by word lists
  (`config.INSTRUCTION_VERBS`), so unusual phrasing is simply not optimized (a safe failure).
* **Descriptive sentences can look like constraints.** Unlabelled context containing `must/should/only/always` may be
  classified as a constraint and, if exactly repeated, de-duplicated. Labelled/introduced context blocks are locked.
* **Conflict detection is shallow.** It finds lexical/numeric contradictions only; paraphrased contradictions are missed,
  and `Use Python` / `Don't use Python 2` is intentionally not flagged.
* **Token counts for Claude/Gemini are estimates**; the heuristic has no verified error bound.
* **Pairwise de-duplication is skipped above 300 comparable clauses** (O(n²); such inputs are almost certainly data).
* **Savings are modest on well-written prompts** (see scenarios 8-10) - the engine removes waste, it does not compress ideas.
* **No semantic-equivalence guarantee** (section 6).
* Thresholds and weights are untuned design choices.

## 9. Future improvements

* Exact tokenizers for Claude and Gemini via their counting APIs (plug-in point already exists).
* spaCy dependency parsing / POS tags for clause detection instead of verb lists; multilingual support.
* Embedding-based semantic similarity (Hugging Face sentence encoders) as an *additional* validator signal.
* Calibrate thresholds/weights on a labelled prompt set; user study to measure whether optimized prompts keep answer quality
  (e.g. compare LLM outputs for original vs optimized prompts).
* Smarter handling of conflicts (ask the user which requirement wins), structured-prompt (XML/markdown section) awareness,
  few-shot example de-duplication.
