from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import tiktoken

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import benchmark  # noqa: E402

API = "https://openrouter.ai/api/v1"
STATE_PATH = ROOT / "results" / "openrouter-batch-state.json"
MAX_TOKENS = 1600
INPUT_BUFFER = 1.20
MODELS = ["openai/gpt-oss-20b:batch", "mistralai/ministral-8b-2512:batch"]


def api_json(path: str, method: str = "GET", payload: dict | None = None, timeout: int = 600) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    data = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
    req = Request(API + path, data=data, method=method, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:1500]
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"OpenRouter connection failed: {exc.reason}") from exc


def catalog_price(model: str) -> tuple[float, float, str]:
    catalog = api_json("/models")
    found = next((item for item in catalog.get("data", []) if item.get("id") == model), None)
    if not found:
        raise RuntimeError(f"Model {model} is not listed in the live OpenRouter catalog")
    pricing = found.get("pricing", {})
    return float(pricing["prompt"]), float(pricing["completion"]), found.get("name", model)


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def submit() -> None:
    inputs = ROOT / "data" / "statements-quality-mix-10000.jsonl"
    truth = ROOT / "data" / "ground-truth-quality-mix-10000.jsonl"
    rows = list(benchmark.iter_jsonl(inputs))
    tokenizer = tiktoken.get_encoding("cl100k_base")
    input_tokens = sum(len(tokenizer.encode(benchmark.PROMPT + row["text"])) for row in rows)
    records = len(rows)
    if records != 10000:
        raise RuntimeError(f"Expected the frozen 10,000-record cohort, found {records}")
    ledger = json.loads(benchmark.SPEND_LEDGER.read_text(encoding="utf-8"))
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if state.get("status") in {"completed", "failed", "cancelled", "expired"}:
            raise RuntimeError("A terminal OpenRouter batch state already exists; do not resubmit the same cohort")
        if state.get("input_sha256") != benchmark.file_sha256(inputs) or state.get("truth_sha256") != benchmark.file_sha256(truth):
            raise RuntimeError("Existing batch state belongs to different cohort hashes")
        if any(job.get("status") == "submission error or unknown outcome; reservation retained" for job in state["jobs"]):
            raise RuntimeError("A prior submission outcome is unknown; reconcile its batch ID before retrying")
        if not any(job.get("status") == "reserved" and not job.get("batch_id") for job in state["jobs"]):
            raise RuntimeError("All reserved models were submitted; use poll instead of submitting again")
    else:
        estimates = []
        for model in MODELS:
            in_rate, out_rate, display_name = catalog_price(model)
            estimate = input_tokens * INPUT_BUFFER * in_rate + records * MAX_TOKENS * out_rate
            estimates.append({"model": model, "display_name": display_name, "input_rate": in_rate, "output_rate": out_rate, "estimate_usd": estimate})
        reserve_total = sum(item["estimate_usd"] for item in estimates)
        available = ledger["cap_usd"] - ledger["spent_usd"] - ledger.get("reserved_usd", 0.0)
        if reserve_total > available:
            raise RuntimeError(f"Batch preflight blocked: ${reserve_total:.6f} estimated versus ${available:.6f} remaining")

        # Reserve both entire jobs before submitting either one, so concurrent provider work remains inside the cap.
        ledger["reserved_usd"] = ledger.get("reserved_usd", 0.0) + reserve_total
        state = {
            "status": "submitting",
            "cohort": "quality-mix-10000",
            "records": records,
            "input_sha256": benchmark.file_sha256(inputs),
            "truth_sha256": benchmark.file_sha256(truth),
            "prompt_sha256": __import__("hashlib").sha256(benchmark.PROMPT.encode()).hexdigest(),
            "input_token_estimate_cl100k": input_tokens,
            "input_token_buffer": INPUT_BUFFER,
            "max_output_tokens_per_record": MAX_TOKENS,
            "jobs": [],
        }
        for item in estimates:
            item["call_id"] = __import__("hashlib").sha256(f"batch|{item['model']}|{state['input_sha256']}".encode()).hexdigest()[:16]
            item["status"] = "reserved"
            state["jobs"].append(item)
            ledger["entries"].append({"call_id": item["call_id"], "model": item["model"], "records": records, "reserved_usd": item["estimate_usd"], "status": "batch reserved before submission"})
        benchmark.SPEND_LEDGER.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        save_json(STATE_PATH, state)

    for job in state["jobs"]:
        if job.get("status") != "reserved" or job.get("batch_id"):
            continue
        requests = []
        for row in rows:
            requests.append({
                "custom_id": f"rec-{row['id']}",
                "body": {
                    "messages": [{"role": "user", "content": benchmark.PROMPT + row["text"]}],
                    "response_format": {"type": "json_object"},
                    "max_tokens": MAX_TOKENS,
                    "temperature": 0,
                },
            })
        payload = {"endpoint": "/v1/chat/completions", "model": job["model"], "completion_window": "24h", "requests": requests}
        job["status"] = "submitting"
        save_json(STATE_PATH, state)
        try:
            response = api_json("/batches", method="POST", payload=payload)
        except Exception as exc:
            job["status"] = "submission error or unknown outcome; reservation retained"
            job["error"] = str(exc)
            state["status"] = "submission needs reconciliation"
            save_json(STATE_PATH, state)
            raise
        job["batch_id"] = response["id"]
        job["provider"] = response.get("provider")
        job["provider_status"] = response.get("status")
        job["status"] = "submitted"
        state["status"] = "submitted"
        save_json(STATE_PATH, state)
        for entry in reversed(ledger["entries"]):
            if entry["call_id"] == job["call_id"]:
                entry["batch_id"] = job["batch_id"]
                entry["provider"] = job["provider"]
                entry["status"] = "batch submitted"
                break
        benchmark.SPEND_LEDGER.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"model": job["model"], "batch_id": job["batch_id"], "provider": job["provider"], "status": job["provider_status"], "reserved_usd": round(job["estimate_usd"], 6)}), flush=True)
    state["status"] = "in_progress"
    save_json(STATE_PATH, state)


