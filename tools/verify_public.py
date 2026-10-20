"""Read-only check of public deployment. No credentials are read."""
import json,sys,hashlib
from pathlib import Path
from urllib.request import Request,urlopen
BASE='https://marinechchang-rgb.github.io/mahi-ocean-web/'
def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'mahi-deployment-validation'}),timeout=30) as r:
        return r.read()
html=fetch(BASE).decode('utf-8')
assert '農業部水產試驗所 鬼頭刀漁海況研究小組' in html
assert 'assets/tfrin-logo.png' in html and 'export.js' in html
logo=fetch(BASE+'assets/tfrin-logo.png')
assert logo[:8]==b'\x89PNG\r\n\x1a\n'
index=json.loads(fetch(BASE+'data/index.json'))
runs=json.loads(fetch('https://api.github.com/repos/marinechchang-rgb/mahi-ocean-web/actions/runs?per_page=5'))['workflow_runs']
report={'site':BASE,'latest_date':index['dates'][0]['date'],'dates':len(index['dates']),
        'institution':True,'logo_sha256':hashlib.sha256(logo).hexdigest(),
        'runs':[{k:r[k] for k in ('id','name','status','conclusion','head_sha','html_url')} for r in runs]}
if len(sys.argv)>1:
    Path(sys.argv[1]).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
