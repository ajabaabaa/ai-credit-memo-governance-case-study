from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from itertools import zip_longest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FIELDS = ["total_revenue", "gross_margin", "research_and_development", "sales_and_marketing", "general_and_administrative", "operating_income", "net_income", "interest_expense", "depreciation_amortization", "cash_and_equivalents", "total_current_assets", "total_current_liabilities", "current_portion_ltd", "long_term_debt", "total_liabilities", "stockholders_equity"]
LABELS = {x.replace("_", " "): x for x in FIELDS}
PROMPT = "Extract the 16 financial values shown in this synthetic two-year filing excerpt. Return only JSON with company, form_type, fiscal_year_end, not_found, and these exact keys: total_revenue, gross_margin, research_and_development, sales_and_marketing, general_and_administrative, operating_income, net_income, interest_expense, depreciation_amortization, cash_and_equivalents, total_current_assets, total_current_liabilities, current_portion_ltd, long_term_debt, total_liabilities, stockholders_equity. Each key must be {cy:number,py:number,page:string}. Map equivalent line labels to those keys (for example, Net sales→total_revenue; Gross profit→gross_margin; Depreciation and amortization→depreciation_amortization). Copy company name exactly. Read the stated fiscal periods, ignore segment-only figures and note references, and use consolidated statement values. Preserve displayed numeric amounts and sign; do not correct, infer, rescale, or calculate. Handle commas and currency symbols. Interest expense is the exact Interest Expense line; exclude Lease Interest Expense. not_found must be an array.\n"
ROOT = Path(__file__).resolve().parents[1]
SPEND_LEDGER = ROOT / "results" / "spend-ledger.json"
MAX_OUTPUT_TOKENS = 1400


def _filing_text(company: str, vals: dict, i: int) -> str:
    style=i%8
    labels={"total_revenue":"Net sales" if style%3==0 else "Total revenue","gross_margin":"Gross profit","research_and_development":"Research and development expense","sales_and_marketing":"Selling and marketing expense","general_and_administrative":"General and administrative expense","operating_income":"Operating income","net_income":"Net income","interest_expense":"Interest expense","depreciation_amortization":"Depreciation and amortization","cash_and_equivalents":"Cash and cash equivalents","total_current_assets":"Total current assets","total_current_liabilities":"Total current liabilities","current_portion_ltd":"Current portion of long-term debt","long_term_debt":"Long-term debt, net of current portion","total_liabilities":"Total liabilities","stockholders_equity":"Total stockholders’ equity"}
    lines=[f"{company} consolidated financial statements, fiscal year ended June 30, 2026 (Form 10-K)","CONSOLIDATED STATEMENTS OF OPERATIONS",["(in thousands, except per-share data)","(USD thousands)","USD, rounded to nearest thousand","(in thousands)"][i%4]]
    ordered=list(vals.items())
    if style%2: ordered.reverse()
    for k,v in ordered:
        label=labels[k]; a,b=v
        if style==1: lines.append(f"{label} .............. ${a:,} (2026) | ${b:,} (2025)")
        elif style==2: lines.append(f"{label}: FY2026 {a:,}; FY2025 {b:,}")
        elif style==3: lines.append(f"{label} | 2026 | 2025\n{a:,} | {b:,}")
        elif style==4: lines.append(f"{label} | ${a:,} | ${b:,}")
        elif style==5: lines.append(f"{label} [1] ........ ${a:,} FY2026; ${b:,} FY2025")
        elif style==6: lines.append(f"{label} (2026) {a:,}; prior year (2025) {b:,}")
        else: lines.append(f"{label} | {a:,} | {b:,}")
    lines += ["Interest expense excludes lease interest.","Lease interest expense | 999 | 888","See Note 7 for debt maturities; amounts may not sum due to rounding."]
    lines.insert(4, f"Segment revenue (not consolidated) | {vals['total_revenue'][0]//3:,} | {vals['total_revenue'][1]//3:,}")
    return "\n".join(lines)


