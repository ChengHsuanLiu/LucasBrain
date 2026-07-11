"""
全市場財務指標篩選模組 (financial_score)。

規則原始定義見 `40_Library/財務指標篩選機制.md`（10 項指標、100 分制配分表的設計理由）；
可調整的門檻/配分/範圍參數則讀取自 `97_Settings/財務指標篩選門檻.md`，調參數不需要改程式碼。

資料來源：FinMind TaiwanStockInfo / TaiwanStockFinancialStatements /
TaiwanStockBalanceSheet / TaiwanStockCashFlowsStatement（付費 Backer 方案）。

分層原則（比照 stock_metrics.py）：
- fetch_* : 純資料抓取，含磁碟快取與重試邏輯
- load_* : 讀取 97_Settings/財務指標篩選門檻.md 的可調參數
- compute_financial_score : 評分規則，消費 fetch_* 與 load_* 的輸出
- scan_market : 迴圈全市場並回傳排序後的分數清單
"""
import json
import os
import re
import time
import urllib.error
from datetime import datetime, timedelta

from .stock_metrics import _finmind_request

CACHE_DIR = r"C:\Users\User\Desktop\LucasBrain\.agent\data\financial_cache"
CACHE_MAX_AGE_DAYS = 7  # 超過此天數才重新呼叫 API，季報資料不會日內變動
SETTINGS_PATH = r"C:\Users\User\Desktop\LucasBrain\97_Settings\財務指標篩選門檻.md"
FINANCIAL_STATEMENT_START = "2023-01-01"  # 抓取起始日，確保有足夠季度算 YoY (需回溯5季)

_OPERATORS = {
    ">": lambda v, t: v > t,
    "<": lambda v, t: v < t,
    ">=": lambda v, t: v >= t,
    "<=": lambda v, t: v <= t,
}


# ==========================================
# 設定表讀取 (97_Settings/財務指標篩選門檻.md)
# ==========================================
def _parse_markdown_table(lines, header_predicate):
    """從一段 markdown 行清單中找到符合 header_predicate 的表格，回傳
    [{欄位名: 值, ...}, ...]（欄位名取自表頭列，值皆為 trim 過的字串）。"""
    rows = []
    header = None
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('|'):
            if in_table and header is not None:
                break
            continue
        cols = [c.strip() for c in stripped.split('|')[1:-1]]
        if header is None:
            if header_predicate(cols):
                header = cols
                in_table = True
            continue
        if all(c.startswith(':') or set(c) <= {':', '-'} for c in cols):
            continue  # 分隔列 (|:---|:---|)
        rows.append(dict(zip(header, cols)))
    return rows


def load_financial_criteria(settings_path=SETTINGS_PATH):
    """讀取「指標門檻與配分」表，回傳 [{key, category, label, basis, operator, threshold, points, enabled}]。
    僅回傳「啟用」欄為 Y 的列。讀取失敗時 fallback 為空清單 (呼叫端應自行判斷是否要用預設值)。"""
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
    except Exception as e:
        print(f"Warning: Failed to read financial screen settings: {e}")
        return []

    rows = _parse_markdown_table(lines, lambda cols: cols[:3] == ['啟用', '指標分類', '篩選指標'])
    criteria = []
    for r in rows:
        if r.get('啟用', '').strip().upper() != 'Y':
            continue
        key_raw = r.get('指標代號', '')
        key = re.sub(r'`', '', key_raw).strip()
        try:
            threshold = float(r.get('門檻值', ''))
            points = float(r.get('配分', ''))
        except ValueError:
            continue
        operator = r.get('運算子', '').strip()
        if not key or operator not in _OPERATORS:
            continue
        criteria.append({
            "key": key,
            "category": r.get('指標分類', ''),
            "label": r.get('篩選指標', ''),
            "basis": r.get('比較基礎', ''),
            "operator": operator,
            "threshold": threshold,
            "points": points,
            "note": r.get('設計邏輯', ''),
        })
    return criteria


