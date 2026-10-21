from __future__ import annotations

import hashlib
import json
import sys
import argparse
from pathlib import Path

from benchmark import iter_generate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def write_pair(n: int, seed: int, profile: str="baseline") -> dict:
    input_hash=hashlib.sha256(); truth_hash=hashlib.sha256()
    stem=f"{profile}-{n}" if profile!="baseline" else str(n)
    qa_hash=hashlib.sha256(); tier_counts={}; exact_counts={}; defect_counts={}
    qa_path=DATA/f"qa-{stem}.jsonl"
    with (DATA/f"statements-{stem}.jsonl").open("w",encoding="utf-8",newline="\n") as input_file, (DATA/f"ground-truth-{stem}.jsonl").open("w",encoding="utf-8",newline="\n") as truth_file, qa_path.open("w",encoding="utf-8",newline="\n") as qa_file:
        for row in iter_generate(n,seed,realistic=profile=="filing-like",quality_mix=profile=="quality-mix"):
            input_obj={"id":row["id"],"company":row["company"],"text":row["text"]}
            if "quality_tier" in row: input_obj["quality_tier"]=row["quality_tier"]
            input_line=json.dumps(input_obj,separators=(",",":"),sort_keys=True)+"\n"
            truth_obj={"id":row["id"],"truth":row["truth"]}
            if "latent_truth" in row: truth_obj["latent_truth"]=row["latent_truth"]
            truth_line=json.dumps(truth_obj,separators=(",",":"),sort_keys=True)+"\n"
            input_file.write(input_line); truth_file.write(truth_line)
            input_hash.update(input_line.encode()); truth_hash.update(truth_line.encode())
            if "quality_tier" in row:
                tier=str(row["quality_tier"]); tier_counts[tier]=tier_counts.get(tier,0)+1
                total=len(row["truth"])*2; exact=sum(row["truth"][k][j]==row["latent_truth"][k][j] for k in row["truth"] for j in (0,1))
                exact_counts[tier]=exact_counts.get(tier,0)+exact
                for defect in row["defects"]: defect_counts[defect["type"]]=defect_counts.get(defect["type"],0)+1
                qa_line=json.dumps({"id":row["id"],"quality_tier":row["quality_tier"],"exact_numeric_fields":exact,"numeric_fields":total,"defects":row["defects"]},separators=(",",":"),sort_keys=True)+"\n"
                qa_file.write(qa_line); qa_hash.update(qa_line.encode())
    return {"inputs_sha256":input_hash.hexdigest(),"ground_truth_sha256":truth_hash.hexdigest(),"qa_sha256":qa_hash.hexdigest() if profile=="quality-mix" else None,"quality_assurance":{"tier_records":tier_counts,"exact_numeric_fields":exact_counts,"numeric_fields_per_tier":{k:v*32 for k,v in tier_counts.items()},"defect_counts":defect_counts} if profile=="quality-mix" else None}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("sizes",nargs="*",type=int)
    parser.add_argument("--profile",choices=("baseline","filing-like","quality-mix"),default="baseline")
    args=parser.parse_args()
    sizes = args.sizes or ([10000] if args.profile=="filing-like" else [1, 10, 100, 1000, 10000, 100000, 1000000])
    DATA.mkdir(exist_ok=True)
    manifest_path=DATA/"manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"seed":20261020,"generator":"src/benchmark.py:iter_generate","schema_version":"source-16-fields-v1","datasets":{}}
    manifest["generator"]="src/benchmark.py:iter_generate"
    for n in sizes:
        hashes = write_pair(n,manifest["seed"],args.profile)
        stem=f"{args.profile}-{n}" if args.profile!="baseline" else str(n)
        entry={"records":n,"profile":args.profile,"inputs":f"statements-{stem}.jsonl","ground_truth":f"ground-truth-{stem}.jsonl",**hashes}
        if args.profile=="quality-mix": entry["qa"]=f"qa-{stem}.jsonl"
        manifest["datasets"][stem]=entry
        print(f"{stem}: inputs sha256={hashes['inputs_sha256']}; truth sha256={hashes['ground_truth_sha256']}; QA={hashes['quality_assurance']}")
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {DATA / 'manifest.json'}")


if __name__ == "__main__":
    main()
