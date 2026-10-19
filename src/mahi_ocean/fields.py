"""Dated, traceable regular grids. Missing cells remain missing."""
from dataclasses import dataclass, field
import datetime as dt
import numpy as np


@dataclass
class GridField:
    values: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    date: dt.date
    unit: str
    source: str
    variable: str
    filename: str = ''
    depth: float | None = None
    qc: str = 'passed'
    mld_definition: str | None = None
    reference_time: str | None = None
    composite_window: tuple[str, str] | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.values = np.array(self.values, dtype=float, copy=True)
        self.lat, self.lon = np.asarray(self.lat), np.asarray(self.lon)
        if self.values.shape != (len(self.lat), len(self.lon)):
            raise ValueError('GridField shape mismatch')
        for axis in (self.lat, self.lon):
            if not len(axis) or not np.all(np.isfinite(axis)):
                raise ValueError('Empty/nonfinite coordinates')
            if len(axis)>1 and not (np.all(np.diff(axis)>0) or np.all(np.diff(axis)<0)):
                raise ValueError('Coordinates must be strictly monotonic')
        self.values[~np.isfinite(self.values)] = np.nan

    @property
    def mask(self):
        return ~np.isfinite(self.values)

    def provenance(self):
        return dict(variable=self.variable, date=self.date.isoformat(), unit=self.unit,
                    source=self.source, filename=self.filename, depth=self.depth, qc=self.qc,
                    reference_time=self.reference_time, composite_window=self.composite_window,
                    mld_definition=self.mld_definition, **self.metadata)


def regrid(source, lat, lon):
    """Bilinear interpolation requires all four corners; never bridge a masked cell."""
    from scipy.interpolate import RegularGridInterpolator
    y, x, a = source.lat, source.lon, source.values
    if y[0]>y[-1]: y,a = y[::-1],a[::-1,:]
    if x[0]>x[-1]: x,a = x[::-1],a[:,::-1]
    if len(y)<2 or len(x)<2: raise ValueError('Regrid requires at least 2x2 coordinates')
    yy,xx=np.meshgrid(lat,lon,indexing='ij')
    loc=np.column_stack([yy.ravel(),xx.ravel()])
    # NaNs propagate even from a zero-weight corner, conservatively preserving coast masks.
    result=RegularGridInterpolator((y,x),a,bounds_error=False,fill_value=np.nan)(loc)
    return result.reshape(len(lat),len(lon))
