import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
files=sorted((root/'results').glob('*.json'))
data=[json.loads(p.read_text()) for p in files]
data=[r for r in data if 'records' in r and 'field_accuracy' in r and r.get('status') in {'completed','completed with provider errors','stopped at provider rate limit','simulated extraction'} and not r.get('exclude_from_dashboard')]
if not data: raise SystemExit('No result files found')
colors=['#1f77b4','#ff7f0e','#2ca02c','#9467bd','#d62728']
w,h=1000,620; left,right,top,bottom=100,60,70,100
plotw=w-left-right; ploth=h-top-bottom
groups={}
for r in data: groups.setdefault(r['model'],[]).append(r)
series=[]
for idx,(model,rows) in enumerate(groups.items()):
    rows.sort(key=lambda x:x['records']); series.append((model,rows,colors[idx%len(colors)]))
def y(v): return top+ploth*(1-v)
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">','<rect width="100%" height="100%" fill="white"/>','<style>text{font-family:Arial,sans-serif;fill:#223} .small{font-size:13px} .axis{stroke:#667;stroke-width:1}</style>']
svg.append('<text x="500" y="32" text-anchor="middle" font-size="21" font-weight="bold">Credit Memo Benchmark V1: Measure Results</text>')
for tick in range(0,101,20):
    yy=y(tick/100); svg.append(f'<line x1="{left}" y1="{yy}" x2="{w-right}" y2="{yy}" stroke="#ddd"/>'); svg.append(f'<text x="{left-12}" y="{yy+5}" text-anchor="end" class="small">{tick}%</text>')
svg += [f'<line x1="{left}" y1="{top}" x2="{left}" y2="{h-bottom}" class="axis"/>',f'<line x1="{left}" y1="{h-bottom}" x2="{w-right}" y2="{h-bottom}" class="axis"/>']
svg.append(f'<text transform="translate(25 {top+ploth/2}) rotate(-90)" text-anchor="middle" font-size="14">Field extraction accuracy</text>')
max_n=max(r['records'] for r in data)
for n in sorted(set(r['records'] for r in data)):
    xx=left+plotw*n/max_n; svg.append(f'<line x1="{xx}" y1="{h-bottom}" x2="{xx}" y2="{h-bottom+5}" class="axis"/>'); svg.append(f'<text x="{xx}" y="{h-bottom+24}" text-anchor="middle" class="small">{n:,}</text>')
svg.append(f'<text x="{left+plotw/2}" y="{h-25}" text-anchor="middle" font-size="14">Records</text>')
for idx,(model,rows,color) in enumerate(series):
    points=[]
    for r in rows:
        xx=left+plotw*r['records']/max_n; yy=y(r['field_accuracy']); points.append(f'{xx},{yy}')
        svg.append(f'<circle cx="{xx}" cy="{yy}" r="6" fill="{color}"/>')
    if len(points)>1: svg.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')
    ly=top+idx*25; svg.append(f'<line x1="{left+20}" y1="{ly}" x2="{left+42}" y2="{ly}" stroke="{color}" stroke-width="4"/>'); svg.append(f'<text x="{left+50}" y="{ly+5}" class="small">{model}</text>')
svg.append('</svg>')
(root/'results'/'accuracy_plot.svg').write_text('\n'.join(svg),encoding='utf8')
with (root/'results'/'summary.csv').open('w',encoding='utf8') as f:
    f.write('records,model,field_accuracy,record_exact_accuracy,ratio_accuracy,metadata_accuracy,elapsed_seconds,records_per_second,prompt_tokens,completion_tokens,total_tokens,token_usage_available,inference_cost_usd,tieout_failures,control_failures,failed_calls,schema_failures\n')
    for r in sorted(data,key=lambda a:(a['model'],a['records'])):
        f.write(','.join(str(r.get(k,'')) for k in ('records','model','field_accuracy','record_exact_accuracy','ratio_accuracy','metadata_accuracy','elapsed_seconds','records_per_second','prompt_tokens','completion_tokens','total_tokens','token_usage_available','inference_cost_usd','tieout_failures','control_failures','failed_calls','schema_failures'))+'\n')
print(f'Plotted {len(data)} results to results/accuracy_plot.svg and results/summary.csv')
