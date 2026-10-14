"""Search directories of public security identities, never prices or advice."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from threading import RLock

import requests

from quant_lab.market_data import normalize_symbol
from quant_lab.paths import user_data_dir
from quant_lab.refresh import RefreshCache


PROFILE_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
CNINFO_URL = "https://www.cninfo.com.cn/new/data/szse_stock.json"
POPULAR = {
    "A 股": ("600519", "000001", "600036", "601318", "300750", "000858", "000333", "002594", "600900", "601398", "601857", "688981"),
    "港股": ("00700", "09988", "03690", "00941", "00005", "00939", "01211", "01810", "02318", "00388", "00981", "09618"),
}


@dataclass(frozen=True)
class Directory:
    market: str
    rows: tuple[tuple[str, str], ...]
    source: str
    received_at: str
    error: str | None = None


def validate_directory(data: dict, market: str) -> Directory:
    if data["market"] != market:
        raise ValueError("证券目录市场不匹配。")
    received = datetime.fromisoformat(data["received_at"])
    if received.tzinfo is None or not data["source"]:
        raise ValueError("证券目录缺少来源或时区。")
    rows = {}
    for code, name in data["rows"]:
        symbol = normalize_symbol(market, code)
        if not isinstance(name, str) or not name.strip() or name.strip() in {"-", "null", "nan"}:
            raise ValueError("证券目录名称无效。")
        if symbol in rows and rows[symbol] != name.strip():
            raise ValueError("证券目录代码重复且名称冲突。")
        rows[symbol] = name.strip()
    if not rows:
        raise ValueError("证券目录为空。")
    priority = {code: i for i, code in enumerate(POPULAR[market])}
    ordered = tuple(sorted(rows.items(), key=lambda r: (priority.get(r[0], 100), r[0])))
    return Directory(market, ordered, data["source"], data["received_at"])


def fetch_directory(market: str) -> Directory:
    normalize_symbol(market, POPULAR[market][0])
    if market == "A 股":
        with requests.get(CNINFO_URL, timeout=(3, 10)) as response:
            response.raise_for_status()
            rows = [(row["code"], row["zwjc"]) for row in response.json()["stockList"]
                    if row.get("category") == "A股"]
        source = "巨潮资讯公开证券基础目录"
    else:
        rows = []
        pages, page = 1, 1
        while page <= pages:
            with requests.get(PROFILE_URL, params={
                "reportName": "RPT_HKF10_INFO_SECURITYINFO",
                "columns": "SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,SECURITY_TYPE",
                "pageSize": "500", "pageNumber": str(page),
                "sortColumns": "SECUCODE", "sortTypes": "1",
            }, timeout=(3, 10)) as response:
                response.raise_for_status()
                result = response.json()["result"]
            pages = int(result["pages"])
            if not 1 <= pages <= 20 or not result["data"]:
                raise ValueError("港股证券目录分页异常。")
            for row in result["data"]:
                if row.get("SECURITY_TYPE") in {"H股", "非H股", "红筹股"} and re.fullmatch(r"\d{5}\.HK", row.get("SECUCODE", "")):
                    code = normalize_symbol(market, row["SECUCODE"])
                    if code != normalize_symbol(market, row["SECURITY_CODE"]):
                        raise ValueError("港股证券目录代码不匹配。")
                    rows.append((code, row["SECURITY_NAME_ABBR"]))
            page += 1
        source = "东方财富公开港股证券资料（H股/非H股/红筹股）"
    return validate_directory({"market": market, "rows": rows, "source": source,
        "received_at": datetime.now(timezone.utc).isoformat()}, market)


def directory_data(directory: Directory) -> dict:
    return {"market": directory.market, "rows": directory.rows,
            "source": directory.source, "received_at": directory.received_at}


_cache = RefreshCache(86400, 8)
_file_lock = RLock()


def _read_directory(market: str) -> Directory:
    filename = "a_shares.json" if market == "A 股" else "hk_shares.json"
    candidates = (user_data_dir() / "securities" / filename,
                  Path(__file__).parent / "resources" / filename)
    error = None
    for path in candidates:
        try:
            directory = validate_directory(json.loads(path.read_text(encoding="utf-8")), market)
            return replace(directory, error=error)
        except FileNotFoundError:
            continue
        except (OSError, ValueError, KeyError, TypeError):
            error = "用户证券目录读取或校验失败；使用带原获取时间的发行资料快照。"
            continue
    raise ValueError("证券搜索目录不可用；仍可手动输入代码。")


def security_directory(market: str, *, force: bool = False) -> Directory:
    key = (str(user_data_dir()), market)
    def load():
        if not force:
            return _read_directory(market)
        directory = fetch_directory(market)
        filename = "a_shares.json" if market == "A 股" else "hk_shares.json"
        path = user_data_dir() / "securities" / filename
        with _file_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(directory_data(directory), ensure_ascii=False), encoding="utf-8")
            temporary.replace(path)
        return directory
    view = _cache.get(key, load, force=force,
        failure_message="证券目录更新失败；保留上次有效目录和原获取时间。")
    directory = view.value or _read_directory(market)
    return replace(directory, error=view.error or directory.error)
