"""Create reproducible, publication-ready SVG figures for the article."""
from __future__ import annotations
import csv, json
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = ROOT / "article" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
COLORS = {"deepseek":"#35d4ff", "minimax":"#8b7bff", "qwen":"#42e6a4", "amber":"#ffbc55", "red":"#ff667d"}
plt.rcParams.update({"figure.facecolor":"#0c111b", "axes.facecolor":"#111a27", "axes.edgecolor":"#344456", "axes.labelcolor":"#d9e6f2", "xtick.color":"#a9b9c8", "ytick.color":"#a9b9c8", "text.color":"#e8f0f8", "grid.color":"#283747", "font.family":"DejaVu Sans", "font.size":10})

def finish(name):
    plt.tight_layout()
    plt.savefig(OUT / name, format="svg", bbox_inches="tight", facecolor="#0c111b")
    raster_dir = ROOT / "tmp" / "pdfs"
    raster_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(raster_dir / f"{Path(name).stem}.png", format="png", dpi=220, bbox_inches="tight", facecolor="#0c111b")
    plt.close()

# Source defects surviving perfect extraction.
sim=json.loads((RESULTS/"simulator-quality-mix-10000.json").read_text())
tiers=["50","75","100"]
latent=[100*sim["quality_tier_breakdown"][t]["ratio_accuracy_latent"] for t in tiers]
fig,ax=plt.subplots(figsize=(8.8,4.5))
bars=ax.bar(["50% source exactness","75% source exactness","100% source exactness"],latent,color=[COLORS["red"],COLORS["amber"],COLORS["qwen"]],width=.58)
ax.set_ylim(0,112); ax.set_ylabel("Ratios matching clean latent values (%)")
ax.set_title("When inputs are wrong, deterministic ratios inherit the error",loc="left",weight="bold",pad=16)
ax.text(0,1.02,"10,000 synthetic records · exact field extraction from what the statements displayed",transform=ax.transAxes,color="#9aafc4")
ax.grid(axis="y",alpha=.65); ax.set_axisbelow(True)
for b,v in zip(bars,latent): ax.text(b.get_x()+b.get_width()/2,v+2,f"{v:.1f}%",ha="center",weight="bold")
finish("source-quality-to-ratios.svg")

# Same matched 24-record screen: 8 records in each tier.
rows=list(csv.DictReader((RESULTS/"quality_sensitivity.csv").open(encoding="utf-8",newline="")))
models=[("DeepSeek V4.1 Flash (OpenCode, free)","opencode/deepseek-v4.1-flash-free",COLORS["deepseek"]),("MiniMax M3.1 Flash (OpenRouter, free)","openrouter/minimax/minimax-m3.1-flash:free",COLORS["minimax"]),("Qwen 3.5 9B (Ollama, local)","ollama/qwen3.5-9b-16k:latest",COLORS["qwen"])]
fig,axs=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
for ax,key,title in [(axs[0],"field_accuracy_source","Extraction match to displayed statement"),(axs[1],"ratio_accuracy_latent","Ratio match to clean latent statement")]:
    x=list(range(3)); width=.23
    for i,(label,model,color) in enumerate(models):
        vals=[100*float(next(r[key] for r in rows if r["model"]==model and r["quality_tier"]==tier)) for tier in tiers]
        ax.bar([p+(i-1)*width for p in x],vals,width,label=label,color=color)
        if key=="ratio_accuracy_latent":
            for p,v in zip(x,vals): ax.text(p+(i-1)*width,v+2,f"{v:.0f}",ha="center",fontsize=8)
    ax.set_xticks(x,["50%","75%","100%"]); ax.set_title(title,loc="left",weight="bold")
    ax.set_xlabel("Predefined source exactness tier"); ax.set_ylim(0,116); ax.grid(axis="y",alpha=.5); ax.set_axisbelow(True)
axs[0].set_ylabel("Exact agreement (%)")
axs[1].legend(frameon=False,loc="lower right",fontsize=8)
fig.suptitle("Matched 24-record pilot · 8 records per source-quality tier",x=.06,ha="left",weight="bold",fontsize=14)
finish("matched-model-quality-pilot.svg")

# Scale characteristics from the ordinary deterministic record-count prefixes.
# The separate quality-mix 10k cohort has more parsing/layout work and is not
# substituted into this scale series.
sizes=[100,1000,10000,100000,1000000]
scale={n:json.loads((RESULTS/f"simulator-{n}.json").read_text()) for n in sizes}
xs=sorted(scale)
fig,ax=plt.subplots(figsize=(8.8,4.5))
ax.plot(xs,[float(scale[x]["records_per_second"]) for x in xs],marker="o",lw=2.5,color=COLORS["deepseek"])
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("Records processed (log scale)"); ax.set_ylabel("Records per second (log scale)")
ax.set_title("The deterministic path scales; this is not an LLM throughput claim",loc="left",weight="bold",pad=14)
ax.grid(True,which="both",alpha=.55)
for x in xs:
    y=float(scale[x]["records_per_second"]); ax.annotate(f"{x:,}\n{y:,.0f}/s",(x,y),xytext=(5,9),textcoords="offset points",fontsize=8,color="#d9e6f2")
finish("simulator-scale.svg")

# Provider success versus usable schema output for the same full cohort.
labels=["GPT-OSS 20B\n(OpenRouter batch)","Ministral 8B\n(OpenRouter batch)"]
provider=[100,100]; truncated=[100,94.62]
fig,ax=plt.subplots(figsize=(8.8,4.5)); x=list(range(2)); w=.24
ax.bar([p-w for p in x],provider,w,label="Provider requests completed",color=COLORS["qwen"])
ax.bar(x,[0,0],w,label="Schema-complete extractions",color=COLORS["deepseek"])
ax.bar([p+w for p in x],truncated,w,label="Responses hit output cap",color=COLORS["red"])
ax.set_xticks(x,labels); ax.set_ylim(0,115); ax.set_ylabel("Share of 10,000 requests (%)")
ax.set_title("Provider completion did not mean usable extraction",loc="left",weight="bold",pad=14)
ax.grid(axis="y",alpha=.55); ax.set_axisbelow(True); ax.legend(frameon=False,loc="lower right")
for p,v in zip([p-w for p in x],provider): ax.text(p,v+2,f"{v:.0f}%",ha="center",fontsize=9)
for p,v in zip([p+w for p in x],truncated): ax.text(p,v+2,f"{v:g}%",ha="center",fontsize=9)
ax.text(.5,.72,"0 schema-complete records for both models",transform=ax.transAxes,ha="center",va="center",color="#d9e6f2",weight="bold")
finish("batch-output-integrity.svg")
print(f"Wrote article figures to {OUT}")
