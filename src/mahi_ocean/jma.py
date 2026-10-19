"""JMA ocean product discovery and fixed-width parsers.

This module intentionally has no GUI or plotting dependencies so it can be
shared by the desktop app, static web exporter, scheduled jobs, and tests.
"""

from __future__ import annotations

import datetime as dt
import gzip
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import numpy as np

PROJECT_ROOT = Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"

PRODUCTS = {
    "sst": {
        "name": "HIMSST 海面水溫",
        "base_url": "https://www.data.jma.go.jp/goos/data/pub/JMA-product/him_sst_pac_D/",
        "folder_name": "him_sst_pac_D",
    },
    "subt": {
        "name": "NPRSUBT 次表層水溫",
        "base_url": "https://www.data.jma.go.jp/goos/data/pub/JMA-product/npr_subt_jpn_D/",
        "folder_name": "npr_subt_jpn_D",
    },
    "subc": {
        "name": "NPRSUBC 表面海流",
        "base_url": "https://www.data.jma.go.jp/goos/data/pub/JMA-product/npr_subc_jpn_D/",
        "folder_name": "npr_subc_jpn_D",
    },
}

DEFAULT_EXTENT = [115.0, 125.0, 20.0, 30.0]
STALE_DATA_DAYS = 14


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)


@dataclass(frozen=True)
class GridData:
    date: dt.date
    lons: np.ndarray
    lats: np.ndarray
    values: np.ndarray
    label: str
    unit: str


@dataclass(frozen=True)
class SubsurfaceData:
    date: dt.date
    lons: np.ndarray
    lats: np.ndarray
    depth_values: dict[int, np.ndarray]


@dataclass(frozen=True)
class CurrentData:
    date: dt.date
    lons: np.ndarray
    lats: np.ndarray
    u: np.ndarray
    v: np.ndarray


def product_folder(product_key: str, root: Path | None = None) -> Path:
    product = PRODUCTS[product_key]
    return (root or DATA_ROOT) / str(product["folder_name"])


def parse_links(html: str) -> list[str]:
    parser = LinkParser()
    parser.feed(html)
    return parser.links


def date_from_text(text: str) -> dt.date | None:
    match = re.search(r"(20\d{6})", text)
    if not match:
        return None
    try:
        return dt.datetime.strptime(match.group(1), "%Y%m%d").date()
    except ValueError:
        return None


def get_text(url: str, timeout: int = 30) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 JMA ocean viewer"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def discover_latest_files(base_url: str, limit: int = 10) -> list[str]:
    from urllib.parse import urlparse
    candidates = {}
    seen = set()
    def scan(url, depth=0):
        if url in seen: return
        seen.add(url)
        links = parse_links(get_text(url))
        folders = []
        for link in links:
            absolute = urljoin(url, link)
            parsed = urlparse(absolute)
            if not absolute.startswith(base_url) or parsed.query or parsed.fragment: continue
            name = parsed.path.rstrip('/').rsplit('/',1)[-1]
            if parsed.path.endswith('/'):
                if depth<2 and re.fullmatch(r'20\d{2}|\d{2}|20\d{4}',name): folders.append(absolute)
            elif not name.lower().startswith('readme'):
                day = date_from_text(name)
                if day and (day not in candidates or name.startswith('re_')):
                    candidates[day] = absolute
        for folder in sorted(set(folders),reverse=True):
            scan(folder,depth+1)
            if len(candidates)>=limit: break
    scan(base_url)
    return [candidates[d] for d in sorted(candidates,reverse=True)[:limit]]


def validate_file(product_key, path, expected_date=None):
    parsed = {'sst':parse_sst,'subt':parse_subt,'subc':parse_subc}[product_key](path)
    if expected_date and parsed.date != expected_date: raise ValueError('Header date differs from filename')
    arrays = [parsed.values] if product_key=='sst' else list(parsed.depth_values.values()) if product_key=='subt' else [parsed.u,parsed.v]
    for a in arrays:
        valid=a[np.isfinite(a)]
        if not valid.size: raise ValueError('All values missing')
        low,high=(-5,45) if product_key!='subc' else (-10,10)
        if valid.min()<low or valid.max()>high: raise ValueError('Physical range QC failed')
    return parsed


