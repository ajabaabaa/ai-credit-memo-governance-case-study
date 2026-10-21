from __future__ import annotations
import argparse, json, re, shutil, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def cli(args):
    exe=shutil.which("opencode.exe") or shutil.which("opencode")
    if not exe: raise RuntimeError("OpenCode CLI not found")
    return subprocess.run([exe,*args],cwd=ROOT,capture_output=True,text=True,timeout=60)

def main():
    ap=argparse.ArgumentParser(description="Recover completed synthetic OpenCode responses by exact model and creation-time window.")
    ap.add_argument("--since-ms",type=int,required=True,help="Unix milliseconds: first allowed session creation time")
    ap.add_argument("--model",required=True)
    ap.add_argument("--expected",type=Path,required=True,help="Frozen cohort input JSONL")
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    wanted={r["id"] for r in (json.loads(line) for line in a.expected.open(encoding="utf-8"))}
    listing=cli(["session","list","--max-count","200","--format","json"])
    if listing.returncode: raise RuntimeError(listing.stderr)
    sessions=json.loads(listing.stdout)
    output={}
    for session in sessions:
        if session.get("created",0)<a.since_ms or session.get("directory")!=str(ROOT): continue
        exported=cli(["session","export",session["id"]])
        if exported.returncode: continue
        try: data=json.loads(exported.stdout)
        except json.JSONDecodeError: continue
        info=data.get("info",{}); model=info.get("model",{})
        if model.get("id")!=a.model: continue
        prompt=next((m.get("text","") for m in data.get("messages",[]) if m.get("type")=="user"),"")
        match=re.search(r"SYNTHETIC CO (\d{5})",prompt)
        if not match: continue
        record_id=int(match.group(1))
        if record_id not in wanted: continue
        texts=[]
        for message in data.get("messages",[]):
            if message.get("type")=="assistant":
                texts.extend(part.get("text","") for part in message.get("content",[]) if part.get("type")=="text")
        content="\n".join(texts).strip()
        extraction=None; error=None
        if content:
            start=content.find("{")
            if start>=0:
                try: extraction=json.JSONDecoder().raw_decode(content[start:])[0]
                except json.JSONDecodeError as exc: error=f"Saved assistant response is not valid JSON: {exc}"
            else: error="Saved assistant response contained no JSON object"
        else: error="No assistant text in saved OpenCode session"
        tokens=info.get("tokens",{}); cache=tokens.get("cache",{})
        output[record_id]={"id":record_id,"session_id":session["id"],"extraction":extraction or {},"usage":{"prompt_tokens":(tokens.get("input") or 0)+(cache.get("read") or 0)+(cache.get("write") or 0),"completion_tokens":(tokens.get("output") or 0)+(tokens.get("reasoning") or 0)},"cost":info.get("cost",0),"error":error}
    if set(output)!=wanted:
        raise RuntimeError(f"Recovered response IDs mismatch: expected {len(wanted)}, recovered {len(output)}, missing={sorted(wanted-set(output))[:20]}, extra={sorted(set(output)-wanted)[:20]}")
    path=a.output if a.output.is_absolute() else ROOT/a.output
    with path.open("w",encoding="utf-8",newline="\n") as f:
        for record_id in sorted(output): f.write(json.dumps(output[record_id],separators=(",",":"),sort_keys=True)+"\n")
    print(json.dumps({"recovered":len(output),"model":a.model,"output":str(path.relative_to(ROOT)),"failed_responses":sum(bool(x["error"]) for x in output.values()),"tokens":sum(x["usage"]["prompt_tokens"]+x["usage"]["completion_tokens"] for x in output.values()),"cost":sum(float(x["cost"] or 0) for x in output.values())},indent=2))

if __name__=="__main__": main()