def load_screen_settings(settings_path=SETTINGS_PATH):
    """讀取「資料完整性處理原則」與「全市場掃描範圍設定」兩張 設定項/目前值 表格，
    回傳 {missing_data_policy, min_quarters_required, include_types, excluded_categories}。
    讀取失敗或表格缺列時 fallback 為程式內建預設值，確保腳本仍可運作。"""
    defaults = {
        "missing_data_policy": "lenient",
        "min_quarters_required": 5,
        "include_types": ("twse", "tpex"),
        "excluded_categories": {
            "ETF", "ETN", "Index", "上櫃ETF", "上櫃指數股票型基金(ETF)",
            "受益證券", "大盤", "存託憑證", "所有證券", "指數投資證券(ETN)",
            "金融保險", "金融業",
        },
    }
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
    except Exception as e:
        print(f"Warning: Failed to read financial screen settings, using defaults: {e}")
        return defaults

    rows = _parse_markdown_table(lines, lambda cols: cols[:2] == ['設定項', '目前值'])
    settings = dict(defaults)
    for r in rows:
        item, value = r.get('設定項', ''), r.get('目前值', '')
        if item == '史料不足處理方式' and value in ('lenient', 'strict'):
            settings['missing_data_policy'] = value
        elif item == '最少所需季度數':
            try:
                settings['min_quarters_required'] = int(value)
            except ValueError:
                pass
        elif item == '納入市場別':
            settings['include_types'] = tuple(v.strip() for v in value.split(',') if v.strip())
        elif item == '排除產業類別':
            settings['excluded_categories'] = {v.strip() for v in value.split(',') if v.strip()}
    return settings


def load_liquidity_settings(settings_path=SETTINGS_PATH):
    """讀取「流動性與市值篩選」設定項/目前值表格，回傳
    {enabled, min_market_cap, min_avg_daily_value, lookback_days}（市值/成交金額單位為元，非億/萬）。"""
    defaults = {
        "enabled": True,
        "min_market_cap": 30 * 1e8,
        "min_avg_daily_value": 1000 * 1e4,
        "lookback_days": 5,
    }
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
    except Exception as e:
        print(f"Warning: Failed to read liquidity settings, using defaults: {e}")
        return defaults

    rows = _parse_markdown_table(lines, lambda cols: cols[:2] == ['設定項', '目前值'])
    settings = dict(defaults)
    for r in rows:
        item, value = r.get('設定項', ''), r.get('目前值', '')
        try:
            if item == '啟用流動性/市值篩選':
                settings['enabled'] = value.strip().upper() == 'Y'
            elif item == '最低市值 (億元)':
                settings['min_market_cap'] = float(value) * 1e8
            elif item == '最低日均成交金額 (萬元)':
                settings['min_avg_daily_value'] = float(value) * 1e4
            elif item == '成交量回溯交易日數':
                settings['lookback_days'] = int(value)
        except ValueError:
            continue
    return settings


# ==========================================
# FinMind 資料抓取 (含快取)
# ==========================================
def _cache_path(ticker):
    return os.path.join(CACHE_DIR, f"{ticker}.json")


