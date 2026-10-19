"""Uncalibrated exploratory proxies. No GAM coefficients are invented."""
from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np
from .fields import GridField, regrid

VERSION = '2.0.0'
PROFILES = {
    'psat_residence_literature': {'sst':(25.,27.),'transition':(24.,28.),'sss':34.25,'mld':(23.,53.)},
    'catch_cpue_literature': {'sst':(26.,28.),'transition':(25.,29.),'sss':(34.2,34.4),'mld':(20.,40.)},
    'legacy_t100_exploratory': {'t100':(17.8,23.1),'transition':(16.8,24.1)},
}
LIMITATION = '探索性相對適合度 0–1，非原 GAM、捕獲機率、魚群實際位置或漁獲保證。'


@dataclass
class ModelResult:
    values: np.ndarray
    metadata: dict


def plateau(a, low, high, outer_low, outer_high):
    if not outer_low<low<=high<outer_high: raise ValueError('Invalid transition')
    return np.minimum(np.clip((a-outer_low)/(low-outer_low),0,1),
                      np.clip((outer_high-a)/(outer_high-high),0,1))


def evaluate(fields, profile='psat_residence_literature', *, max_lag_days=0,
             transitions=None, weights=None, avoidance_factor=.25):
    p=PROFILES[profile]
    base_name='t100' if profile=='legacy_t100_exploratory' else 'sst'
    if base_name not in fields: raise ValueError(f'{base_name} required')
    base=fields[base_name]
    names=[base_name] if base_name=='t100' else [v for v in ('sst','sss','mld') if v in fields]
    if not 0<=avoidance_factor<=1 or max_lag_days<0: raise ValueError('Invalid model configuration')
    scores={}; provenance={}
    for name in names:
        f=fields[name]
        if abs((f.date-base.date).days)>max_lag_days: raise ValueError(f'{name} date lag exceeds policy')
        if f.composite_window and f.composite_window[0][:10]!=f.composite_window[1][:10]:
            raise ValueError(f'{name} composite window incompatible with daily model')
        expected={'sst':'degC','t100':'degC','sss':'PSU','mld':'m'}[name]
        if f.unit!=expected: raise ValueError(f'{name} units require {expected}')
        if f.qc!='passed': raise ValueError(f'{name} QC not passed')
        if name=='mld' and f.mld_definition!='temperature_delta_0.2C':
            raise ValueError('MLD definition incompatible: requires temperature_delta_0.2C')
        a=f.values if np.array_equal(f.lat,base.lat) and np.array_equal(f.lon,base.lon) else regrid(f,base.lat,base.lon)
        if name==base_name:
            scores[name]=plateau(a,*p[name],*(transitions or p['transition']))
        elif name=='sss':
            scores[name]=np.where(a<34.25,1.,0.) if profile=='psat_residence_literature' else np.where((a>=34.2)&(a<=34.4),1.,0.)
        else:
            lo,hi=p['mld']
            scores[name]=np.where((a>=lo)&(a<=hi),avoidance_factor,1.) if profile=='psat_residence_literature' else np.where((a>=lo)&(a<=hi),1.,0.)
        scores[name][~np.isfinite(a)]=np.nan
        provenance[name]={**f.provenance(),'lag_days':(f.date-base.date).days}
    weights=weights or {n:1. for n in names}
    if set(weights)-set(names) or any(not np.isfinite(w) or w<0 for w in weights.values()):
        raise ValueError('Invalid/unsupported model weights')
    active={n:weights.get(n,1.) for n in names if weights.get(n,1.)>0}
    if not active or base_name not in active: raise ValueError('Base factor must have positive weight')
    # Outside the PSAT MLD avoidance interval is neutral. Do not award extra
    # suitability by averaging a value of 1 into the other environmental scores.
    averaged={n:w for n,w in active.items() if not (profile=='psat_residence_literature' and n=='mld')}
    result=sum(scores[n]*w for n,w in averaged.items())/sum(averaged.values())
    aggregation='weighted arithmetic mean (engineering assumption)'
    if profile=='psat_residence_literature' and 'mld' in active:
        result*=scores['mld']**active['mld']
        aggregation+='; multiplied by MLD avoidance factor**weight; outside interval neutral'
    result[base.mask]=np.nan
    return ModelResult(result,dict(model_id='exploratory_threshold_proxy',profile=profile,version=VERSION,
        mode='SST-only proxy' if names==['sst'] else 'exploratory multi-factor proxy' if len(names)>1 else 'legacy T100 proxy',
        parameters=p, transitions=list(transitions or p['transition']), weights=active, avoidance_factor=avoidance_factor,
        aggregation=aggregation,layers=provenance,
        missing=[n for n in ('sss','mld') if n not in fields] if base_name=='sst' else [],
        limitations=[LIMITATION,'MLD outside avoidance interval is neutral, not evidence of preference.',
                     'Thresholds checked against supplied abstract/114 slides; full 2026 paper and original GAM not imported.']))


def load_gam_bundle(path):
    """Read a declarative mgcv interchange manifest, never execute an R/pickle payload."""
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    required={'coefficients','smooth_basis','factor_definitions','training_data_version','model_version','response','link'}
    if not required<=data.keys(): raise ValueError(f'GAM bundle missing {sorted(required-data.keys())}')
    return data


def predict_gam(bundle, fields):
    raise NotImplementedError('mgcv basis evaluator must be validated against original R predictions before use')
