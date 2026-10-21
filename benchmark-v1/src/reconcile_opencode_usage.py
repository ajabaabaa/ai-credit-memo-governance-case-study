"""Backfill usage for older OpenCode runs from local session metadata."""
import json
import re
import shutil
import subprocess
from pathlib import Path

from benchmark import ROOT


def opencode_exe() -> str:
    exe=shutil.which("opencode.exe")
    if not exe:
        shim=shutil.which("opencode.cmd")
        if shim: exe=str(Path(shim).parent/"node_modules"/"@opencode"/"cli"/"bin"/"opencode.exe")
    if not exe: raise SystemExit("OpenCode executable not found")
    return exe


def main() -> None:
    exe=opencode_exe()
    listing=subprocess.run([exe,"session","list","--max-count","10000","--format","json"],cwd=ROOT,capture_output=True,text=True,timeout=60)
    listing.check_returncode()
    sessions=[]
    for listed in json.loads(listing.stdout):
        exported=subprocess.run([exe,"session","export",listed["id"]],cwd=ROOT,capture_output=True,text=True,timeout=30)
        if exported.returncode: continue
        try: data=json.loads(exported.stdout); info=data.get("info",{})
        except json.JSONDecodeError: continue
        model=info.get("model",{})
        user_text="\n".join(m.get("text","") for m in data.get("messages",[]) if m.get("type")=="user")
        match=re.search(r"SYNTHETIC CO (\d{5}) \|",user_text)
        if not match: continue
        tokens=info.get("tokens",{}); cache=tokens.get("cache",{})
        sessions.append({"session_id":listed["id"],"model_id":model.get("id"),"provider_id":model.get("providerID"),"record_id":int(match.group(1)),"created_ms":info.get("time",{}).get("created",0),"prompt_tokens":(tokens.get("input") or 0)+(cache.get("read") or 0)+(cache.get("write") or 0),"completion_tokens":(tokens.get("output") or 0)+(tokens.get("reasoning") or 0),"cost":float(info.get("cost",0) or 0)})
    updated=0
    results=[]
    for path in sorted((ROOT/"results").glob("*.json")):
        result=json.loads(path.read_text(encoding="utf-8"))
        if result.get("provider_route")=="opencode" and result.get("details"):
            results.append((path,result))
    by_model={}
    for path,result in results:
        by_model.setdefault(result["model"].removeprefix("opencode/"),[]).append((path,result))
    for model_id,runs in by_model.items():
        ordered=sorted((s for s in sessions if s["provider_id"]=="opencode" and s["model_id"]==model_id),key=lambda s:s["created_ms"])
        assignments={}; upper_bound=None
        for path,result in sorted(runs,key=lambda pair:pair[1]["records"],reverse=True):
            n=result["records"]; expected=list(range(n)); candidates=[]
            for start in range(max(0,len(ordered)-n+1)):
                window=ordered[start:start+n]
                if [s["record_id"] for s in window]==expected and (upper_bound is None or window[-1]["created_ms"]<upper_bound):
                    candidates.append(window)
            if candidates:
                chosen=candidates[-1]
                assignments[path]=chosen
                upper_bound=chosen[0]["created_ms"]
        for path,result in runs:
            chosen=assignments.get(path)
            if not chosen: continue
            n=result["records"]
            result["opencode_sessions_matched"]=len(chosen)
            result["prompt_tokens"]=sum(s["prompt_tokens"] for s in chosen)
            result["completion_tokens"]=sum(s["completion_tokens"] for s in chosen)
            result["total_tokens"]=result["prompt_tokens"]+result["completion_tokens"]
            result["token_usage_available"]=True
            result["inference_cost_usd"]=sum(s["cost"] for s in chosen)
            result["priced_calls"]=n
            path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
            updated+=1
    print(f"Reconciled token and cost metadata for {updated} completed OpenCode runs from {len(sessions)} local sessions.")


if __name__=="__main__": main()
