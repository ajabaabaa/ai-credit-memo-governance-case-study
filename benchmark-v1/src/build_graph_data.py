import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
rows=[]
for path in sorted((root/'results').glob('*.json')):
    try: row=json.loads(path.read_text(encoding='utf8'))
    except (json.JSONDecodeError,UnicodeDecodeError): continue
    if 'records' in row and 'field_accuracy' in row and row.get('status') in {'completed', 'completed with provider errors', 'stopped at provider rate limit', 'simulated extraction'} and not row.get('exclude_from_dashboard'):
        row['result_file']=path.name
        rows.append(row)
target=root/'dashboard'/'data.js'
target.parent.mkdir(exist_ok=True)
target.write_text('window.BENCHMARK_RESULTS = '+json.dumps(rows,separators=(',',':'))+';\n',encoding='utf8')
print(f'Wrote {len(rows)} completed measurements to {target.relative_to(root)}')