def poll(wait: bool = True, interval: int = 30) -> None:
    if not STATE_PATH.exists():
        raise RuntimeError("No OpenRouter batch state file exists")
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    terminal = {"completed", "failed", "expired", "cancelled"}
    while True:
        pending = False
        for job in state["jobs"]:
            if not job.get("batch_id") or job.get("status") in terminal:
                continue
            response = api_json("/batches/" + job["batch_id"])
            job["provider_status"] = response.get("status")
            job["counts"] = response.get("request_counts")
            job["provider"] = response.get("provider", job.get("provider"))
            if response.get("status") in terminal:
                job["status"] = response["status"]
                job["actual_cost_usd"] = (response.get("usage") or {}).get("cost")
                job["aggregate_usage"] = response.get("usage")
                raw_path = ROOT / "results" / f"openrouter-batch-{re.sub(r'[^A-Za-z0-9_.-]+','_',job['model'])}.json"
                save_json(raw_path, response)
                job["raw_results"] = raw_path.name
                settle_job(job, response)
                save_json(STATE_PATH, state)
            else:
                pending = True
        state["status"] = "in_progress" if pending else "completed"
        save_json(STATE_PATH, state)
        print(json.dumps({"status": state["status"], "jobs": [{"model": j["model"], "status": j["status"], "counts": j.get("counts")} for j in state["jobs"]]}), flush=True)
        if not pending or not wait:
            return
        time.sleep(interval)