def _load_cache(ticker):
    path = _cache_path(ticker)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _save_cache(ticker, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_cache_path(ticker), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _cache_is_fresh(cache):
    if not cache or not cache.get("fetched_at"):
        return False
    age_days = (time.time() - cache["fetched_at"]) / 86400.0
    return age_days < CACHE_MAX_AGE_DAYS


def _finmind_request_with_retry(dataset, data_id, start_date, max_retries=3, backoff_sec=2.0):
    """包裝 _finmind_request，遇到速率限制/暫時性錯誤時重試 (指數退避)。"""
    for attempt in range(max_retries):
        try:
            return _finmind_request(dataset, data_id, start_date)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                time.sleep(backoff_sec * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(backoff_sec * (attempt + 1))
                continue
            raise
    return []


def fetch_stock_universe(settings=None):
    """回傳 [{stock_id, stock_name, industry_category, type}]，依 97_Settings 設定過濾類別，
    並依 stock_id 去重 (TaiwanStockInfo 含歷史類別異動列，僅保留最新一筆)。"""
    settings = settings or load_screen_settings()
    records = _finmind_request_with_retry("TaiwanStockInfo", "", "2020-01-01")
    latest_by_id = {}
    for r in records:
        if r.get("type") not in settings["include_types"]:
            continue
        if r.get("industry_category") in settings["excluded_categories"]:
            continue
        sid = r.get("stock_id")
        if sid not in latest_by_id or r.get("date", "") > latest_by_id[sid].get("date", ""):
            latest_by_id[sid] = r
    return sorted(latest_by_id.values(), key=lambda r: r["stock_id"])


def fetch_market_cap_snapshot(max_lookback_calendar_days=10):
    """回傳最近一個交易日的 {stock_id: market_value}，一次 API 呼叫抓全市場快照
    (TaiwanStockMarketValue data_id="" 回傳當日全市場資料)。從今天往回找，直到找到
    有資料的交易日為止 (跳過假日/週末)。"""
    d = datetime.now()
    for _ in range(max_lookback_calendar_days):
        date_str = d.strftime("%Y-%m-%d")
        records = _finmind_request_with_retry("TaiwanStockMarketValue", "", date_str)
        if records:
            return {r["stock_id"]: r["market_value"] for r in records if r.get("market_value") is not None}
        d -= timedelta(days=1)
    return {}


def fetch_liquidity_snapshot(lookback_days=5, max_calendar_days=15):
    """回傳近 lookback_days 個交易日的 {stock_id: 平均每日成交金額}，透過逐日呼叫
    TaiwanStockPrice (data_id="" 回傳當日全市場資料) 累積，非交易日 (假日/週末) 自動跳過。
    每個交易日僅需 1 次 API 呼叫，遠比逐檔查詢省下大量請求數。"""
    totals = {}
    counts = {}
    collected_days = 0
    d = datetime.now()
    calendar_days_checked = 0
    while collected_days < lookback_days and calendar_days_checked < max_calendar_days:
        date_str = d.strftime("%Y-%m-%d")
        records = _finmind_request_with_retry("TaiwanStockPrice", "", date_str)
        if records:
            for r in records:
                money = r.get("Trading_money")
                if money is None:
                    continue
                sid = r["stock_id"]
                totals[sid] = totals.get(sid, 0.0) + money
                counts[sid] = counts.get(sid, 0) + 1
            collected_days += 1
        d -= timedelta(days=1)
        calendar_days_checked += 1
    return {sid: totals[sid] / counts[sid] for sid in totals}


def apply_liquidity_filter(universe, settings=None):
    """依市值與日均成交金額過濾 universe，回傳 (filtered_universe, excluded_count)。
    settings=None 時透過 load_liquidity_settings() 讀取；啟用=False 時原樣回傳不過濾。"""
    settings = settings or load_liquidity_settings()
    if not settings["enabled"]:
        return universe, 0

    market_caps = fetch_market_cap_snapshot()
    avg_values = fetch_liquidity_snapshot(lookback_days=settings["lookback_days"])

    filtered = []
    for stock in universe:
        sid = stock["stock_id"]
        cap = market_caps.get(sid)
        avg_value = avg_values.get(sid)
        if cap is not None and cap < settings["min_market_cap"]:
            continue
        if avg_value is not None and avg_value < settings["min_avg_daily_value"]:
            continue
        filtered.append(stock)
    return filtered, len(universe) - len(filtered)


def _fetch_raw_financials(ticker, rate_limit_sec=0.15):
    """抓取單一個股的財報三表原始資料 (含磁碟快取)，回傳
    {financials: [...], balance_sheet: [...], cash_flow: [...], fetched_at}。"""
    cache = _load_cache(ticker)
    if _cache_is_fresh(cache):
        return cache

    fs = _finmind_request_with_retry("TaiwanStockFinancialStatements", ticker, FINANCIAL_STATEMENT_START)
    time.sleep(rate_limit_sec)
    bs = _finmind_request_with_retry("TaiwanStockBalanceSheet", ticker, FINANCIAL_STATEMENT_START)
    time.sleep(rate_limit_sec)
    cf = _finmind_request_with_retry("TaiwanStockCashFlowsStatement", ticker, FINANCIAL_STATEMENT_START)
    time.sleep(rate_limit_sec)

    data = {
        "financials": fs,
        "balance_sheet": bs,
        "cash_flow": cf,
        "fetched_at": time.time(),
    }
    _save_cache(ticker, data)
    return data


def _pivot_by_date(records, wanted_types):
    """把 FinMind 的 [{date, type, value}] 長格式，依 date 轉成 {date: {type: value}} 寬格式，
    僅保留 wanted_types 內的欄位。"""
    by_date = {}
    for r in records:
        t = r.get("type")
        if t not in wanted_types:
            continue
        d = r.get("date")
        by_date.setdefault(d, {})[t] = r.get("value")
    return by_date


def _build_quarterly_series(raw):
    """合併三表為單一按季排序的清單。僅保留三表同時有資料的季度 (date 交集)。"""
    fs_by_date = _pivot_by_date(raw["financials"], {"Revenue", "GrossProfit", "OperatingIncome", "IncomeAfterTaxes"})
    bs_by_date = _pivot_by_date(raw["balance_sheet"], {"Inventories", "TotalAssets", "Liabilities", "EquityAttributableToOwnersOfParent"})
    cf_by_date = _pivot_by_date(raw["cash_flow"], {"CashFlowsFromOperatingActivities", "PropertyAndPlantAndEquipment"})

    common_dates = sorted(set(fs_by_date) & set(bs_by_date) & set(cf_by_date))
    quarters = []
    for d in common_dates:
        fs, bs, cf = fs_by_date[d], bs_by_date[d], cf_by_date[d]
        revenue = fs.get("Revenue")
        if revenue is None or revenue == 0:
            continue
        quarters.append({
            "date": d,
            "revenue": revenue,
            "gross_profit": fs.get("GrossProfit"),
            "operating_income": fs.get("OperatingIncome"),
            "net_income": fs.get("IncomeAfterTaxes"),
            "inventory": bs.get("Inventories"),
            "total_assets": bs.get("TotalAssets"),
            "liabilities": bs.get("Liabilities"),
            "equity": bs.get("EquityAttributableToOwnersOfParent"),
            "operating_cash_flow": cf.get("CashFlowsFromOperatingActivities"),
            "capex": cf.get("PropertyAndPlantAndEquipment"),  # FinMind 原始值已為負數 (現金流出)
        })
    return quarters


def _pct_change(current, prior):
    if current is None or prior is None or prior == 0:
        return None
    return (current - prior) / abs(prior) * 100.0


def _gross_margin(q):
    if q is None or q["revenue"] in (None, 0) or q["gross_profit"] is None:
        return None
    return q["gross_profit"] / q["revenue"] * 100.0


def _inventory_to_sales(q):
    if q is None or q["revenue"] in (None, 0) or q["inventory"] is None:
        return None
    return q["inventory"] / q["revenue"]


# key -> 需要哪些季度 ('q0'/'q1'/'q4') + 如何從中算出比較值的函式
def _build_value_getters():
    return {
        "revenue_yoy": (("q0", "q4"), lambda q0, q1, q4: _pct_change(q0["revenue"], q4["revenue"]) if q4 else None),
        "revenue_qoq": (("q0", "q1"), lambda q0, q1, q4: _pct_change(q0["revenue"], q1["revenue"]) if q1 else None),
        "op_income_yoy": (("q0", "q4"), lambda q0, q1, q4: _pct_change(q0["operating_income"], q4["operating_income"]) if q4 else None),
        "op_income_qoq": (("q0", "q1"), lambda q0, q1, q4: _pct_change(q0["operating_income"], q1["operating_income"]) if q1 else None),
        "gross_margin_yoy": (("q0", "q4"), lambda q0, q1, q4: (_gross_margin(q0) - _gross_margin(q4)) if (q4 and _gross_margin(q0) is not None and _gross_margin(q4) is not None) else None),
        "gross_margin_qoq": (("q0", "q1"), lambda q0, q1, q4: (_gross_margin(q0) - _gross_margin(q1)) if (q1 and _gross_margin(q0) is not None and _gross_margin(q1) is not None) else None),
        "roe": (("q0",), lambda q0, q1, q4: (q0["net_income"] / q0["equity"] * 100.0) if (q0["net_income"] is not None and q0["equity"]) else None),
        "fcf": (("q0",), lambda q0, q1, q4: (q0["operating_cash_flow"] + q0["capex"]) if (q0["operating_cash_flow"] is not None and q0["capex"] is not None) else None),
        "debt_ratio": (("q0",), lambda q0, q1, q4: (q0["liabilities"] / q0["total_assets"] * 100.0) if (q0["liabilities"] is not None and q0["total_assets"]) else None),
        "inventory_qoq": (("q0", "q1"), lambda q0, q1, q4: (_inventory_to_sales(q0) - _inventory_to_sales(q1)) if (q1 and _inventory_to_sales(q0) is not None and _inventory_to_sales(q1) is not None) else None),
        "inventory_yoy": (("q0", "q4"), lambda q0, q1, q4: (_inventory_to_sales(q0) - _inventory_to_sales(q4)) if (q4 and _inventory_to_sales(q0) is not None and _inventory_to_sales(q4) is not None) else None),
    }


def compute_financial_score(ticker, name=None, rate_limit_sec=0.15, criteria=None, settings=None):
    """計算單一個股的 financial_score，回傳
    {ticker, name, total_score, max_possible_score, latest_quarter, breakdown: [...], data_complete}。
    breakdown 每項含 {criterion, key, points_earned, points_max, value, note}。
    criteria/settings 未帶入時會各自從 97_Settings/財務指標篩選門檻.md 重新讀取
    (scan_market() 迴圈呼叫時應在外層讀一次、傳入避免重複讀檔)。"""
    criteria = criteria if criteria is not None else load_financial_criteria()
    settings = settings if settings is not None else load_screen_settings()
    value_getters = _build_value_getters()

    raw = _fetch_raw_financials(ticker, rate_limit_sec=rate_limit_sec)
    quarters = _build_quarterly_series(raw)

    if not quarters:
        return {
            "ticker": ticker, "name": name, "total_score": 0, "max_possible_score": 0,
            "latest_quarter": None, "breakdown": [], "data_complete": False,
        }

    min_q = settings["min_quarters_required"]
    q0 = quarters[-1]
    q1 = quarters[-2] if len(quarters) >= 2 else None
    q4 = quarters[-min_q] if len(quarters) >= min_q else None
    lenient = settings["missing_data_policy"] == "lenient"

    breakdown = []
    for c in criteria:
        getter = value_getters.get(c["key"])
        if getter is None:
            continue
        _, value_fn = getter
        value = value_fn(q0, q1, q4)

        if value is None:
            points_max = 0 if lenient else c["points"]
            breakdown.append({
                "criterion": c["label"], "key": c["key"], "points_earned": 0,
                "points_max": points_max, "value": None, "note": "史料不足，無法計算",
            })
            continue

        passed = _OPERATORS[c["operator"]](value, c["threshold"])
        breakdown.append({
            "criterion": c["label"], "key": c["key"],
            "points_earned": c["points"] if passed else 0, "points_max": c["points"],
            "value": value, "note": c["note"],
        })

    total_score = sum(b["points_earned"] for b in breakdown)
    max_possible_score = sum(b["points_max"] for b in breakdown)
    data_complete = q4 is not None

    return {
        "ticker": ticker, "name": name, "total_score": total_score,
        "max_possible_score": max_possible_score, "latest_quarter": q0["date"],
        "breakdown": breakdown, "data_complete": data_complete,
    }


def scan_market(rate_limit_sec=0.15, min_score=None, progress_callback=None, universe=None):
    """掃描全市場 (或指定 universe)，回傳依 total_score 由高到低排序的分數清單。
    universe=None 時透過 fetch_stock_universe() 抓取全市場清單。
    progress_callback(index, total, ticker) 可選，用於長時間掃描時回報進度。"""
    settings = load_screen_settings()
    criteria = load_financial_criteria()
    if universe is None:
        universe = fetch_stock_universe(settings=settings)

    results = []
    total = len(universe)
    for i, stock in enumerate(universe):
        ticker = stock["stock_id"]
        name = stock.get("stock_name")
        if progress_callback:
            progress_callback(i + 1, total, ticker)
        try:
            score = compute_financial_score(ticker, name=name, rate_limit_sec=rate_limit_sec,
                                              criteria=criteria, settings=settings)
        except Exception as e:
            score = {
                "ticker": ticker, "name": name, "total_score": 0, "max_possible_score": 0,
                "latest_quarter": None, "breakdown": [], "data_complete": False, "error": str(e),
            }
        if min_score is None or score["total_score"] >= min_score:
            results.append(score)

    results.sort(key=lambda r: r["total_score"], reverse=True)
    return results
