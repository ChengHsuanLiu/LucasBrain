"""
動能篩選模組 (momentum_score)。

規則與配分定義見 `97_Settings/動能篩選門檻.md`：14 項個股動能指標，
從0分累加、無滿分上限（滿足越多條件分數越高，非扣分制）。

資料來源：FinMind TaiwanStockPrice / TaiwanStockInstitutionalInvestorsBuySell /
TaiwanStockMonthRevenue，皆逐檔查詢 (單檔一次呼叫可回傳一段日期範圍)。
**注意 (2026-07-11 除錯記錄)**：開發過程中曾誤判 HTTP 402 是「批次查詢 (data_id="")
帳號方案不支援」，改成逐檔查詢後仍持續 402，實際檢查 API 回應內容為
`{"msg":"Requests reach the upper limit."}`——是**當日/當期 API 總請求量配額用盡**，
與批次或逐檔查詢方式無關。換言之逐檔查詢並不會比批次更省配額，甚至因為每檔各自一次
請求、總請求數遠高於批次 (1次批次可涵蓋全市場 vs 839次逐檔)，逐檔查詢反而更快耗盡配額。
本模組先前已改寫為逐檔查詢 (fetch_price_history/fetch_taiex_history)，邏輯正確可用，
但配額回復後應評估改回批次以節省請求數——尤其是 fetch_price_history 若改回單一批次
`fetch_bulk_price_history` 風格，可用遠少於839次的請求數涵蓋全市場價格資料。

分層原則（比照 financial_screen.py）：
- fetch_* : 純資料抓取
- load_momentum_criteria : 讀取 97_Settings/動能篩選門檻.md 的配分/啟用設定
- compute_momentum_score : 評分規則，消費 fetch_* 與 load_* 的輸出
- scan_momentum_market : 迴圈全市場並回傳排序後的分數清單
"""
import time
from datetime import datetime, timedelta

from .stock_metrics import compute_ma_metrics, fetch_tdcc_history_finmind
from .financial_screen import (
    _finmind_request_with_retry,
    _parse_markdown_table,
    _fetch_raw_financials,
    _build_quarterly_series,
    _gross_margin,
    fetch_stock_universe,
    apply_liquidity_filter,
    load_screen_settings,
    load_liquidity_settings,
)

SETTINGS_PATH = r"C:\Users\User\Desktop\LucasBrain\97_Settings\動能篩選門檻.md"

INSTITUTIONAL_LOOKBACK_TRADING_DAYS = 20
PRICE_LOOKBACK_TRADING_DAYS = 75  # 60日新高/60MA需要至少61天算斜率，抓75天留餘裕
REVENUE_START_MONTHS_BACK = 16


# ==========================================
# 設定表讀取
# ==========================================
def load_momentum_criteria(settings_path=SETTINGS_PATH):
    """讀取「個股動能指標」表，回傳 [{key, category, label, points}]，僅回傳啟用=Y的列。"""
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
    except Exception as e:
        print(f"Warning: Failed to read momentum screen settings: {e}")
        return []

    rows = _parse_markdown_table(lines, lambda cols: cols[:3] == ['啟用', '指標分類', '篩選指標'])
    criteria = []
    for r in rows:
        if r.get('啟用', '').strip().upper() != 'Y':
            continue
        key = r.get('指標代號', '').replace('`', '').strip()
        try:
            points = float(r.get('配分', ''))
        except ValueError:
            continue
        if not key:
            continue
        criteria.append({
            "key": key,
            "category": r.get('指標分類', ''),
            "label": r.get('篩選指標', ''),
            "points": points,
            "note": r.get('條件說明', ''),
        })
    return criteria


# ==========================================
# 批次資料抓取 (市場快照，逐交易日累積)
# ==========================================
def fetch_price_history(ticker, lookback_trading_days=PRICE_LOOKBACK_TRADING_DAYS, rate_limit_sec=0.15):
    """逐檔抓取股價 (FinMind TaiwanStockPrice)，單檔一次呼叫即可回傳一段日期範圍。
    注意：此函式改為逐檔查詢而非批次——批次查詢 (data_id="") 實測在同一 session 內大量
    呼叫後會間歇性回傳 HTTP 402 (即使加大重試次數也未必能恢復，推測是批次查詢有獨立於
    逐檔查詢速率限制之外的用量上限)，逐檔查詢整個 session 皆穩定，故改用逐檔以確保可靠性。
    回傳依日期由舊到新排序的 [{date, close, volume, high}, ...]。"""
    start = (datetime.now() - timedelta(days=int(lookback_trading_days * 1.6) + 20)).strftime("%Y-%m-%d")
    records = _finmind_request_with_retry("TaiwanStockPrice", ticker, start)
    time.sleep(rate_limit_sec)
    out = [{"date": r["date"], "close": r.get("close"), "volume": r.get("Trading_Volume"), "high": r.get("max")}
           for r in records]
    out.sort(key=lambda e: e["date"])
    return out[-lookback_trading_days:]


