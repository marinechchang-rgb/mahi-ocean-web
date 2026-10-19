"""Check dated public data before publication."""
from pathlib import Path
import json, math
p=Path(__file__).resolve().parents[1]/'docs'/'data'
idx=json.loads((p/'index.json').read_text(encoding='utf-8'))
assert len(idx['dates'])>0
count=0
for entry in idx['dates']:
    d=json.loads((p/entry['file']).read_text(encoding='utf-8'))
    assert d['date']==entry['date']
    for s in d['sources'].values():
        assert s['date']==d['date'] and s['url'].startswith('https://www.data.jma.go.jp/') and len(s['sha256'])==64
    for name,g in d['layers'].items():
        assert len(g['lat'])==len(g['values'])
        assert all(len(r)==len(g['lon']) for r in g['values'])
        values=[v for r in g['values'] for v in r if v is not None]
        assert values and all(math.isfinite(v) for v in values)
        if name in ('psat','cpue','legacy'): assert all(0<=v<=1 for v in values)
        count+=1
assert (p/'land.json').is_file()
print(f'Validated {len(idx["dates"])} dates, {count} layers, source dates and HSI bounds.')
