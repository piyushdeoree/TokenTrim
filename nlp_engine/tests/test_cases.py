"""
The 10 required evaluation scenarios.

Each case lists strings that MUST still appear (verbatim) in the optimized
prompt. This is an independent check - it does not rely on the validator.
"""
from __future__ import annotations

_LONG_CONTEXT = "\n".join(
    f"Paragraph {i}: The quarterly logistics report describes warehouse throughput, "
    f"staffing levels and delivery delays in region {i} in considerable detail."
    for i in range(60)
)

CASES = [
    {
        "id": 1, "name": "simple question",
        "prompt": "What is the capital of France?",
        "must_contain": ["capital", "France"],
        "expect_change": False, "expect_issues": [],
    },
    {
        "id": 2, "name": "long verbose prompt",
        "prompt": ("I would like you to please provide me with an explanation of how photosynthesis works "
                   "in plants. Could you please also give me an example of it?"),
        "must_contain": ["photosynthesis", "plants", "example"],
        "expect_change": True, "expect_issues": ["verbosity"],
    },
    {
        "id": 3, "name": "repeated instructions",
        "prompt": "Analyze this carefully. Please carefully analyze the data.",
        "must_contain": ["data"],
        "expect_change": True, "expect_issues": ["redundancy"],
    },
    {
        "id": 4, "name": "duplicate constraints",
        "prompt": ("Write a product description for a coffee mug. Keep the answer under 100 words. "
                   "The answer must be under 100 words. Limit the response to 100 words."),
        "must_contain": ["coffee mug", "100 words"],
        "expect_change": True, "expect_issues": ["duplicate_constraint"],
    },
    {
        "id": 5, "name": "large context (must not be cut)",
        "prompt": "Summarize the following report in 3 bullet points.\n\nText:\n" + _LONG_CONTEXT,
        "must_contain": [_LONG_CONTEXT, "3 bullet points"],
        "expect_change": False, "expect_issues": ["excessive_context"],
    },
    {
        "id": 6, "name": "code-generation prompt",
        "prompt": ("Please write a Python function called `calculate_total` that sums a list of prices. "
                   "I would like you to make sure that it handles empty lists.\n"
                   "```python\ndef calculate_total(prices):\n    pass\n```"),
        "must_contain": ["`calculate_total`", "Python", "empty lists",
                         "```python\ndef calculate_total(prices):\n    pass\n```"],
        "expect_change": True, "expect_issues": ["verbosity"],
    },
    {
        "id": 7, "name": "summarization prompt (spec example)",
        "prompt": ("You are an expert assistant. I would like you to carefully analyze the following text. "
                   "Please analyze it carefully and provide me with a detailed summary. "
                   "Make sure that the summary is clear, concise, and easy to understand."),
        "must_contain": ["Analyze the following text", "summary", "clear, concise, and easy to understand"],
        "expect_change": True, "expect_issues": ["redundancy", "verbosity"],
    },
    {
        "id": 8, "name": "structured JSON-output prompt",
        "prompt": ('Return the result as JSON with keys "name", "age", "email". Please make sure that the '
                   "output is valid JSON. Do not include any explanation. Respond only in JSON format.\n"
                   '{"name": "string", "age": 0, "email": "string"}'),
        "must_contain": ['"name"', '"age"', '"email"', "JSON", "Do not include any explanation",
                         '{"name": "string", "age": 0, "email": "string"}'],
        "expect_change": True, "expect_issues": [],
    },
    {
        "id": 9, "name": "prompt with important numbers",
        "prompt": ("Please summarize the Q3 2025 report in under 150 words. Revenue grew 12.5% to "
                   "$4.2 million. Make sure to mention the 3 key risks."),
        "must_contain": ["Q3", "2025", "150", "12.5%", "$4.2 million", "3 key risks"],
        "expect_change": None, "expect_issues": [],
    },
    {
        "id": 10, "name": "already tight prompt (little/no change)",
        "prompt": "Translate to French: 'Good morning, how are you?'",
        "must_contain": ["Translate to French", "'Good morning, how are you?'"],
        "expect_change": False, "expect_issues": [],
    },
]