def fetch_taiex_history(lookback_trading_days=PRICE_LOOKBACK_TRADING_DAYS):
    """抓取加權指數 (TAIEX) 同期資料，回傳依日期由舊到新排序的 [{date, close}, ...]。"""
    start = (datetime.now() - timedelta(days=int(lookback_trading_days * 1.6) + 20)).strftime("%Y-%m-%d")
    records = _finmind_request_with_retry("TaiwanStockPrice", "TAIEX", start)
    out = [{"date": r["date"], "close": r.get("close")} for r in records]
    out.sort(key=lambda e: e["date"])
    return out[-lookback_trading_days:]


def fetch_institutional_flow(ticker, lookback_trading_days=INSTITUTIONAL_LOOKBACK_TRADING_DAYS, rate_limit_sec=0.15):
    """逐檔抓取法人買賣超 (FinMind TaiwanStockInstitutionalInvestorsBuySell)。
    注意：此資料集的全市場批次查詢 (data_id="") 會回傳 HTTP 402 (帳號方案不支援批次)，
    與 TaiwanStockPrice/TaiwanStockMarketValue 不同，只能逐檔查詢 (單檔call可回傳一段日期範圍)。
    回傳依日期由舊到新排序的 [{date, trust_net, foreign_net}, ...]，trust_net/foreign_net
    為淨買超股數 (buy - sell)。"""
    start = (datetime.now() - timedelta(days=lookback_trading_days * 2 + 10)).strftime("%Y-%m-%d")
    records = _finmind_request_with_retry("TaiwanStockInstitutionalInvestorsBuySell", ticker, start)
    time.sleep(rate_limit_sec)

    by_date = {}
    for r in records:
        name = r.get("name")
        if name not in ("Investment_Trust", "Foreign_Investor"):
            continue
        net = (r.get("buy") or 0) - (r.get("sell") or 0)
        day_map = by_date.setdefault(r["date"], {"trust_net": 0, "foreign_net": 0})
        if name == "Investment_Trust":
            day_map["trust_net"] = net
        else:
            day_map["foreign_net"] = net

    series = [{"date": d, **v} for d, v in by_date.items()]
    series.sort(key=lambda e: e["date"])
    return series[-lookback_trading_days:]


def fetch_revenue_history(ticker, rate_limit_sec=0.15):
    """逐檔抓取月營收 (FinMind TaiwanStockMonthRevenue)，回傳依 (revenue_year, revenue_month)
    由舊到新排序的 [{revenue_year, revenue_month, revenue}, ...]。"""
    start = (datetime.now() - timedelta(days=REVENUE_START_MONTHS_BACK * 31)).strftime("%Y-%m-%d")
    records = _finmind_request_with_retry("TaiwanStockMonthRevenue", ticker, start)
    time.sleep(rate_limit_sec)
    out = [{"revenue_year": r["revenue_year"], "revenue_month": r["revenue_month"], "revenue": r["revenue"]}
           for r in records if r.get("revenue") is not None]
    out.sort(key=lambda r: (r["revenue_year"], r["revenue_month"]))
    return out


def fetch_quarterly_gross_margin(ticker, rate_limit_sec=0.15):
    """抓取近三季平均毛利率(%)，重用 financial_screen.py 的財報三表快取與毛利率計算，
    避免與 financial_score 重複打 API (共用同一份磁碟快取)。資料不足3季時回傳 None。"""
    raw = _fetch_raw_financials(ticker, rate_limit_sec=rate_limit_sec)
    quarters = _build_quarterly_series(raw)
    if len(quarters) < 3:
        return None
    margins = [_gross_margin(q) for q in quarters[-3:]]
    margins = [m for m in margins if m is not None]
    if not margins:
        return None
    return sum(margins) / len(margins)


def fetch_whale_holding_ratio(ticker, rate_limit_sec=0.15):
    """抓取最新一期400張以上大戶持股比例(%)，重用 stock_metrics.fetch_tdcc_history_finmind
    (FinMind TaiwanStockHoldingSharesPer)。無資料時回傳 None。"""
    start = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
    try:
        history = fetch_tdcc_history_finmind(ticker, start)
    except Exception:
        history = []
    time.sleep(rate_limit_sec)
    if not history:
        return None
    return history[0]["ratio_400"]


