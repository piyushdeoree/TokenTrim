"""Parser for Google's official Gemini Developer API pricing page.

Supports the provider's documented per-model Standard/Batch/Flex tabs expressed
as its published Markdown table representation. Unsupported page revisions fail
closed rather than extracting unrelated tool or storage charges.
"""
from __future__ import annotations
from datetime import date,datetime
from html.parser import HTMLParser
import re
from .base import finish

GOOGLE_URL="https://ai.google.dev/gemini-api/docs/pricing"
FETCH_URL=GOOGLE_URL

class _GoogleHTMLMarkdown(HTMLParser):
    """Convert provider model headings, tabs, and pricing tables to parseable Markdown."""
    def __init__(self):
        super().__init__(); self.parts=[]; self.cell=[]; self.row=[]; self.in_cell=False; self.heading=0; self.button=False; self.button_text=[]; self.anchor=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ("h2","h3","h4"):
            self.heading=int(tag[1]); self.parts.append("\n"+"#"*self.heading+" ")
        elif tag=="button": self.button=True; self.button_text=[]
        elif tag=="a": self.anchor=attrs.get("href")
        elif tag=="tr": self.row=[]
        elif tag in ("td","th") and self.row is not None: self.cell=[]; self.in_cell=True
        elif tag=="br": self.parts.append("\n")
    def handle_data(self,data):
        if self.in_cell: self.cell.append(data)
        elif self.button: self.button_text.append(data)
        elif self.anchor and "/models/" in self.anchor:
            model=self.anchor.rsplit("/",1)[-1]
            self.parts.append(f"[`{model}`]({self.anchor})")
            self.anchor=None
        else:
            self.parts.append(data)
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.in_cell:
            self.row.append(" ".join("".join(self.cell).split())); self.in_cell=False
        elif tag=="tr" and self.row is not None:
            if self.row: self.parts.append("\n| "+" | ".join(self.row)+" |\n")
            self.row=None
        elif tag=="button" and self.button:
            label=" ".join("".join(self.button_text).split())
            if label in {"Standard","Batch","Flex","Priority","Fast"}:
                self.parts.append(f"\n#### {label}\n")
            self.button=False
        elif tag=="a": self.anchor=None
        elif tag in ("h2","h3","h4"): self.parts.append("\n"); self.heading=0

def _as_markdown(document):
    if "<html" not in document.lower() and "<table" not in document.lower(): return document
    parser=_GoogleHTMLMarkdown(); parser.feed(document)
    return "".join(parser.parts)

def _effective_price(text: str, today: date | None=None):
    today=today or date.today()
    pieces=[x.strip() for x in text.splitlines() if x.strip()]
    candidates=[]
    for piece in pieces:
        match=re.search(r"\$\s*([0-9]+(?:\.[0-9]+)?)",piece)
        if not match: continue
        amount=match.group(1); through=re.search(r"through\s+([A-Za-z]+\s+\d{1,2},\s*\d{4})",piece,re.I)
        starting=re.search(r"starting\s+([A-Za-z]+\s+\d{1,2},\s*\d{4})",piece,re.I)
        try:
            if through:
                end=datetime.strptime(through.group(1),"%B %d, %Y").date()
                candidates.append((amount,today<=end,None if today<=end else end.isoformat()))
            elif starting:
                begin=datetime.strptime(starting.group(1),"%B %d, %Y").date()
                candidates.append((amount,today>=begin,begin.isoformat()))
            else: candidates.append((amount,True,None))
        except ValueError: raise ValueError(f"unrecognized effective-date condition: {piece}") from None
    active=[x for x in candidates if x[1]]
    if not active: raise ValueError(f"no currently effective price found in {text!r}")
    # Prefer latest effective start among overlapping entries.
    dated=[x for x in active if x[2]]
    chosen=sorted(dated,key=lambda x:x[2])[-1] if dated else active[0]
    from decimal import Decimal
    value=Decimal(chosen[0])
    if not value.is_finite() or value<0: raise ValueError("invalid Gemini price")
    return value,chosen[2]