def download_latest(product_key: str, status_callback=None, root: Path | None = None) -> list[Path]:
    import hashlib, json, logging, time
    product=PRODUCTS[product_key]; folder=product_folder(product_key,root)
    folder.mkdir(parents=True,exist_ok=True)
    def retry(operation):
        for attempt in range(3):
            try: return operation()
            except Exception:
                if attempt==2: raise
                time.sleep(.5*(attempt+1))
    try: urls=retry(lambda:discover_latest_files(str(product['base_url']),10))
    except Exception as exc:
        logging.exception('JMA discovery failed: %s',product_key)
        if status_callback: status_callback(f'{product_key} discovery failed; offline cache: {exc}')
        return local_product_files(product_key,root)
    paths=[]
    for index,url in enumerate(urls,1):
        target=folder/url.rsplit('/',1)[-1]; temp=target.with_name(target.name+'.part')
        day=date_from_text(target.name)
        try:
            cached=False
            if target.exists():
                try: validate_file(product_key,target,day); cached=True
                except (ValueError,UnicodeError,OSError): pass
            if not cached:
                def fetch():
                    with urlopen(Request(url,headers={'User-Agent':'Mahi-research/2.0'}),timeout=40) as response, temp.open('wb') as handle:
                        while chunk:=response.read(262144): handle.write(chunk)
                    validate_file(product_key,temp,day)
                retry(fetch)
                temp.replace(target)
            meta=target.with_name(target.name+'.json')
            if not cached or not meta.exists():
                record=dict(date=day.isoformat(),dataset=product['folder_name'],url=url,filename=target.name,
                    origin_kind='reanalysis' if target.name.startswith('re_') else 'analysis',
                    retrieved_utc=None if cached else dt.datetime.now(dt.timezone.utc).isoformat(),
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest(),parser_version='2.0.0',qc_status='passed',
                    note='Pre-existing cache: retrieval time unknown' if cached else 'live download')
                part=meta.with_name(meta.name+'.part'); part.write_text(json.dumps(record,indent=2),encoding='utf-8'); part.replace(meta)
            paths.append(target)
            if status_callback: status_callback(f"{product_key}: {index}/{len(urls)} {target.name} QC passed")
        except Exception as exc:
            logging.exception('JMA download/QC failed: %s',url)
            if status_callback: status_callback(f'{product_key} failed; preserving cache: {exc}')
        finally:
            temp.unlink(missing_ok=True)
    return paths or local_product_files(product_key,root)


def local_product_files(product_key: str, root: Path | None = None) -> list[Path]:
    folder=product_folder(product_key,root)
    if not folder.exists(): return []
    by_date={}
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix in {'.tmp','.part','.json'}: continue
        day=date_from_text(path.name)
        if day and (day not in by_date or path.name.startswith('re_')): by_date[day]=path
    return [by_date[d] for d in sorted(by_date,reverse=True)]


def latest_local_date(product_key: str, root: Path | None = None) -> dt.date | None:
    for path in local_product_files(product_key, root):
        file_date = date_from_text(path.name)
        if file_date:
            return file_date
    return None


def local_data_status(
    today: dt.date | None = None,
    root: Path | None = None,
) -> tuple[dict[str, dt.date | None], str, bool]:
    today = today or dt.date.today()
    dates = {key: latest_local_date(key, root) for key in PRODUCTS}
    available = [value for value in dates.values() if value]
    if not available:
        return dates, "尚無可用本機資料", True

    oldest_latest = min(available)
    age_days = (today - oldest_latest).days
    if len(available) < len(PRODUCTS):
        return dates, "部分資料缺漏，請重新下載最新資料", True
    if age_days > STALE_DATA_DAYS:
        return dates, f"資料可能過期：最新共同資料約 {age_days} 天前", True
    return dates, f"資料日期正常：最新共同資料約 {age_days} 天前", False