# ==========================================
# 評分邏輯
# ==========================================
def _revenue_yoy_series(revenue_records):
    """回傳依時間排序的 YoY% 清單 (需有去年同月資料才算得出，缺的月份跳過)。"""
    by_ym = {(r["revenue_year"], r["revenue_month"]): r["revenue"] for r in revenue_records}
    yoy_list = []
    for r in revenue_records:
        y, m, rev = r["revenue_year"], r["revenue_month"], r["revenue"]
        prior = by_ym.get((y - 1, m))
        if prior:
            yoy_list.append((y, m, (rev - prior) / abs(prior) * 100.0))
    return yoy_list


def compute_momentum_score(ticker, price_series, taiex_series, institutional_series, revenue_records, criteria,
                            gross_margin_avg=None, whale_ratio_400=None):
    """計算單一個股的 momentum_score (從0累加，無上限)，回傳
    {ticker, total_score, breakdown: [...], data_complete}。
    breakdown 每項含 {criterion, key, points_earned, passed}。
    gross_margin_avg：近三季平均毛利率(%)，None表示資料不足。
    whale_ratio_400：最新一期400張以上大戶持股比例(%)，None表示資料不足。"""
    earned = {}

    closes = [p["close"] for p in price_series if p["close"] is not None]
    volumes = [p["volume"] for p in price_series if p["volume"] is not None]
    highs = [p["high"] for p in price_series if p["high"] is not None]

    data_complete = len(closes) >= 61 and len(institutional_series) >= 2

    if len(closes) >= 61:
        ma = compute_ma_metrics(closes)
        current_price = closes[-1]

        # 1. 創60日新高 (量能確認)
        recent_60_closes = closes[-60:]
        recent_20_volumes = volumes[-20:] if len(volumes) >= 20 else volumes
        avg_vol_20 = sum(recent_20_volumes) / len(recent_20_volumes) if recent_20_volumes else 0
        today_vol = volumes[-1] if volumes else 0
        is_60d_high = current_price >= max(recent_60_closes)
        vol_confirmed = avg_vol_20 > 0 and today_vol >= avg_vol_20 * 1.5
        earned["price_60d_high"] = is_60d_high and vol_confirmed

        # 2. 均線多頭排列
        vals = {p: ma[p]["val"] for p in (5, 10, 20, 60)}
        earned["ma_bullish_alignment"] = all(v > 0 for v in vals.values()) and vals[5] > vals[10] > vals[20] > vals[60]

        # 3. 價格在五日線之上
        earned["price_above_5ma"] = ma[5]["val"] > 0 and current_price > ma[5]["val"]

        # 4-6. 均線上彎
        earned["ma5_up"] = ma[5]["slope"] == "上彎"
        earned["ma20_up"] = ma[20]["slope"] == "上彎"
        earned["ma60_up"] = ma[60]["slope"] == "上彎"

        # 7. 價量同步上漲
        if len(closes) >= 2 and len(volumes) >= 2:
            earned["price_up_volume_up"] = closes[-1] > closes[-2] and volumes[-1] > volumes[-2]
        else:
            earned["price_up_volume_up"] = False

        # 8. 當日漲幅 > 5%
        if len(closes) >= 2 and closes[-2]:
            daily_gain = (closes[-1] - closes[-2]) / closes[-2] * 100.0
            earned["daily_gain_5pct"] = daily_gain > 5
        else:
            daily_gain = None
            earned["daily_gain_5pct"] = False

        # 9. 當日漲停鎖死 (近似判斷：漲幅>=9.5% 且收盤=當日最高價)
        today_high = highs[-1] if highs else None
        earned["limit_up_locked"] = (
            daily_gain is not None and daily_gain >= 9.5
            and today_high is not None and current_price >= today_high
        )
    else:
        for k in ("price_60d_high", "ma_bullish_alignment", "price_above_5ma", "ma5_up",
                   "ma20_up", "ma60_up", "price_up_volume_up", "daily_gain_5pct", "limit_up_locked"):
            earned[k] = False

    # 10. RS強度
    if len(closes) >= 21 and len(taiex_series) >= 21:
        taiex_closes = [p["close"] for p in taiex_series if p["close"] is not None]
        if len(taiex_closes) >= 21 and closes[-21] and taiex_closes[-21]:
            stock_ret = (closes[-1] - closes[-21]) / closes[-21] * 100.0
            taiex_ret = (taiex_closes[-1] - taiex_closes[-21]) / taiex_closes[-21] * 100.0
            earned["rs_strength"] = (stock_ret - taiex_ret) > 0
        else:
            earned["rs_strength"] = False
    else:
        earned["rs_strength"] = False

    # 11-13. 法人籌碼
    if len(institutional_series) >= 2:
        last2 = institutional_series[-2:]
        earned["trust_buy_streak"] = all(d["trust_net"] > 0 for d in last2)
        earned["foreign_buy_streak"] = all(d["foreign_net"] > 0 for d in last2)
    else:
        earned["trust_buy_streak"] = False
        earned["foreign_buy_streak"] = False

    if len(institutional_series) >= 1:
        # 投信買超金額(元) 以 淨買股數 x 當日收盤價 近似
        price_by_date = {p["date"]: p["close"] for p in price_series if p["close"] is not None}
        trust_amounts = []
        for d in institutional_series[-20:]:
            px = price_by_date.get(d["date"])
            if px:
                trust_amounts.append(d["trust_net"] * px)
        if trust_amounts:
            earned["trust_buy_high"] = trust_amounts[-1] > 0 and trust_amounts[-1] >= max(trust_amounts)
        else:
            earned["trust_buy_high"] = False
    else:
        earned["trust_buy_high"] = False

    # 14. 營收加速
    yoy_series = _revenue_yoy_series(revenue_records)
    if len(yoy_series) >= 3:
        yoy_m, yoy_m1, yoy_m2 = yoy_series[-1][2], yoy_series[-2][2], yoy_series[-3][2]
        earned["revenue_accel"] = yoy_m > yoy_m1 > yoy_m2
    else:
        earned["revenue_accel"] = False

    # 15-17. 近三季平均毛利率分層 (各門檻獨立判斷，非互斥級距)
    if gross_margin_avg is not None:
        earned["gross_margin_20"] = gross_margin_avg > 20
        earned["gross_margin_35"] = gross_margin_avg > 35
        earned["gross_margin_50"] = gross_margin_avg > 50
    else:
        earned["gross_margin_20"] = False
        earned["gross_margin_35"] = False
        earned["gross_margin_50"] = False

    # 18-19. 400張以上大戶持股分層 (各門檻獨立判斷，非互斥級距)
    if whale_ratio_400 is not None:
        earned["whale_400_35"] = whale_ratio_400 > 35
        earned["whale_400_50"] = whale_ratio_400 > 50
    else:
        earned["whale_400_35"] = False
        earned["whale_400_50"] = False

    breakdown = []
    total_score = 0
    for c in criteria:
        passed = bool(earned.get(c["key"], False))
        points_earned = c["points"] if passed else 0
        total_score += points_earned
        breakdown.append({
            "criterion": c["label"], "key": c["key"],
            "points_earned": points_earned, "passed": passed,
        })

    return {
        "ticker": ticker, "total_score": total_score,
        "breakdown": breakdown, "data_complete": data_complete,
    }


