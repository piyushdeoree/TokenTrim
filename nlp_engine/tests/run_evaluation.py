"""
Measure the 10 scenarios and write a Markdown table.

    python -m nlp_engine.tests.run_evaluation        (from the parent directory)

Reports original/optimized token counts, reduction, whether the validator accepted
the optimization, and an independent check that required strings are preserved.
The tokenizer method is printed so nobody mistakes an estimate for an exact count.
"""
import pathlib
import sys

from nlp_engine import analyze_prompt_detailed, tokenizer_info
from .test_cases import CASES

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-4o"


def main():
    info = tokenizer_info(MODEL)
    rows = ["| # | Scenario | Original | Optimized | Saved | Reduction | Accepted | Preserved | Issues |",
            "|---|----------|---------:|----------:|------:|----------:|:--------:|:---------:|--------|"]
    tot_o = tot_n = 0
    for c in CASES:
        d = analyze_prompt_detailed(c["prompt"], MODEL)
        kept = all(s in d.final.optimized_prompt for s in c["must_contain"])
        tot_o += d.final.original_tokens
        tot_n += d.final.optimized_tokens
        issues = ", ".join(sorted({i.type for i in d.issues})) or "-"
        rows.append(f"| {c['id']} | {c['name']} | {d.final.original_tokens} | {d.final.optimized_tokens} | "
                    f"{d.final.tokens_saved} | {d.final.reduction_percentage:.1f}% | "
                    f"{'yes' if d.optimization_accepted else 'no change'} | {'yes' if kept else 'NO'} | {issues} |")
    overall = 100 * (tot_o - tot_n) / tot_o if tot_o else 0
    header = (f"# Evaluation results\n\nModel: `{MODEL}`  \nToken counting: `{info.method}` "
              f"({'EXACT' if info.exact else 'ESTIMATE - not an exact tokenizer'})  \n"
              f"{info.note}\n\n")
    footer = (f"\nTotal: {tot_o} -> {tot_n} tokens ({overall:.1f}% over these 10 prompts; "
              "this is a descriptive number for this tiny hand-written set, not an accuracy or "
              "generalisation claim).\n\n'Preserved' = every required string (numbers, names, code, "
              "constraints, JSON schema, context) is still present verbatim.\n")
    text = header + "\n".join(rows) + "\n" + footer
    print(text)
    out = pathlib.Path(__file__).with_name("evaluation_results.md")
    out.write_text(text, encoding="utf-8")
    print(f"written to {out}")


if __name__ == "__main__":
    main()
