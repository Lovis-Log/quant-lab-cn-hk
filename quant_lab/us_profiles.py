"""Public US company identities from AKShare's Eastmoney profile endpoint.

Only names and source identifiers are requested. These do not certify a price
feed, listing history, corporate actions, or a market-data retention licence.
"""

import requests

from quant_lab.us_market import normalize_us_symbol


URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
SOURCE = "东方财富公开美股公司基础资料（NYSE/Nasdaq）"


def profile_identity(row):
    source_code = row["SECURITY_CODE"]
    if row["SECUCODE"] not in (source_code + ".O", source_code + ".N"):
        raise ValueError("美股证券资料市场或来源代码不匹配。")
    # The profile endpoint spells share classes BRK_B; price research uses BRK.B.
    code = normalize_us_symbol(source_code.replace("_", "."))
    name = row.get("ORG_NAME") or row.get("ORG_EN_ABBR")
    if not isinstance(name, str) or not name.strip() or name.strip().lower() in {"-", "null", "nan"}:
        raise ValueError("美股证券资料名称无效。")
    return code, name.strip()


def profile_page(page=1, symbol=None):
    params = {"reportName": "RPT_USF10_INFO_ORGPROFILE",
              "columns": "SECUCODE,SECURITY_CODE,ORG_NAME,ORG_EN_ABBR",
              "pageNumber": str(page), "pageSize": "500", "source": "SECURITIES",
              "client": "PC", "sortColumns": "SECUCODE", "sortTypes": "1"}
    if symbol is not None:
        canonical = normalize_us_symbol(symbol)
        params["filter"] = f'(SECURITY_CODE="{canonical.replace(".", "_")}")'
    with requests.get(URL, params=params, timeout=(3, 10)) as response:
        response.raise_for_status()
        payload = response.json()
    result = payload.get("result")
    if not payload.get("success") or not isinstance(result, dict) or not result.get("data"):
        raise ValueError("美股基础资料未返回有效记录；不能据此判断证券不存在。")
    if not 1 <= int(result["pages"]) <= 100:
        raise ValueError("美股证券目录分页异常。")
    return result


def security_name(symbol):
    symbol = normalize_us_symbol(symbol)
    rows = profile_page(symbol=symbol)["data"]
    identities = [profile_identity(row) for row in rows]
    if len(identities) != 1 or identities[0][0] != symbol:
        raise ValueError("美股证券资料与查询不匹配。")
    return identities[0][1]


def directory_rows():
    rows, page, pages = [], 1, 1
    while page <= pages:
        result = profile_page(page)
        pages = int(result["pages"])
        for row in result["data"]:
            source_code = row.get("SECURITY_CODE", "")
            if row.get("SECUCODE") not in (source_code + ".O", source_code + ".N"):
                continue  # OTC and other venues are outside the supported directory.
            try:
                normalize_us_symbol(source_code.replace("_", "."))
            except ValueError:
                continue  # Unsupported preferred/warrant namespaces are not guessed.
            rows.append(profile_identity(row))
        page += 1
    return rows
