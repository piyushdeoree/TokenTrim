"""Generate a SYNTHETIC prompt/response dataset for development and testing.

!!! THIS DATA IS NOT REAL. !!!
Output lengths are drawn from hand-written distributions below. Any model
trained on it only learns those assumptions, so metrics measured on it say
nothing about real-world accuracy. Replace with real logs
(config.REAL_DATASET_FILE) before reporting results.

Usage (from the repo root):
    python -m cost_engine.data.generate_synthetic --rows 5000
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .. import config
from ..calculator import calculate_cost
from ..pricing import list_models

# Assumed behaviour per task type: (typical output/input ratio, noise sigma,
# input-token log-mean, input-token log-sigma). Pure assumptions.
TASK_PROFILES = {
    "question_answering": (1.2, 0.45, 4.2, 0.6),
    "summarization": (0.25, 0.30, 6.8, 0.6),
    "translation": (1.05, 0.15, 5.0, 0.6),
    "coding": (2.5, 0.55, 4.8, 0.7),
    "creative_writing": (4.0, 0.50, 3.8, 0.6),
    "extraction": (0.35, 0.35, 6.0, 0.7),
    "analysis": (1.4, 0.45, 6.0, 0.7),
}

# Assumed verbosity multiplier per model (illustrative only).
MODEL_VERBOSITY = {
    "gpt-4o": 1.0, "gpt-4o-mini": 0.9, "claude-sonnet": 1.15,
    "claude-haiku": 0.95, "gemini-pro": 1.05, "gemini-flash": 0.85,
}


def generate(rows: int = 5000, seed: int = config.RANDOM_STATE) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tasks = list(TASK_PROFILES)
    models = list_models()
    start = datetime(2026, 1, 1)
    recs = []
    for i in range(rows):
        task = tasks[rng.integers(len(tasks))]
        model = models[rng.integers(len(models))]
        ratio, sigma, mu, ls = TASK_PROFILES[task]
        input_tokens = int(max(5, rng.lognormal(mu, ls)))
        complexity = int(rng.integers(1, 6))  # 1 (simple) .. 5 (complex)
        cx_factor = 0.8 + 0.1 * complexity
        mean_out = input_tokens * ratio * cx_factor * MODEL_VERBOSITY.get(model, 1.0)
        output_tokens = int(max(1, mean_out * rng.lognormal(0, sigma)))
        word_count = max(1, int(input_tokens * 0.75))
        sentence_count = max(1, int(word_count / rng.uniform(12, 25)))
        ts = start + timedelta(minutes=int(rng.integers(0, 60 * 24 * 270)))
        cost = calculate_cost(model, input_tokens, output_tokens).total_cost
        recs.append({
            "prompt_id": f"syn-{i:06d}",
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "task_type": task,
            "complexity": complexity,
            "timestamp": ts.isoformat(),
            "cost": cost,
            "data_source": "SYNTHETIC",
        })
    return pd.DataFrame(recs).sort_values("timestamp").reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=config.RANDOM_STATE)
    args = ap.parse_args()
    df = generate(args.rows, args.seed)
    config.SYNTHETIC_DATASET_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.SYNTHETIC_DATASET_FILE, index=False)
    print(f"Wrote {len(df)} SYNTHETIC rows to {config.SYNTHETIC_DATASET_FILE}")


if __name__ == "__main__":
    main()
