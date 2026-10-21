from __future__ import annotations

import hashlib
import json
import random
import argparse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
SOURCE=DATA/"statements-quality-mix-10000.jsonl"
TRUTH=DATA/"ground-truth-quality-mix-10000.jsonl"
def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--per-layout",type=int,default=1); a=ap.parse_args()
    inputs=[json.loads(line) for line in SOURCE.open(encoding="utf-8")]
    truths=[json.loads(line) for line in TRUTH.open(encoding="utf-8")]
    truth_by_id={row["id"]:row for row in truths}
    selected=[]
    for tier in (50,75,100):
        for layout in range(8):
            candidates=[row for row in inputs if row.get("quality_tier")==tier and row["id"]%8==layout]
            selected.extend(random.Random(20261020+tier*31+layout).sample(candidates,a.per_layout))
    selected.sort(key=lambda row:row["id"])
    ih=hashlib.sha256(); th=hashlib.sha256()
    n=len(selected); stem=f"quality-mix-sample-{n}"
    in_path=DATA/f"statements-{stem}.jsonl"
    truth_path=DATA/f"ground-truth-{stem}.jsonl"
    with in_path.open("w",encoding="utf-8",newline="\n") as fi, truth_path.open("w",encoding="utf-8",newline="\n") as ft:
        for row in selected:
            i=json.dumps(row,separators=(",",":"),sort_keys=True)+"\n"
            t=json.dumps(truth_by_id[row["id"]],separators=(",",":"),sort_keys=True)+"\n"
            fi.write(i); ft.write(t); ih.update(i.encode()); th.update(t.encode())
    info={"records":len(selected),"per_tier":{str(tier):sum(r["quality_tier"]==tier for r in selected) for tier in (50,75,100)},"layouts_per_tier":{"8 statement styles × sampled records":a.per_layout},"selection":"deterministic, stratified by quality tier and statement style; seed 20261020","inputs":in_path.name,"inputs_sha256":ih.hexdigest(),"ground_truth":truth_path.name,"ground_truth_sha256":th.hexdigest()}
    (DATA/f"{stem}.json").write_text(json.dumps(info,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(info,indent=2))

if __name__=="__main__": main()
