"""Rescore saved model outputs against the frozen truth without rerunning inference."""
import hashlib
import json
import sys
from pathlib import Path

from benchmark import FIELDS, PROMPT, ROOT, ratios, read_jsonl


def main() -> None:
    updated = 0
    for path in sorted((ROOT / "results").glob("*.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        if "details" not in result or "dataset_inputs" not in result:
            continue
        inputs_path = ROOT / result["dataset_inputs"]
        truth_path = ROOT / "data" / f"ground-truth-{result['records']}.jsonl"
        rows = {r["id"]:r for r in read_jsonl(inputs_path)}
        truths = {r["id"]:r["truth"] for r in read_jsonl(truth_path)}
        values_correct = fields_total = exact = meta_exact = ties = controls = schemas = missing_records = 0
        ratio_correct = ratio_total = ratio_exact = 0
        failed_ids = {e["id"] for e in result.get("errors",[])}
        for item in result["details"]:
            idx = item["id"]; got = item.get("extraction",{}); truth = truths[idx]; row = rows[idx]
            ok_record = True
            for field in FIELDS:
                for year,pos in (("cy",0),("py",1)):
                    ok = got.get(field,{}).get(year)==truth[field][pos]
                    fields_total += 1; values_correct += int(ok); ok_record &= ok
            exact += int(ok_record)
            metadata = got.get("company")==row.get("company") and got.get("form_type")=="10-K" and got.get("fiscal_year_end")=="June 30, 2026"
            meta_exact += int(metadata)
            missing = any(f not in got for f in FIELDS)
            missing_records += int(missing)
            tie_record = 0
            for y in ("cy","py"):
                try:
                    tie_record += int(got["gross_margin"][y]-got["research_and_development"][y]-got["sales_and_marketing"][y]-got["general_and_administrative"][y]-got["operating_income"][y] != 0)
                except (KeyError,TypeError):
                    tie_record += 1
            ties += tie_record
            expected_keys = {"company","form_type","fiscal_year_end","not_found",*FIELDS}
            schema = isinstance(got,dict) and expected_keys.issubset(got)
            schemas += int(not schema)
            controls += int(idx in failed_ids or missing or bool(got.get("not_found")) or not metadata or tie_record>0)
            ratios_out = None; ratio_ok = False
            ratio_total += 10
            if not missing:
                try:
                    ratios_out = ratios(got)
                    truth_values = {k:{"cy":v[0],"py":v[1]} for k,v in truth.items()}
                    ratios_truth = ratios(truth_values)
                    ratio_ok = True
                    for p in range(2):
                        for metric in ratios_truth[p]:
                            match = abs(ratios_out[p][metric]-ratios_truth[p][metric]) <= 1e-12
                            ratio_correct += int(match); ratio_ok &= match
                except (KeyError,TypeError,ZeroDivisionError):
                    ratio_ok = False
            ratio_exact += int(ratio_ok)
            item.update({"record_exact":ok_record,"metadata_exact":metadata,"ratio_exact":ratio_ok,"ratios":ratios_out,"gross_margin_tieout_failures":tie_record})
        n = result["records"]
        free_or_local = result["model"]=="simulator" or result["model"].startswith("ollama/") or result["model"].endswith(":free") or result["model"].endswith("-free")
        result.update({"prompt_sha256":hashlib.sha256(PROMPT.encode()).hexdigest(),"field_accuracy":values_correct/fields_total if fields_total else 0,"fields_correct":values_correct,"fields_total":fields_total,"record_exact_accuracy":exact/n if n else 0,"ratio_accuracy":ratio_correct/ratio_total if ratio_total else 0,"ratio_values_correct":ratio_correct,"ratio_values_total":ratio_total,"ratio_exact_records":ratio_exact,"metadata_exact_records":meta_exact,"metadata_accuracy":meta_exact/n if n else 0,"tieout_failures":ties,"control_failures":controls,"schema_failures":schemas,"missing_field_records":missing_records,"incorrect_field_values":fields_total-values_correct,"inference_cost_usd":0.0 if free_or_local else result.get("inference_cost_usd"),"priced_calls":n if free_or_local else result.get("priced_calls",0)})
        path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
        updated += 1
    print(f"Rescored {updated} saved result files against frozen truth.")


if __name__ == "__main__":
    main()
