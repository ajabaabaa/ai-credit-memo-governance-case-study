import csv,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
data=[]
for path in (ROOT/"results").glob("*.json"):
    try:r=json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError,UnicodeDecodeError):continue
    if r.get("dataset_inputs","").endswith("statements-quality-mix-sample-24.jsonl") and r.get("records")==24 and r.get("failed_calls")==0 and r.get("status")=="completed":
        data.append(r)
data.sort(key=lambda r:r["model"])
if not data: raise SystemExit("No complete 24-record quality-mix model runs")
with (ROOT/"results"/"quality_sensitivity.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.writer(f);w.writerow(["model","quality_tier","records","field_accuracy_source","field_accuracy_latent","ratio_accuracy_source","ratio_accuracy_latent","control_failures","tieout_failures"])
    for r in data:
        for tier in ("50","75","100"):
            g=r["quality_tier_breakdown"][tier]
            w.writerow([r["model"],tier,g["records"],g["field_accuracy_source"],g["field_accuracy_latent"],g["ratio_accuracy_source"],g["ratio_accuracy_latent"],g["control_failures"],g["tieout_failures"]])

W,H=1050,790; colors=["#00c9e8","#74a5ff","#32c989","#e2a345"]
metrics=[("field_accuracy_source","Extraction match to displayed source"),("field_accuracy_latent","Extracted fields matching clean latent values"),("ratio_accuracy_latent","Deterministic ratios matching clean latent values")]
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">','<rect width="100%" height="100%" fill="#0f131d"/>','<style>text{font-family:Arial,sans-serif;fill:#dfe2f1}.muted{fill:#849495;font-size:12px}.grid{stroke:#303943;stroke-width:1}</style>','<text x="525" y="30" text-anchor="middle" font-size="22" font-weight="700">Source-quality sensitivity · 24-record stratified pilots</text>']
left,right=125,50; pw=W-left-right; gap=28; ph=190; xvals=[50,75,100]
for p,(metric,title) in enumerate(metrics):
    top=65+p*(ph+gap); bottom=top+ph
    svg.append(f'<text x="{left}" y="{top-12}" font-size="15" font-weight="700">{title}</text>')
    for tick in (0,0.25,0.5,0.75,1):
        y=bottom-ph*tick;svg.append(f'<line class="grid" x1="{left}" y1="{y}" x2="{W-right}" y2="{y}"/>');svg.append(f'<text class="muted" x="{left-12}" y="{y+4}" text-anchor="end">{tick:.0%}</text>')
    for j,tier in enumerate(xvals):
        x=left+pw*j/2;svg.append(f'<text class="muted" x="{x}" y="{bottom+20}" text-anchor="middle">{tier}% source quality</text>')
    for ix,r in enumerate(data):
        vals=[r["quality_tier_breakdown"][str(t)][metric] for t in xvals]; pts=[]
        for j,v in enumerate(vals):
            x=left+pw*j/2;y=bottom-ph*v;pts.append((x,y));svg.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{colors[ix%len(colors)]}"/>')
        svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{colors[ix%len(colors)]}" stroke-width="2.5"/>')
        if p==0: svg.append(f'<line x1="{left+ix*220}" y1="{H-24}" x2="{left+ix*220+18}" y2="{H-24}" stroke="{colors[ix%len(colors)]}" stroke-width="3"/><text class="muted" x="{left+ix*220+24}" y="{H-20}">{r["model"]}</text>')
svg.append('</svg>')
(ROOT/"results"/"quality_sensitivity.svg").write_text("\n".join(svg),encoding="utf-8")
print(f"Plotted {len(data)} complete model curves to results/quality_sensitivity.svg and results/quality_sensitivity.csv")