def _corrupt_source_values(clean: dict, tier: int, record_id: int, seed: int) -> tuple[dict,list[dict]]:
    import random
    source={k:list(v) for k,v in clean.items()}
    slots=list(range(32)); random.Random(seed ^ (record_id*0x9E3779B1)).shuffle(slots)
    wrong={50:16,75:8,100:0}[tier]; defects=[]
    for slot in slots[:wrong]:
        field=FIELDS[slot//2]; year=slot%2; old=source[field][year]
        kind=(record_id+slot)%5
        if kind==0: new=old+max(1,10**max(0,len(str(abs(old)))-2)) # single digit OCR-like substitution
        elif kind==1: new=max(1,old//10) # dropped digit / decimal-place shift
        elif kind==2: new=old*1000 # unit scale mismatch
        elif kind==3: new=source[field][1-year]
        else:
            other=FIELDS[(FIELDS.index(field)+1)%len(FIELDS)]
            new=source[other][year]
        if new==old: new=old+1
        source[field][year]=new
        defects.append({"field":field,"period":"cy" if year==0 else "py","type":["ocr_digit","decimal_shift","unit_scale","period_misalignment","adjacent_line_value"][kind]})
    return source,defects


def iter_generate(n: int, seed: int = 20261020, realistic: bool = False, quality_mix: bool = False):
    # Existing synthetic statement generator and field definitions retained.
    import random
    rng = random.Random(seed)
    for i in range(n):
        rev = [rng.randint(100000, 900000), rng.randint(90000, 850000)]
        gm = [int(x*rng.uniform(.35, .75)) for x in rev]
        rd = [int(x*rng.uniform(.04, .16)) for x in rev]
        sm = [int(x*rng.uniform(.05, .2)) for x in rev]
        op = [int(gm[j]-rd[j]-sm[j]-gm[j]*rng.uniform(.1, .4)) for j in range(2)]
        ga = [gm[j]-rd[j]-sm[j]-op[j] for j in range(2)]
        vals = {"total_revenue":rev,"gross_margin":gm,"research_and_development":rd,"sales_and_marketing":sm,"general_and_administrative":ga,"operating_income":op,"net_income":[int(op[j]*rng.uniform(.55,.9)) for j in range(2)],"interest_expense":[rng.randint(500,12000) for _ in range(2)],"depreciation_amortization":[rng.randint(1000,30000) for _ in range(2)],"cash_and_equivalents":[rng.randint(10000,70000) for _ in range(2)],"total_current_assets":[rng.randint(20000,150000) for _ in range(2)],"total_current_liabilities":[rng.randint(15000,100000) for _ in range(2)],"current_portion_ltd":[rng.randint(1000,20000) for _ in range(2)],"long_term_debt":[rng.randint(5000,80000) for _ in range(2)],"total_liabilities":[rng.randint(20000,250000) for _ in range(2)],"stockholders_equity":[rng.randint(20000,200000) for _ in range(2)]}
        company=f"SYNTHETIC CO {i:05d}"
        if quality_mix:
            # Balanced deterministic strata: 3,333 records each at 50%/75%, 3,334 at 100%.
            tier=50 if i < n//3 else (75 if i < (2*n)//3 else 100)
            observed,defects=_corrupt_source_values(vals,tier,i,seed)
            text=_filing_text(company,observed,i)
            yield {"id":i,"text":text,"truth":observed,"latent_truth":vals,"company":company,"quality_tier":tier,"defects":defects}
        elif not realistic:
            lines = [f"{company} | Form 10-K | FY end June 30, 2026"]
            lines += [f"{k.replace('_',' ').title()} | {v[0]} | {v[1]}" for k,v in vals.items()]
            lines += ["Lease Interest Expense | 999 | 888"]
            yield {"id":i,"text":"\n".join(lines),"truth":vals,"company":company}
        else:
            yield {"id":i,"text":_filing_text(company,vals,i),"truth":vals,"company":company}


def generate(n: int, seed: int = 20261020, realistic: bool = False, quality_mix: bool = False) -> list[dict]:
    return list(iter_generate(n,seed,realistic,quality_mix))


def parse_statement(row: dict) -> dict:
    values = {}
    lines=row["text"].splitlines()[1:]
    aliases={"net sales":"total_revenue","gross profit":"gross_margin","research and development expense":"research_and_development","selling and marketing expense":"sales_and_marketing","general and administrative expense":"general_and_administrative","depreciation and amortization":"depreciation_amortization","cash and cash equivalents":"cash_and_equivalents","current portion of long-term debt":"current_portion_ltd","long-term debt, net of current portion":"long_term_debt","total stockholders equity":"stockholders_equity"}
    pairs=[]
    for index,line in enumerate(lines):
        if re.fullmatch(r".+? \| 2026 \| 2025",line):
            if index+1<len(lines):
                amount=re.fullmatch(r"(-?[\d,]+) \| (-?[\d,]+)",lines[index+1])
                if amount:
                    pairs.append((line.split(" | ")[0],amount.group(1),amount.group(2)))
            continue
        patterns=(r"(.+?) \| (\$?-?[\d,]+) \| (\$?-?[\d,]+)",r"(.+?) \.{2,} \$?(-?[\d,]+) \(2026\) \| \$?(-?[\d,]+) \(2025\)",r"(.+?): FY2026 (-?[\d,]+); FY2025 (-?[\d,]+)",r"(.+?) \[1\] \.{2,} \$?(-?[\d,]+) FY2026; \$?(-?[\d,]+) FY2025",r"(.+?) \(2026\) (-?[\d,]+); prior year \(2025\) (-?[\d,]+)")
        match=next((re.fullmatch(p,line) for p in patterns if re.fullmatch(p,line)),None)
        if match:
            pairs.append((match.group(1),match.group(2),match.group(3)))
            continue
    for raw_label,cy,py in pairs:
        label=re.sub(r"\s+", " ", raw_label.strip().lower().replace("’", "").removesuffix(" [1]"))
        field = LABELS.get(label) or aliases.get(label)
        if field:
            values[field] = {"cy":int(cy.replace(',','').replace('$','')),"py":int(py.replace(',','').replace('$','')),"page":"Synthetic statement"}
    return {"company":row["company"],"form_type":"10-K","fiscal_year_end":"June 30, 2026","not_found":[],**values}


def normalize_extraction(value: dict) -> dict:
    if not isinstance(value, dict):
        return {}
    normalized = {}
    for key, item in value.items():
        canonical = re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")
        normalized[canonical] = item
    if normalized.get("not_found") is False or normalized.get("not_found") is None:
        normalized["not_found"] = []
    if isinstance(normalized.get("not_found"), str):
        normalized["not_found"] = [normalized["not_found"]] if normalized["not_found"].strip() else []
    if isinstance(normalized.get("form_type"), str):
        normalized["form_type"] = normalized["form_type"].replace("Form ", "").strip()
    return normalized


def _http_json(url: str, payload: dict, headers: dict, timeout: int = 120) -> dict:
    req = Request(url, data=json.dumps(payload).encode(), headers={**headers, "Content-Type":"application/json"})
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:1000]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Provider connection failed: {exc.reason}") from exc


def _get_openrouter_price(model: str) -> tuple[float, float]:
    request = Request("https://openrouter.ai/api/v1/models", headers={"Accept":"application/json"})
    with urlopen(request, timeout=30) as response:
        catalog = json.loads(response.read())
    model_id = model.removeprefix("openrouter/")
    for item in catalog.get("data", []):
        if item.get("id") == model_id:
            pricing = item.get("pricing", {})
            return float(pricing["prompt"]), float(pricing["completion"])
    raise RuntimeError(f"Model {model_id} is absent from the OpenRouter catalog; refusing unpriced inference")


def _paid_reserve(model: str, row: dict, prompt_text: str) -> tuple[float, str]:
    input_price, output_price = _get_openrouter_price(model)
    # Conservative bound: ASCII prompt characters as input tokens plus max output tokens.
    estimate = len(prompt_text) * input_price + MAX_OUTPUT_TOKENS * output_price
    ledger = json.loads(SPEND_LEDGER.read_text(encoding="utf-8"))
    if ledger["spent_usd"] + ledger["reserved_usd"] + estimate > ledger["cap_usd"]:
        raise RuntimeError(f"Paid inference blocked: conservative call estimate ${estimate:.6f} would exceed remaining cap ${ledger['cap_usd']-ledger['spent_usd']-ledger['reserved_usd']:.6f}")
    call_id = hashlib.sha256(f"{model}|{row['id']}|{time.time_ns()}".encode()).hexdigest()[:16]
    ledger["reserved_usd"] += estimate
    ledger["entries"].append({"call_id":call_id,"model":model,"record_id":row["id"],"reserved_usd":estimate,"status":"reserved"})
    SPEND_LEDGER.write_text(json.dumps(ledger,indent=2)+"\n",encoding="utf-8")
    return estimate, call_id


def _paid_settle(call_id: str, estimate: float, actual: float | None, succeeded: bool) -> None:
    ledger = json.loads(SPEND_LEDGER.read_text(encoding="utf-8"))
    ledger["reserved_usd"] = max(0.0, ledger["reserved_usd"]-estimate)
    charge = actual if succeeded and actual is not None else estimate
    ledger["spent_usd"] += charge
    for entry in reversed(ledger["entries"]):
        if entry["call_id"] == call_id:
            entry.update({"actual_or_conservative_usd":charge,"status":"settled" if succeeded else "conservative charge after failed/unknown response"})
            break
    SPEND_LEDGER.write_text(json.dumps(ledger,indent=2)+"\n",encoding="utf-8")


def _openrouter_extract(row: dict, model: str) -> tuple[dict, dict, float | None]:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    api_model = model.removeprefix("openrouter/")
    prompt_text = PROMPT+row["text"]
    body = {"model":api_model,"messages":[{"role":"user","content":prompt_text}],"response_format":{"type":"json_object"},"usage":{"include":True}}
    paid = not api_model.endswith(":free")
    estimate = call_id = None
    if paid:
        body["max_tokens"] = MAX_OUTPUT_TOKENS
        estimate, call_id = _paid_reserve(model, row, prompt_text)
    try:
        data = _http_json("https://openrouter.ai/api/v1/chat/completions", body, {"Authorization":"Bearer "+key})
    except Exception:
        if paid: _paid_settle(call_id, estimate, None, False)
        raise
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    cost = usage.get("cost")
    if cost is None and isinstance(usage.get("cost_details"), dict):
        cost = usage["cost_details"].get("upstream_inference_cost")
    if paid:
        _paid_settle(call_id, estimate, float(cost) if cost is not None else None, True)
    return json.loads(content), usage, float(cost) if cost is not None else None


def _ollama_extract(row: dict, model: str) -> tuple[dict, dict, float]:
    name = model.removeprefix("ollama/")
    data = _http_json("http://localhost:11434/api/chat", {"model":name,"messages":[{"role":"user","content":PROMPT+row["text"]}],"format":"json","stream":False,"think":False,"options":{"temperature":0,"num_predict":1400}}, {}, timeout=600)
    return json.loads(data["message"]["content"]), {"prompt_tokens":data.get("prompt_eval_count",0),"completion_tokens":data.get("eval_count",0)}, 0.0


def _opencode_extract(row: dict, model: str) -> tuple[dict, dict, float | None]:
    prompt = PROMPT + row["text"]
    exe = shutil.which("opencode.exe")
    if not exe:
        shim = shutil.which("opencode.cmd")
        if shim:
            exe = str(Path(shim).parent / "node_modules" / "@opencode" / "cli" / "bin" / "opencode.exe")
    if not exe:
        raise RuntimeError("OpenCode executable not found on PATH")
    proc = subprocess.run([exe, "run", "--format", "json", "--model", model, prompt], cwd=ROOT, capture_output=True, text=True, timeout=180)
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout)[-1500:])
    events = []
    for line in proc.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    texts = []
    usage = {"prompt_tokens":None,"completion_tokens":None}
    for event in events:
        props = event.get("properties", {})
        part = event.get("part", props.get("part", {}))
        if part.get("type") == "text" and part.get("text"):
            texts.append(part["text"])
        if part.get("type") in {"step-finish", "step_finish"} or event.get("type") in {"step-finish", "step_finish"}:
            u = part.get("tokens", {})
            if not u:
                u = props.get("tokens", {})
            if u.get("input") is not None:
                usage["prompt_tokens"] = (usage["prompt_tokens"] or 0) + u["input"]
            if u.get("output") is not None:
                usage["completion_tokens"] = (usage["completion_tokens"] or 0) + u["output"]
    content = "\n".join(texts).strip()
    if not content:
        # `json` format can be a single result object in some OpenCode builds.
        content = proc.stdout.strip()
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "company" in parsed:
                return parsed, usage, None
        except json.JSONDecodeError:
            pass
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.I)
    # OpenCode's JSON event stream omits aggregate usage on some builds. Read the
    # completed local session record, which exposes provider model, token counts,
    # reasoning tokens, and actual billed cost without persisting the transcript.
    session_proc = subprocess.run([exe,"session","list","--max-count","1","--format","json"],cwd=ROOT,capture_output=True,text=True,timeout=30)
    session_id = next((e.get("sessionID") or e.get("sessionId") or e.get("session_id") for e in reversed(events) if e.get("sessionID") or e.get("sessionId") or e.get("session_id")),None)
    if session_proc.returncode == 0:
        try:
            sessions = json.loads(session_proc.stdout)
            session_id = session_id or (sessions[0].get("id") if sessions else None)
        except (json.JSONDecodeError,IndexError,AttributeError):
            pass
    actual_cost = None
    if session_id:
        export_proc = subprocess.run([exe,"session","export",session_id],cwd=ROOT,capture_output=True,text=True,timeout=30)
        if export_proc.returncode == 0:
            try:
                info = json.loads(export_proc.stdout).get("info",{})
                tokens = info.get("tokens",{})
                if tokens.get("input") is not None and tokens.get("output") is not None:
                    cache = tokens.get("cache",{})
                    usage["prompt_tokens"] = tokens["input"] + (cache.get("read",0) or 0) + (cache.get("write",0) or 0)
                    usage["completion_tokens"] = tokens["output"] + (tokens.get("reasoning",0) or 0)
                actual_cost = float(info["cost"]) if info.get("cost") is not None else None
            except (json.JSONDecodeError,TypeError,ValueError,KeyError):
                pass
    return json.loads(content), usage, actual_cost


