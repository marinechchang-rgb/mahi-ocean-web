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
    # Independent numerical check of exported proxy against exported temperature.
    for key,base,lo,hi in [('psat','sst',25.,27.),('cpue','sst',26.,28.),('legacy','100',17.8,23.1)]:
        if key not in d['layers']: continue
        g,t=d['layers'][key],d['layers'][base]
        assert g['lat']==t['lat'] and g['lon']==t['lon']
        for gr,tr in zip(g['values'],t['values']):
            for v,temp in zip(gr,tr):
                if temp is None: assert v is None
                else:
                    expected=max(0,min(1,temp-(lo-1),(hi+1)-temp))
                    assert v is not None and abs(v-expected)<=.0011
assert (p/'land.json').is_file()
print(f'Validated {len(idx["dates"])} dates, {count} layers, source dates and HSI bounds.')