def _price_fields(block: str, tier: str, today: date | None):
    start=block.find('{% tab title="'+tier+'" %}')
    if start>=0:
        next_tab=block.find('{% tab title=',start+1)
        section=block[start:next_tab if next_tab>=0 else len(block)]
    else:
        heading=re.search(r"^####\s+"+re.escape(tier)+r"\s*$",block,re.I|re.M)
        if not heading: return None
        next_heading=re.search(r"^####\s+",block[heading.end():],re.M)
        end=heading.end()+next_heading.start() if next_heading else len(block)
        section=block[heading.end():end]
    def field(label,required=True):
        pattern=r"\*\s*"+label+r"[^\n]*\n\s*\*[^\n]*\n\s*\*\s*([^\n]+(?:\n(?!\s*\*\s*(?:Feature|Input price|Output price|Context caching price))[^\n]+)?)"
        m=re.search(pattern,section,re.I)
        value=m.group(1) if m else None
        if value is None:
            # HTML table fallback: Feature | Free Tier | Paid Tier ...
            target="input price" if label.lower().startswith("input price") else "output price" if label.lower().startswith("output price") else "context caching price"
            for cells in re.findall(r"^\|\s*([^|]+)\|([^|]+)\|([^|]+)\|\s*$",section,re.M):
                if cells[0].strip().lower().startswith(target): value=cells[2].strip(); break
        if value and ("not available" in value.lower() or "not applicable" in value.lower()): return None,None
        if value is None:
            if required: raise ValueError(f"Gemini {tier} {label} field missing")
            return None,None
        if label.lower().startswith("output price") and re.search(r"\$\s*[0-9.]+\s+per\s+image\b",value.splitlines()[0],re.I):
            raise ValueError("non-token output price is published per image")
        return _effective_price(value,today)
    inp,eff1=field(r"Input price")
    out,eff2=field(r"Output price(?:\s*\([^)]*\))?")
    if inp is None or out is None: return {"available":False,"tier":tier,"input":None,"output":None,"cached":None,"effective_dates":[]}
    cache,eff3=field(r"Context caching price",required=False)
    return {"input":inp,"output":out,"cached":cache,"effective_dates":[x for x in (eff1,eff2,eff3) if x]}

def _sections(document):
    # Google docs' Markdown source uses a heading followed by a model-ID link
    # and tab blocks; headings and IDs are both mandatory to avoid title guesses.
    matches=list(re.finditer(r"^##\s+(.+?)(?:\s+\{%\s*id=\"([^\"]+)\"\s*%\})?\s*$",document,re.M))
    result=[]
    for i,match in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(document)
        block=document[match.end():end]
        id_match=re.search(r"\*\s*\[?`?([a-z0-9][a-z0-9.-]+)`?\]?\s*\]\([^)]*/docs/models/[^)]*\)",block,re.I)
        # Some docs builds flatten this into *[`model-id`](/docs/models/id).
        if not id_match: id_match=re.search(r"\[`([a-z0-9][a-z0-9.-]+)`\]\([^)]*\)",block,re.I)
        model_id=id_match.group(1) if id_match else None
        if "{% tab title=\"Standard\" %}" in block or "Input price" in block:
            result.append((match.group(1).strip(),model_id,block))
    return result

def parse_google_pricing(document: str, *, today: date | None=None) -> list[dict]:
    if not isinstance(document,str) or not document.strip(): raise ValueError("Google pricing page is empty")
    rows=[]; malformed=[]
    document=_as_markdown(document)
    for display,model,block in _sections(document):
        if not model:
            if "gemma" in display.lower(): continue
            malformed.append(f"{display}: model identifier link missing")
            continue
        try:
            standard=_price_fields(block,"Standard",today)
            additional={}
            for service_tier in ("Batch","Flex","Priority"):
                candidate=_price_fields(block,service_tier,today)
                if candidate: additional[service_tier.lower()]=candidate
        except ValueError as exc:
            if "non-token output price" in str(exc): continue
            if "embedding" in display.lower() or "decision" in display.lower(): continue
            if "{% tab title=\"Standard\" %}" in block or "Standard" in block:
                malformed.append(f"{model}: {exc}")
            continue
        if not standard or not standard.get("available",True): continue
        cache_storage=re.search(r"\$\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*1,?000,?000 tokens? per hour",block,re.I)
        standard_conditions={"service_tier":"Standard"}
        if cache_storage: standard_conditions["cache_storage_usd_per_million_tokens_hour"]=cache_storage.group(1)
        tiers=[{"tier":"standard","input":standard["input"],"output":standard["output"],
                "cached_input":standard["cached"],"conditions":standard_conditions}]
        for service_tier,pricing in additional.items():
            tiers.append({"tier":service_tier,"input":pricing.get("input"),"output":pricing.get("output"),
                "cached_input":pricing["cached"],"conditions":{"service_tier":service_tier.title(),
                    "available":pricing.get("available",True),
                    "effective_dates":pricing["effective_dates"]}})
        # Extract provider-declared context limit when a model section states it.
        context_match=re.search(r"(?:context window|context length)[^\n]{0,80}?([0-9][0-9,]*)\s*tokens?",block,re.I)
        context=int(context_match.group(1).replace(",","")) if context_match else None
        rows.append(finish("google",GOOGLE_URL,model,display,standard["input"],standard["output"],
            cached=standard["cached"],batch_input=additional.get("batch",{}).get("input") if additional.get("batch",{}).get("available",True) else None,
            batch_output=additional.get("batch",{}).get("output") if additional.get("batch",{}).get("available",True) else None,tier="standard",
            conditions={**standard_conditions,"effective_dates":standard["effective_dates"]},
            tiers=tiers,effective_date=next(iter(standard["effective_dates"]),None),context_window=context,
            notes="Gemini pricing can change by effective date; the parser selects the currently effective Standard/Batch value and retains tier conditions."))
    if malformed: raise ValueError("Google pricing page has malformed model blocks: "+"; ".join(malformed[:8]))
    if not rows: raise ValueError("Google pricing page contained no supported model Standard/Batch pricing blocks")
    return rows
