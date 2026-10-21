from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = [
    ("openai/gpt-oss-20b:batch", "openrouter-batch-openai_gpt-oss-20b_batch.json", "openrouter-openai_gpt-oss-20b_batch-quality-mix-10000.json"),
    ("mistralai/ministral-8b-2512:batch", "openrouter-batch-mistralai_ministral-8b-2512_batch.json", "openrouter-mistralai_ministral-8b-2512_batch-quality-mix-10000.json"),
]

rows = []
for model, raw_name, result_name in MODELS:
    raw = json.loads((ROOT / "results" / raw_name).read_text(encoding="utf-8"))
    result = json.loads((ROOT / "results" / result_name).read_text(encoding="utf-8"))
    reasons = Counter()
    parsed = 0
    for item in raw.get("results") or []:
        choices = (item.get("response") or {}).get("body", {}).get("choices") or []
        finish = choices[0].get("finish_reason", "error") if choices else "error"
        reasons[finish] += 1
        if choices:
            try:
                json.loads(choices[0].get("message", {}).get("content", ""))
                parsed += 1
            except (json.JSONDecodeError, TypeError):
                pass
    total = (raw.get("request_counts") or {}).get("total", 0)
    provider_completed = (raw.get("request_counts") or {}).get("completed", 0)
    usable = max(0, parsed - result.get("schema_failures", 0))
    rows.append({
        "model": model,
        "records": total,
        "provider_completed": provider_completed,
        "provider_failed": (raw.get("request_counts") or {}).get("failed", 0),
        "finish_length": reasons["length"],
        "json_parse_failures": total - parsed,
        "parsed_but_schema_incomplete": max(0, parsed - usable),
        "schema_complete_records": usable,
        "field_accuracy_source": result.get("field_accuracy", 0),
        "latent_ratio_accuracy": result.get("ratio_accuracy_latent", 0),
        "batch_cost_usd": raw.get("usage", {}).get("cost"),
        "batch_seconds": result.get("batch_elapsed_seconds"),
    })

with (ROOT / "results" / "batch_output_integrity.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

W, H = 1120, 390
left, right = 270, 120
barw = W - left - right
colors = {"parse": "#f06b78", "schema": "#f1b34f", "valid": "#32c989"}
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<rect width="100%" height="100%" fill="#0f131d"/>', '<style>text{font-family:Arial,sans-serif;fill:#dfe2f1}.muted{fill:#9aa6b2;font-size:13px}</style>', '<text x="560" y="34" text-anchor="middle" font-size="22" font-weight="700">10,000-record batch output integrity</text>', '<text x="560" y="58" text-anchor="middle" class="muted">All requests reached providers; truncated or incomplete JSON prevented valid schema scoring.</text>']
for i, row in enumerate(rows):
    y = 110 + i * 115
    svg.append(f'<text x="{left-16}" y="{y+24}" text-anchor="end" font-size="14">{row["model"]}</text>')
    sections = [("json_parse_failures", "parse", "JSON parse failed"), ("parsed_but_schema_incomplete", "schema", "Parsed, schema incomplete"), ("schema_complete_records", "valid", "Schema complete")]
    x = left
    for field, color, label in sections:
        count = row[field]
        width = barw * count / max(1, row["records"])
        if width > 0:
            svg.append(f'<rect x="{x}" y="{y}" width="{width}" height="38" fill="{colors[color]}"/>')
            if width > 82:
                svg.append(f'<text x="{x+width/2}" y="{y+24}" text-anchor="middle" font-size="13" fill="#10131a">{count:,} {label}</text>')
            x += width
    svg.append(f'<text x="{left}" y="{y+61}" class="muted">cost ${row["batch_cost_usd"]:.4f} · {row["finish_length"]:,} finish_reason=length · {row["provider_completed"]:,}/{row["records"]:,} provider-completed</text>')
svg.append('</svg>')
(ROOT / "results" / "batch_output_integrity.svg").write_text("\n".join(svg), encoding="utf-8")
print("Wrote 2 model batch integrity summaries to results/batch_output_integrity.svg and .csv")