def extract(row: dict, model: str = "simulator") -> tuple[dict, dict, float | None]:
    if model == "simulator":
        return parse_statement(row), {"prompt_tokens":0,"completion_tokens":0}, 0.0
    if model.startswith("ollama/"):
        result, usage, cost = _ollama_extract(row, model)
        return normalize_extraction(result), usage, cost
    if model.startswith("opencode/"):
        if not model.endswith("-free"):
            raise RuntimeError("OpenCode model is not explicitly marked free; V1 only allows explicitly free OpenCode routes")
        result, usage, cost = _opencode_extract(row, model)
        if model.endswith("-free"):
            cost = 0.0
        return normalize_extraction(result), usage, cost
    result, usage, cost = _openrouter_extract(row, model)
    if model.removeprefix("openrouter/").endswith(":free"):
        cost = 0.0
    return normalize_extraction(result), usage, cost


def ratios(x: dict) -> list[dict]:
    out = []
    for year in ("cy","py"):
        v = lambda k: x[k][year]
        out.append({"interest_coverage":v("operating_income")/v("interest_expense"),"current_ratio":v("total_current_assets")/v("total_current_liabilities"),"debt_to_equity":(v("current_portion_ltd")+v("long_term_debt"))/v("stockholders_equity"),"debt_to_ebitda":(v("current_portion_ltd")+v("long_term_debt"))/(v("operating_income")+v("depreciation_amortization")),"net_margin":v("net_income")/v("total_revenue")})
    return out


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def read_jsonl(path: Path) -> list[dict]:
    return list(iter_jsonl(path))


