"""Parser for OpenAI's official Markdown pricing documentation."""
from __future__ import annotations
import re
from .base import table_rows, price, finish

OPENAI_URL="https://developers.openai.com/api/docs/pricing"
FETCH_URL=OPENAI_URL+".md"

def parse_openai_pricing(document: str) -> list[dict]:
    if not isinstance(document,str) or not document.strip(): raise ValueError("OpenAI pricing page is empty")
    multimodal=re.search(r"^Multimodal models\s*$",document,re.I|re.M)
    if multimodal: document=document[:multimodal.start()]
    lines=document.splitlines(); current="standard"; records={}; active_table=None; row_errors=[]
    short_threshold=re.search(r"Short context:\s*[^\n]*?([0-9,]+K?)\s+input tokens",document,re.I)
    long_threshold=re.search(r"Long context:\s*([^\n]+)",document,re.I)
    source_modifiers=[line.strip() for line in lines if "Regional processing" in line and "uplift" in line]
    for line in lines:
        tier_heading=re.search(r"###\s+(Standard|Batch|Flex|Fast|Ultrafast) pricing data",line,re.I)
        if tier_heading: current=tier_heading.group(1).lower()
        elif re.match(r"\s*####\s+Batch\b",line,re.I): current="batch"
        if not line.strip().startswith("|"): active_table=None; continue
        row=next(table_rows(line),None)
        if not row: continue
        normalized=[x.lower() for x in row]
        if normalized[0]=="model": active_table=normalized; continue
        if not active_table or row[0].startswith("---"): continue
        # Do not treat unrelated tables as token price tables.
        if len(active_table)<4 or not any("input" in h for h in active_table) or not any("output" in h for h in active_table):
            active_table=None; continue
        if len(row)!=len(active_table):
            if row[0]: row_errors.append(f"{row[0]}: row width differs from pricing header")
            continue
        if not row[0].strip():
            if any(re.search(r"\$\s*[0-9]",cell) for cell in row[1:]): row_errors.append("pricing row has no model identifier")
            continue
        name=re.sub(r"\s*\([^)]*\)","",row[0]).strip()
        if current=="batch":
            try:
                values={h:v for h,v in zip(active_table,row)}
                batch_in=price(values.get("short context input",values.get("input","-")),optional=True)
                batch_out=price(values.get("short context output",values.get("output","-")),optional=True)
                if (batch_in is None)!=(batch_out is None): raise ValueError("batch input/output rates are incomplete")
                if name in records:
                    records[name]["batch_input"]=batch_in; records[name]["batch_output"]=batch_out
                    records[name]["variants"].append({"tier":"batch","input":batch_in,"output":batch_out,
                        "cached_input":price(values.get("short context cached input","-"),optional=True),
                        "cache_write_30m":price(values.get("short context 30m write","-"),optional=True),
                        "cache_write_12h":price(values.get("short context 12h write","-"),optional=True),
                        "conditions":{"context":"short","service_tier":"batch","available":batch_in is not None}})
                elif batch_in is not None:
                    row_errors.append(f"{name}: batch row has no standard pricing row")
            except (KeyError,ValueError) as exc: row_errors.append(f"{name}: {exc}")
            continue
        try:
            values={h: v for h,v in zip(active_table,row)}
            if current in {"flex","fast","ultrafast"} and name not in records:
                row_errors.append(f"{name}: {current} tier has no matching standard model row")
                continue
            if "short context input" in values:
                prefix="short context "
                inp=price(values[prefix+"input"]); out=price(values[prefix+"output"])
                cached=price(values[prefix+"cached input"],optional=True)
                write=price(values.get(prefix+"30m write","-"),optional=True)
                long_in=price(values["long context input"],optional=True)
                long_out=price(values["long context output"],optional=True)
                long={"input":long_in,"output":long_out,
                      "cached_input":price(values["long context cached input"],optional=True),
                      "cache_write_30m":price(values.get("long context 30m write","-"),optional=True),
                      "cache_write_12h":price(values.get("long context 12h write","-"),optional=True),
                      "conditions":{"context":"long","available":long_in is not None and long_out is not None,
                                    "threshold":long_threshold.group(1).strip() if long_threshold else "provider-defined"}}
                short={"input":inp,"output":out,"cached_input":cached,"cache_write_30m":write,
                       "cache_write_12h":price(values.get("short context 12h write","-"),optional=True),
                       "conditions":{"context":"short","threshold":short_threshold.group(1) if short_threshold else "provider-defined"}}
                variants=[short,long]
            else:
                inp=price(values["input"]); out=price(values["output"])
                cached=price(values.get("cached input","-"),optional=True); write=None; variants=[]
            rec=records.setdefault(name,{"name":name,"input":inp,"output":out,"cached":cached,"write":write,
                                         "batch_input":None,"batch_output":None,"variants":variants,"conditions":{"service_tier":current}})
            if current in {"flex","fast","ultrafast"}:
                rec["variants"].append({"tier":current,"input":inp,"output":out,"cached_input":cached,"conditions":{"service_tier":current}})
        except (KeyError,ValueError) as exc:
            row_errors.append(f"{name}: {exc}")
    if row_errors: raise ValueError("OpenAI pricing table contains incomplete or unsupported rows: "+"; ".join(row_errors[:8]))
    if not records: raise ValueError("OpenAI pricing page contained no supported model price tables")
    results=[]
    for r in records.values():
        conditions={**r["conditions"],"source_modifiers":source_modifiers}
        promotion=re.search(re.escape(r["name"])+r"[^\n]*promotional pricing[^\n]*(?:until|through)\s+([^.;]+)",document,re.I)
        if promotion: conditions["promotional_price_until"]=promotion.group(1).strip()
        results.append(finish("openai",OPENAI_URL,r["name"],r["name"],r["input"],r["output"],cached=r["cached"],
        cache_write=r["write"],batch_input=r["batch_input"],batch_output=r["batch_output"],
        tier="standard",conditions=conditions,tiers=r["variants"],
        notes="Short-context rates are the default when provider table distinguishes short/long context; all listed variants are retained in pricing_tiers."))
    return results