def parse_header_date(line: str) -> dt.date:
    if re.fullmatch(r"[ 0-9]{12}", line[:12]) and len(line) >= 12:
        return dt.date(int(line[:4]), int(line[4:8]), int(line[8:12]))
    digits = re.findall(r"\d+", line)
    if len(digits) >= 3:
        year, month, day = (int(digits[0]), int(digits[1]), int(digits[2]))
        return dt.date(year, month, day)
    joined = "".join(digits)
    if len(joined) >= 8:
        return dt.datetime.strptime(joined[:8], "%Y%m%d").date()
    raise ValueError(f"無法解析日期標頭：{line[:40]}")


def parse_fixed_width_row(line: str, width: int, count: int) -> np.ndarray:
    compact = line.rstrip("\r\n")
    if len(compact) != width * count:
        raise ValueError(f"Invalid record width: {len(compact)} expected {width * count}")
    values = [int(compact[i : i + width]) for i in range(0, width * count, width)]
    return np.asarray(values, dtype=float)


def read_lines(path: Path) -> list[str]:
    raw=Path(path).read_bytes()
    if raw[:2]==b'\x1f\x8b': raw=gzip.decompress(raw)
    return raw.decode('ascii',errors='strict').splitlines()


def parse_sst(path: Path) -> GridData:
    lines = read_lines(path)
    if len(lines) != 601: raise ValueError("Expected 601 records")
    date = parse_header_date(lines[0])
    rows = [parse_fixed_width_row(line, 3, 800) for line in lines[1:601]]
    data = np.vstack(rows)
    data[np.isin(data, [888, 999])] = np.nan
    data = data / 10.0
    lats = 59.95 - np.arange(600) * 0.1
    lons = 100.05 + np.arange(800) * 0.1
    return GridData(date, lons, lats, data, "SST", "degC")


def parse_subt(path: Path) -> SubsurfaceData:
    lines = read_lines(path)
    if len(lines) != 1585: raise ValueError("Expected 1585 records")
    date = parse_header_date(lines[0])
    lats = 56.2 - np.arange(395) * 0.1
    lons = 113.545455 + np.arange(550) / 11.0
    depths = [50, 100, 200, 400]
    depth_values: dict[int, np.ndarray] = {}
    for block_index, depth in enumerate(depths):
        start = 1 + block_index * 396
        if not lines[start].strip().isdigit() or int(lines[start]) != depth: raise ValueError("Invalid depth marker")
        rows = [parse_fixed_width_row(line, 4, 550) for line in lines[start + 1 : start + 396]]
        data = np.vstack(rows)
        data[data == 9999] = np.nan
        depth_values[depth] = data / 100.0
    return SubsurfaceData(date, lons, lats, depth_values)


def parse_subc(path: Path) -> CurrentData:
    lines = read_lines(path)
    if len(lines) != 795: raise ValueError("Expected 795 records")
    date = parse_header_date(lines[0])
    lats = 56.25 - np.arange(396) * 0.1
    lons = 113.5 + np.arange(551) / 11.0
    components = []
    for start, marker in [(1,"Eastward_Component"),(398,"Northward_Component")]:
        if lines[start].strip() != marker: raise ValueError("Invalid component marker")
        rows = [parse_fixed_width_row(line, 4, 551) for line in lines[start + 1 : start + 397]]
        data = np.vstack(rows)
        data[data == 9999] = np.nan
        components.append(data / 100.0)
    return CurrentData(date, lons, lats, components[0], components[1])


def nearest_file_for_date(product_key: str, selected: dt.date, root: Path | None = None) -> Path | None:
    files = local_product_files(product_key, root)
    dated = [(date_from_text(path.name), path) for path in files]
    dated = [(date, path) for date, path in dated if date]
    if not dated:
        return None
    exact = [path for date, path in dated if date == selected]
    if exact:
        return exact[0]
    return min(dated, key=lambda item: abs((item[0] - selected).days))[1]