def file_sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def run(inputs_path: Path, truth_path: Path, model: str, retain_details: bool=True, cached_responses: dict | None=None, response_checkpoint: Path | None=None, delay_seconds: float=0.0) -> dict:
    start = time.perf_counter()
    records_requested=sum(1 for line in inputs_path.open(encoding="utf-8") if line.strip())
    extract_time = 0.0
    exact = correct = latent_correct = total = tie_fail = control_fail = prompt = completion = 0
    ratios_correct = latent_ratios_correct = ratios_total = ratios_exact_records = metadata_exact_count = records_processed = 0
    token_known_calls = 0
    schema_fail = missing_fail = value_fail = 0
    costs: list[float] = []
    errors = []
    details = []
    quality_stats={}
    provider_rate_limited=False
    for row,truth_row in zip_longest(iter_jsonl(inputs_path),iter_jsonl(truth_path),fillvalue=None):
        if provider_rate_limited: break
        if row is None or truth_row is None:
            raise ValueError("Frozen input and ground-truth files have different record counts")
        if row.get("id") != truth_row.get("id"):
            raise ValueError(f"Input/truth ID mismatch: {row.get('id')} vs {truth_row.get('id')}")
        truth = truth_row["truth"]
        latent_truth=truth_row.get("latent_truth",truth)
        records_processed += 1
        t = time.perf_counter()
        try:
            if cached_responses is not None and row["id"] in cached_responses:
                cached=cached_responses[row["id"]]
                got=normalize_extraction(cached.get("extraction",{})); usage=cached.get("usage",{}); cost=cached.get("cost")
                error=cached.get("error")
                if error: raise RuntimeError(error)
            else:
                got, usage, cost = extract(row, model)
                error = None
                if cached_responses is not None:
                    cached_responses[row["id"]]={"id":row["id"],"extraction":got,"usage":usage,"cost":cost,"error":None}
                    if response_checkpoint:
                        with response_checkpoint.open("a",encoding="utf-8",newline="\n") as checkpoint:
                            checkpoint.write(json.dumps(cached_responses[row["id"]],separators=(",",":"),sort_keys=True)+"\n")
                if delay_seconds > 0: time.sleep(delay_seconds)
        except Exception as exc:
            got, usage, cost, error = {}, {}, None, str(exc)
            provider_rate_limited=bool(re.search(r"429|rate.?limit|freeusagelimit|quota exceeded",error,re.I))
            if cached_responses is not None:
                cached_responses[row["id"]]={"id":row["id"],"extraction":{},"usage":{},"cost":None,"error":error}
                if response_checkpoint:
                    with response_checkpoint.open("a",encoding="utf-8",newline="\n") as checkpoint:
                        checkpoint.write(json.dumps(cached_responses[row["id"]],separators=(",",":"),sort_keys=True)+"\n")
        extract_time += time.perf_counter()-t
        prompt_value = usage.get("prompt_tokens",usage.get("input_tokens"))
        completion_value = usage.get("completion_tokens",usage.get("output_tokens"))
        if prompt_value is not None: prompt += prompt_value
        if completion_value is not None: completion += completion_value
        if prompt_value is not None and completion_value is not None: token_known_calls += 1
        if cost is not None: costs.append(cost)
        if error: errors.append({"id":row["id"],"error":error})
        record_ok = True
        for field in FIELDS:
            for year,pos in (("cy",0),("py",1)):
                field_value=got.get(field)
                extracted_value=field_value.get(year) if isinstance(field_value,dict) else None
                ok = extracted_value==truth[field][pos]
                latent_ok = extracted_value==latent_truth[field][pos]
                total += 1; correct += int(ok); record_ok &= ok
                latent_correct += int(latent_ok)
                value_fail += int(not ok)
        exact += int(record_ok)
        record_tie_fail = 0
        for year in ("cy","py"):
            try:
                record_tie_fail += int(got["gross_margin"][year]-got["research_and_development"][year]-got["sales_and_marketing"][year]-got["general_and_administrative"][year]-got["operating_income"][year] != 0)
            except (KeyError,TypeError):
                record_tie_fail += 1
        tie_fail += record_tie_fail
        expected_keys = {"company","form_type","fiscal_year_end","not_found",*FIELDS}
        malformed=any(not isinstance(got.get(f),dict) or any(not isinstance(got[f].get(y),(int,float)) for y in ("cy","py")) or not isinstance(got[f].get("page"),str) for f in FIELDS)
        missing = any(f not in got for f in FIELDS) or malformed
        missing_fail += int(missing)
        schema_fail += int(not isinstance(got,dict) or not expected_keys.issubset(got) or malformed)
        metadata_ok = got.get("company") == row.get("company") and got.get("form_type") == "10-K" and got.get("fiscal_year_end") == "June 30, 2026"
        metadata_exact_count += int(metadata_ok)
        control_fail += int(bool(got.get("not_found")) or missing or bool(error) or not metadata_ok or record_tie_fail > 0)
        got_ratios = None
        ratio_record_ok = False; latent_ratio_record_ok=False
        ratios_total += 10
        if not missing:
            try:
                got_ratios = ratios(got)
                truth_input = {k:{"cy":v[0],"py":v[1]} for k,v in truth.items()}
                truth_ratios = ratios(truth_input)
                ratio_record_ok = True
                latent_input={k:{"cy":v[0],"py":v[1]} for k,v in latent_truth.items()}
                latent_truth_ratios=ratios(latent_input)
                latent_ratio_record_ok=True
                for period in range(2):
                    for metric in truth_ratios[period]:
                        matches = abs(got_ratios[period][metric]-truth_ratios[period][metric]) <= 1e-12
                        ratios_correct += int(matches); ratio_record_ok &= matches
                        latent_matches=abs(got_ratios[period][metric]-latent_truth_ratios[period][metric])<=1e-12
                        latent_ratios_correct+=int(latent_matches); latent_ratio_record_ok &= latent_matches
            except (KeyError,TypeError,ZeroDivisionError):
                ratio_record_ok = False
        ratios_exact_records += int(ratio_record_ok)
        tier=row.get("quality_tier")
        if tier is not None:
            group=quality_stats.setdefault(str(tier),{"records":0,"fields_correct_source":0,"fields_correct_latent":0,"fields_total":0,"ratios_correct_source":0,"ratios_correct_latent":0,"ratios_total":0,"control_failures":0,"tieout_failures":0})
            group["records"]+=1; group["fields_correct_source"]+=sum(isinstance(got.get(f),dict) and got[f].get(y)==truth[f][p] for f in FIELDS for y,p in (("cy",0),("py",1)))
            group["fields_correct_latent"]+=sum(isinstance(got.get(f),dict) and got[f].get(y)==latent_truth[f][p] for f in FIELDS for y,p in (("cy",0),("py",1)))
            group["fields_total"]+=32; group["ratios_correct_source"]+=sum(abs(got_ratios[j][m]-ratios({k:{"cy":v[0],"py":v[1]} for k,v in truth.items()})[j][m])<=1e-12 for j in range(2) for m in got_ratios[j]) if got_ratios else 0
            group["ratios_correct_latent"]+=sum(abs(got_ratios[j][m]-ratios({k:{"cy":v[0],"py":v[1]} for k,v in latent_truth.items()})[j][m])<=1e-12 for j in range(2) for m in got_ratios[j]) if got_ratios else 0
            group["ratios_total"]+=10; group["control_failures"]+=int(bool(got.get("not_found")) or missing or bool(error) or not metadata_ok or record_tie_fail>0); group["tieout_failures"]+=record_tie_fail
        if retain_details:
            details.append({"id":row["id"],"record_exact":record_ok,"metadata_exact":metadata_ok,"ratio_exact":ratio_record_ok,"ratios":got_ratios,"gross_margin_tieout_failures":record_tie_fail,"error":error,"extraction":got})
    elapsed = time.perf_counter()-start
    provider = "simulator" if model=="simulator" else model.split("/",1)[0] if "/" in model else "openrouter"
    tokens_available = token_known_calls == records_processed or model == "simulator"
    ledger = json.loads(SPEND_LEDGER.read_text(encoding="utf-8")) if SPEND_LEDGER.exists() else {"cap_usd":2.0,"spent_usd":0.0,"reserved_usd":0.0}
    zero_cost_route = model=="simulator" or model.startswith("ollama/") or model.endswith(":free") or model.endswith("-free")
    for group in quality_stats.values():
        group["field_accuracy_source"]=group["fields_correct_source"]/group["fields_total"] if group["fields_total"] else 0
        group["field_accuracy_latent"]=group["fields_correct_latent"]/group["fields_total"] if group["fields_total"] else 0
        group["ratio_accuracy_source"]=group["ratios_correct_source"]/group["ratios_total"] if group["ratios_total"] else 0
        group["ratio_accuracy_latent"]=group["ratios_correct_latent"]/group["ratios_total"] if group["ratios_total"] else 0
    status="simulated extraction" if model=="simulator" else "stopped at provider rate limit" if provider_rate_limited else "completed" if not errors else "completed with provider errors"
    result = {"records":records_processed,"records_requested":records_requested,"seed":json.loads((ROOT/"data"/"manifest.json").read_text(encoding="utf-8")).get("seed"),"dataset_inputs":str(inputs_path.relative_to(ROOT)),"dataset_sha256":file_sha256(inputs_path),"truth_sha256":file_sha256(truth_path),"prompt_sha256":hashlib.sha256(PROMPT.encode()).hexdigest(),"model":model,"provider_route":provider,"elapsed_seconds":elapsed,"extraction_seconds":extract_time,"records_per_second":records_processed/elapsed if elapsed else 0,"field_accuracy":correct/total if total else 0,"field_accuracy_latent":latent_correct/total if total else 0,"fields_correct":correct,"fields_total":total,"record_exact_accuracy":exact/records_processed if records_processed else 0,"ratio_accuracy":ratios_correct/ratios_total if ratios_total else 0,"ratio_accuracy_latent":latent_ratios_correct/ratios_total if ratios_total else 0,"ratio_values_correct":ratios_correct,"ratio_values_latent_correct":latent_ratios_correct,"ratio_values_total":ratios_total,"ratio_exact_records":ratios_exact_records,"quality_tier_breakdown":quality_stats,"metadata_exact_records":metadata_exact_count,"metadata_accuracy":metadata_exact_count/records_processed if records_processed else 0,"tieout_failures":tie_fail,"control_failures":control_fail,"schema_failures":schema_fail,"missing_field_records":missing_fail,"incorrect_field_values":value_fail,"prompt_tokens":prompt if tokens_available else None,"completion_tokens":completion if tokens_available else None,"total_tokens":prompt+completion if tokens_available else None,"token_usage_available":tokens_available,"inference_cost_usd":0.0 if zero_cost_route else sum(costs) if len(costs)==records_processed else None,"priced_calls":records_processed if zero_cost_route else len(costs),"spending_cap_usd":ledger["cap_usd"],"paid_spend_to_date_usd":ledger["spent_usd"],"failed_calls":len(errors),"errors":errors,"ratios_deterministic":True,"summary_only":not retain_details,"status":status}
    if retain_details: result["details"] = details
    return result


