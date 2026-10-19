"""Build public, dated web products with the desktop's validated core."""
from pathlib import Path
import sys, json, datetime as dt, argparse, hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mahi_ocean import jma
from mahi_ocean.fields import GridField
from mahi_ocean.models import evaluate

def grid(a,lat,lon,step=1):
    yi=np.where((lat>=20)&(lat<=30))[0][::step]
    xi=np.where((lon>=115)&(lon<=125))[0][::step]
    v=a[np.ix_(yi,xi)]
    return dict(lat=lat[yi].tolist(),lon=lon[xi].tolist(),values=[[None if not np.isfinite(x) else round(float(x),3) for x in r] for r in v])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--raw-root',type=Path,default=ROOT/'raw'); ap.add_argument('--download',action='store_true'); args=ap.parse_args()
    if args.download:
        for key in jma.PRODUCTS: jma.download_latest(key,root=args.raw_root)
    dest=ROOT/'docs'/'data'; dest.mkdir(parents=True,exist_ok=True)
    files={k:{} for k in jma.PRODUCTS}
    for k in files:
        for p in jma.local_product_files(k,args.raw_root):
            d=jma.date_from_text(p.name)
            if d and d not in files[k]: files[k][d]=p
    dates=sorted(set().union(*(set(v) for v in files.values())),reverse=True)[:10]
    if not dates: raise RuntimeError('No real JMA data')
    index=dict(generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),dates=[],extent=[115,125,20,30],model_version='2.0.0')
    for day in dates:
        product=dict(date=day.isoformat(),layers={},sources={})
        for k in files:
            p=files[k].get(day)
            if p is None: continue
            jma.validate_file(k,p,day)
            product['sources'][k]=dict(date=day.isoformat(),filename=p.name,url=jma.PRODUCTS[k]['base_url']+p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            data=getattr(jma,'parse_'+k)(p)
            if k=='sst':
                product['layers']['sst']=dict(**grid(data.values,data.lats,data.lons),unit='°C')
                f=GridField(data.values,data.lats,data.lons,day,'degC','JMA HIMSST','sst',p.name)
                for name,profile in [('psat','psat_residence_literature'),('cpue','catch_cpue_literature')]:
                    result=evaluate({'sst':f},profile)
                    product['layers'][name]=dict(**grid(result.values,data.lats,data.lons),unit='0–1',model=result.metadata)
            elif k=='subt':
                for depth,a in data.depth_values.items(): product['layers'][str(depth)]=dict(**grid(a,data.lats,data.lons),unit='°C')
                f=GridField(data.depth_values[100],data.lats,data.lons,day,'degC','JMA NPRSUBT','t100',p.name,depth=100)
                result=evaluate({'t100':f},'legacy_t100_exploratory')
                product['layers']['legacy']=dict(**grid(result.values,data.lats,data.lons),unit='0–1',model=result.metadata)
            else:
                product['current']=dict(u=grid(data.u,data.lats,data.lons,5),v=grid(data.v,data.lats,data.lons,5),unit='m/s',date=day.isoformat())
        name=day.isoformat()+'.json'
        (dest/name).write_text(json.dumps(product,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8')
        index['dates'].append(dict(date=day.isoformat(),file=name,layers=list(product['layers']),current='current' in product))
    (dest/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'dates':len(dates),'latest':dates[0].isoformat(),'output':str(dest)}))
if __name__=='__main__': main()