def scan_momentum_market(rate_limit_sec=0.15, progress_callback=None, universe=None):
    """掃描全市場 (或指定 universe)，回傳依 total_score 由高到低排序的分數清單。
    universe=None 時透過 fetch_stock_universe() + apply_liquidity_filter() 抓取
    (與 financial_screen 共用同一套市場範圍/流動性設定)。
    progress_callback(index, total, ticker) 可選，用於長時間掃描時回報進度。"""
    criteria = load_momentum_criteria()

    if universe is None:
        universe = fetch_stock_universe(settings=load_screen_settings())
        liquidity_settings = load_liquidity_settings()
        if liquidity_settings["enabled"]:
            universe, _ = apply_liquidity_filter(universe, settings=liquidity_settings)

    print("Fetching TAIEX index history...")
    taiex_series = fetch_taiex_history()

    results = []
    total = len(universe)
    for i, stock in enumerate(universe):
        ticker = stock["stock_id"]
        if progress_callback:
            progress_callback(i + 1, total, ticker)
        try:
            price_series = fetch_price_history(ticker, rate_limit_sec=rate_limit_sec)
            institutional_series = fetch_institutional_flow(ticker, rate_limit_sec=rate_limit_sec)
            revenue_records = fetch_revenue_history(ticker, rate_limit_sec=rate_limit_sec)
            gross_margin_avg = fetch_quarterly_gross_margin(ticker, rate_limit_sec=rate_limit_sec)
            whale_ratio_400 = fetch_whale_holding_ratio(ticker, rate_limit_sec=rate_limit_sec)
            score = compute_momentum_score(
                ticker,
                price_series=price_series,
                taiex_series=taiex_series,
                institutional_series=institutional_series,
                revenue_records=revenue_records,
                criteria=criteria,
                gross_margin_avg=gross_margin_avg,
                whale_ratio_400=whale_ratio_400,
            )
            score["name"] = stock.get("stock_name")
        except Exception as e:
            score = {"ticker": ticker, "name": stock.get("stock_name"), "total_score": 0,
                      "breakdown": [], "data_complete": False, "error": str(e)}
        results.append(score)

    results.sort(key=lambda r: r["total_score"], reverse=True)
    return results