def settle_job(job: dict, response: dict) -> None:
    ledger = json.loads(benchmark.SPEND_LEDGER.read_text(encoding="utf-8"))
    charge = job.get("actual_cost_usd")
    if charge is None:
        charge = job["estimate_usd"]
        status = "conservative charge; provider did not report batch cost"
    else:
        charge = float(charge)
        status = "settled batch cost"
    ledger["reserved_usd"] = max(0.0, ledger.get("reserved_usd", 0.0) - job["estimate_usd"])
    ledger["spent_usd"] += charge
    for entry in reversed(ledger["entries"]):
        if entry["call_id"] == job["call_id"]:
            entry.update({"actual_or_conservative_usd": charge, "status": status, "provider_status": response.get("status"), "request_counts": response.get("request_counts")})
            break
    benchmark.SPEND_LEDGER.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def score() -> None:
    if not STATE_PATH.exists():
        raise RuntimeError("No OpenRouter batch state file exists")
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    inputs = ROOT / "data" / "statements-quality-mix-10000.jsonl"
    truth = ROOT / "data" / "ground-truth-quality-mix-10000.jsonl"
    if benchmark.file_sha256(inputs) != state["input_sha256"] or benchmark.file_sha256(truth) != state["truth_sha256"]:
        raise RuntimeError("Frozen cohort hashes do not match the submitted batches")
    for job in state["jobs"]:
        if job.get("status") != "completed":
            continue
        raw_path = ROOT / "results" / job["raw_results"]
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        cache = {}
        for item in raw.get("results") or []:
            match = re.fullmatch(r"rec-(\d+)", item.get("custom_id", ""))
            if not match:
                continue
            record_id = int(match.group(1))
            try:
                body = item["response"]["body"]
                content = body["choices"][0]["message"]["content"]
                content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
                extraction = json.loads(content)
                error = None
                usage = body.get("usage", {})
                cost = usage.get("cost")
            except Exception as exc:
                extraction, error, usage, cost = {}, str(exc), {}, None
            cache[record_id] = {"id": record_id, "extraction": extraction, "usage": usage, "cost": cost, "error": error}
        for row in benchmark.iter_jsonl(inputs):
            cache.setdefault(row["id"], {"id": row["id"], "extraction": {}, "usage": {}, "cost": None, "error": "Missing result in completed batch response"})
        cache_path = ROOT / "results" / f"openrouter-responses-{re.sub(r'[^A-Za-z0-9_.-]+','_',job['model'])}-quality-mix-10000.jsonl"
        with cache_path.open("w", encoding="utf-8", newline="\n") as out:
            for record_id in sorted(cache):
                out.write(json.dumps(cache[record_id], separators=(",", ":"), sort_keys=True) + "\n")
        result = benchmark.run(inputs, truth, "openrouter/" + job["model"], cached_responses=cache)
        usage = job.get("aggregate_usage") or {}
        batch_elapsed = max(0, (raw.get("finalized_at") or raw.get("created_at") or 0) - (raw.get("created_at") or 0))
        result.update({
            "model": "openrouter/" + job["model"],
            "provider_route": "openrouter_batch/" + str(job.get("provider") or "provider-not-reported"),
            "transport": "OpenRouter Batch API",
            "batch_id": job["batch_id"],
            "batch_status": job["status"],
            "batch_input_sha256": state["input_sha256"],
            "batch_truth_sha256": state["truth_sha256"],
            "total_tokens": usage.get("total_tokens"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "token_usage_available": usage.get("total_tokens") is not None,
            "inference_cost_usd": job.get("actual_cost_usd"),
            "priced_calls": (job.get("counts") or {}).get("completed", 0),
            "batch_request_counts": job.get("counts"),
            "batch_response_cache": cache_path.name,
            "batch_elapsed_seconds": batch_elapsed,
            "elapsed_seconds": batch_elapsed,
            "extraction_seconds": batch_elapsed,
            "records_per_second": result["records"] / batch_elapsed if batch_elapsed else 0,
            "exclude_from_dashboard": True,
            "exclude_from_quality_comparison": True,
            "comparability_note": "All batch requests reached the provider, but the 640-token completion cap truncated model JSON outputs. This is an output-budget failure, not a valid model-accuracy comparison; excluded from performance charts.",
        })
        result_path = ROOT / "results" / f"openrouter-{re.sub(r'[^A-Za-z0-9_.-]+','_',job['model'])}-quality-mix-10000.json"
        save_json(result_path, result)
        review_path = benchmark.write_review_packet(result, result_path, benchmark.read_jsonl(inputs))
        print(json.dumps({"model": result["model"], "records": result["records"], "status": result["status"], "result": result_path.name, "review": review_path.name, "cost_usd": result["inference_cost_usd"], "ratio_accuracy_latent": result["ratio_accuracy_latent"]}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit and score same-cohort OpenRouter batch inference")
    parser.add_argument("action", choices=["submit", "poll", "score"])
    parser.add_argument("--once", action="store_true", help="Poll once instead of waiting for terminal status")
    args = parser.parse_args()
    if args.action == "submit":
        submit()
    elif args.action == "poll":
        poll(wait=not args.once)
    else:
        score()


if __name__ == "__main__":
    main()
