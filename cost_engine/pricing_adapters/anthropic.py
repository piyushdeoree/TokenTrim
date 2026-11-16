"""Parser for Anthropic's official Claude Platform pricing Markdown."""
from __future__ import annotations
import re
from .base import table_rows,price,finish,model_key

ANTHROPIC_URL="https://platform.claude.com/docs/en/about-claude/pricing"
FETCH_URL=ANTHROPIC_URL+".md"

def _clean(text):
    text=re.sub(r"<sup>.*?</sup>","",text,flags=re.I)
    text=re.sub(r"\[([^\]]+)\]\([^)]*\)",r"\1",text)
    text=re.sub(r"\s+"," ",text).strip()
    return text

def parse_anthropic_pricing(document: str) -> list[dict]:
    if not isinstance(document,str) or not document.strip(): raise ValueError("Anthropic pricing page is empty")
    records={}; section=""; row_errors=[]
    regional=bool(re.search(r"1\.1x pricing multiplier|10 percent premium",document,re.I))
    for line in document.splitlines():
        heading=re.match(r"^#{1,4}\s+(.+)",line.strip())
        if heading: section=heading.group(1).lower()
        row=next(table_rows(line),None)
        if not row or len(row)<3: continue
        header=[_clean(x).lower() for x in row]
        if "model" in header and any("input" in h for h in header) and any("output" in h for h in header):
            columns=header; continue
        if "columns" not in locals(): continue
        if len(row)!=len(columns):
            if row[0].startswith("Claude") and ("model pricing" in section or "batch processing" in section or "fast mode" in section):
                row_errors.append(f"{row[0]}: row width differs from pricing header")
            continue
        values={name:_clean(value) for name,value in zip(columns,row)}
        raw_model=values.get("model","")
        if not raw_model:
            if any("$" in value for value in values.values()): row_errors.append("pricing row has no model identifier")
            continue
        if raw_model.lower() in {"model","concept"}: continue
        display=_clean(raw_model)
        base_display=re.sub(r"\s*\([^)]*\)","",display).strip()
        # Parse only the three first-party model-price tables. Other feature
        # tables (tool token counts, cloud billing) are not token SKU rates.
        if not any(k in values for k in ("base input tokens","input","batch input")): continue
        try:
            batch="batch" in values.get("batch input","").lower() or "batch processing" in section
            if "base input tokens" in values:
                input_rate=price(values["base input tokens"])
                output_rate=price(values["output tokens"])
                cache_write_5m=price(values["5m cache writes"],optional=True)
                cache_write_1h=price(values["1h cache writes"],optional=True)
                cached=price(values["cache hits and refreshes"],optional=True)
                field_set={"input":input_rate,"output":output_rate,"cached":cached,
                           "cache_write":cache_write_5m,"cache_write_1h":cache_write_1h}
                identifier=model_key(base_display)
                rec=records.get(identifier)
                if rec is None:
                    rec={"model":identifier,"display":base_display,"input":input_rate,"output":output_rate,
                         "cached":cached,"write":cache_write_5m,"batch_input":None,"batch_output":None,
                         "tiers":[],"conditions":{"scope":"Anthropic first-party API","pricing_tier":"standard"}}
                    records[identifier]=rec
                # Multiple rows for context thresholds (notably Haiku) are
                # represented as explicit conditional variants.
                if "for prompts over" in display.lower() or "for prompts up to" in display.lower():
                    condition=re.search(r"for prompts (up to|over) ([\d,]+) tokens",display,re.I)
                    rec["tiers"].append({"tier":"standard","input":input_rate,"output":output_rate,
                        "cached_input":cached,"cache_write_5m":cache_write_5m,"cache_write_1h":cache_write_1h,
                        "conditions":{"prompt_tokens":condition.group(1)+" "+condition.group(2).replace(",","")} if condition else {"display_condition":display}})
                    if "up to" in display.lower(): rec.update(input=input_rate,output=output_rate,cached=cached,write=cache_write_5m)
                elif rec is not records[identifier] or rec["display"]==base_display:
                    rec["tiers"].append({"tier":"standard","input":input_rate,"output":output_rate,
                        "cached_input":cached,"cache_write_5m":cache_write_5m,"cache_write_1h":cache_write_1h,
                        "conditions":{"display_condition":display} if display!=base_display else {"scope":"global"}})
                if "retired" in display.lower(): rec["conditions"]["availability"]="retired or platform-limited as stated by provider"
                if "limited availability" in display.lower(): rec["conditions"]["availability"]="limited availability"
            elif batch and "batch input" in values:
                identifier=model_key(base_display)
                if identifier in records:
                    batch_input=price(values["batch input"]); batch_output=price(values["batch output"])
                    records[identifier]["tiers"].append({"tier":"batch","input":batch_input,
                        "output":batch_output,"conditions":{"discount":"50%","scope":"Anthropic Batch API",
                        "display_condition":display}})
                    if "for prompts over" not in display.lower():
                        records[identifier]["batch_input"]=batch_input
                        records[identifier]["batch_output"]=batch_output
                else: row_errors.append(f"{display}: batch row has no standard model row")
            elif "input" in values and "output" in values and section.startswith("fast mode"):
                identifier=model_key(base_display)
                if identifier in records:
                    records[identifier]["tiers"].append({"tier":"fast","input":price(values["input"]),
                        "output":price(values["output"]),"conditions":{"availability":"Fast mode"}})
        except (KeyError,ValueError) as exc:
            row_errors.append(f"{base_display}: {exc}")
    if row_errors: raise ValueError("Anthropic pricing table contains incomplete or unsupported rows: "+"; ".join(row_errors[:8]))
    if not records: raise ValueError("Anthropic pricing page contained no supported model pricing table")
    return [finish("anthropic",ANTHROPIC_URL,r["model"],r["display"],r["input"],r["output"],
        cached=r["cached"],cache_write=r["write"],batch_input=r["batch_input"],batch_output=r["batch_output"],
        tier="standard",conditions={**r["conditions"],"regional_modifier_published":regional},tiers=r["tiers"],
        notes="Pricing tier variants, prompt thresholds, cache durations, availability and modifiers are retained in pricing_tiers/pricing_conditions.") for r in records.values()]