def write_review_packet(result: dict, out: Path, rows: list[dict]) -> Path:
    review_id = hashlib.sha256((result["model"]+result["dataset_sha256"]).encode()).hexdigest()[:10].upper()
    target = out.with_name("gate1-review-" + review_id + ".csv")
    map_path = ROOT/"results"/"gate1-review-key.csv"
    known = {}
    if map_path.exists():
        with map_path.open(newline="",encoding="utf-8") as kf:
            known = {row["review_run_id"]:row for row in csv.DictReader(kf)}
    known[review_id] = {"review_run_id":review_id,"model":result["model"],"result_file":out.name}
    with map_path.open("w",newline="",encoding="utf-8") as kf:
        key_writer = csv.DictWriter(kf, fieldnames=["review_run_id","model","result_file"])
        key_writer.writeheader(); key_writer.writerows(known.values())
    with target.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["review_run_id","blinded_case_id","statement_text","extracted_json","borrower_matches_intake","latest_fiscal_year","no_missing_fields","tieout_both_years_pass","two_figures_spot_checked","reviewer_decision","reviewer_correction_json","review_reason","sendback_count","escalated"])
        writer.writeheader()
        for i, item in enumerate(result["details"]):
            writer.writerow({"review_run_id":review_id,"blinded_case_id":f"CASE-{item['id']:05d}","statement_text":rows[i]["text"],"extracted_json":json.dumps(item["extraction"],separators=(",",":")),"borrower_matches_intake":"","latest_fiscal_year":"","no_missing_fields":"","tieout_both_years_pass":"","two_figures_spot_checked":"","reviewer_decision":"","reviewer_correction_json":"","review_reason":"","sendback_count":0,"escalated":""})
    return target


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records",type=int,default=100)
    ap.add_argument("--profile",help="Dataset profile name used in frozen filenames (e.g. quality-mix)")
    ap.add_argument("--model",default="simulator",help="simulator, ollama/<tag>, opencode/<provider/model>, or OpenRouter model ID")
    ap.add_argument("--inputs",type=Path)
    ap.add_argument("--truth",type=Path)
    ap.add_argument("--run-name",help="Optional result filename stem for distinct cohorts")
    ap.add_argument("--responses",type=Path,help="JSONL response cache: replay saved responses and checkpoint new calls for resumable runs")
    ap.add_argument("--delay-seconds",type=float,default=0.0,help="Wait between fresh model calls to limit provider request rate")
    ap.add_argument("--summary-only",action="store_true",help="Avoid retaining per-record details or a review sheet on large simulator runs")
    a = ap.parse_args()
    stem=f"{a.profile}-{a.records}" if a.profile else str(a.records)
    inputs = (a.inputs or ROOT/"data"/f"statements-{stem}.jsonl").resolve()
    truth = (a.truth or ROOT/"data"/f"ground-truth-{stem}.jsonl").resolve()
    cached={}
    if a.responses:
        if a.responses.exists(): cached={item["id"]:item for item in iter_jsonl(a.responses.resolve())}
        known={row["id"] for row in iter_jsonl(inputs)}
        if set(cached)-known: raise ValueError(f"Response cache contains {len(set(cached)-known)} IDs outside the cohort")
    result = run(inputs,truth,a.model,retain_details=not a.summary_only,cached_responses=cached if a.responses else None,response_checkpoint=a.responses.resolve() if a.responses else None,delay_seconds=a.delay_seconds)
    safe_model = re.sub(r"[^A-Za-z0-9_.-]+","_",a.model)
    out = ROOT/"results"/f"{a.run_name or f'{safe_model}-{stem}'}.json"
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    review = write_review_packet(result,out,read_jsonl(inputs)) if not a.summary_only else None
    print(json.dumps({k:v for k,v in result.items() if k!="details"},indent=2))
    if review: print(f"Gate 1 review packet: {review.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
