"""
大盤(加權指數/櫃買指數)資料與技術指標共用模組，供 generate_daily_report.py 使用。

分層原則：
- fetch_* : 純資料抓取 (FinMind 指數OHLC、TWSE/TPEx官方融資餘額、三大法人、外資期貨)
- compute_* : 純計算 (均線/乖離、KD、MACD、量增減判定)，不含文字敘述
- detect_* : 型態偵測 (黃金/死亡交叉、簡易背離)，回傳布林/日期，不含文字敘述

KD/MACD 背離偵測是簡化版的高低點比對，非嚴謹的技術分析演算法，僅供參考。
"""
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_metrics import _finmind_request, calculate_ma, CREDENTIALS_PATH

INDEX_MA_PERIODS = [5, 20, 60]


# ==========================================
# 1. Index OHLC (TAIEX / TPEx)
# ==========================================
def fetch_index_history(index_id, start_date, credentials_path=CREDENTIALS_PATH):
    """index_id: 'TAIEX' (上市加權指數) 或 'TPEx' (上櫃指數)。回傳依日期由舊到新排序的
    [{date, open, high, low, close, volume, money, spread}]。money 為當日成交金額(元)，
    spread 為 FinMind 提供的當日漲跌點數 (close - 前一日close)。"""
    records = _finmind_request("TaiwanStockPrice", index_id, start_date, credentials_path)
    records.sort(key=lambda r: r.get("date", ""))
    out = []
    for r in records:
        out.append({
            "date": r["date"],
            "open": r.get("open", 0.0),
            "high": r.get("max", 0.0),
            "low": r.get("min", 0.0),
            "close": r.get("close", 0.0),
            "volume": r.get("Trading_Volume", 0),
            "money": r.get("Trading_money", 0),
            "spread": r.get("spread", 0.0),
        })
    return out


# ==========================================
# 2. Technical Indicators
# ==========================================
def compute_index_ma(ohlc, periods=INDEX_MA_PERIODS):
    """回傳 {period: {val, val_prev, slope, close_vs_ma}}。close_vs_ma 為 "漲過"/"跌破"。"""
    closes = [r["close"] for r in ohlc]
    current_price = closes[-1] if closes else 0.0
    result = {}
    for p in periods:
        ma_val = calculate_ma(closes, p, -1)
        ma_prev = calculate_ma(closes, p, -2)
        if ma_val is None:
            result[p] = {"val": None, "val_prev": None, "slope": "無數據", "close_vs_ma": "無數據"}
            continue
        slope = "上彎" if (ma_prev is not None and ma_val > ma_prev) else "下彎"
        close_vs_ma = "漲過" if current_price > ma_val else "跌破"
        result[p] = {"val": ma_val, "val_prev": ma_prev, "slope": slope, "close_vs_ma": close_vs_ma}
    return result


def compute_bias(ohlc, periods=INDEX_MA_PERIODS):
    """回傳 {period: 帶正負號的乖離% (close 相對 MA)}。"""
    closes = [r["close"] for r in ohlc]
    current_price = closes[-1] if closes else 0.0
    result = {}
    for p in periods:
        ma_val = calculate_ma(closes, p, -1)
        result[p] = ((current_price - ma_val) / ma_val * 100) if ma_val else None
    return result


def compute_volume_trend(ohlc):
    """比較最近一日成交量 vs 前一日，回傳 ("量增"/"量縮", 變化%)。"""
    if len(ohlc) < 2:
        return "無數據", 0.0
    today_vol = ohlc[-1]["volume"]
    prev_vol = ohlc[-2]["volume"]
    if not prev_vol:
        return "無數據", 0.0
    change_pct = (today_vol - prev_vol) / prev_vol * 100
    return ("量增" if today_vol > prev_vol else "量縮"), change_pct


def compute_volume_ma(ohlc, period=5):
    """回傳 {ma, ma_prev, slope, position}：period日均量值/前一期均量值/
    均量斜率(上彎/下彎)/今日成交量相對均量線的位置(站上/跌破)。資料不足時回傳 slope/position 為 "無數據"。"""
    volumes = [r["volume"] for r in ohlc]
    n = len(volumes)
    if n < period + 1:
        return {"ma": None, "ma_prev": None, "slope": "無數據", "position": "無數據"}
    ma_val = sum(volumes[-period:]) / period
    ma_prev = sum(volumes[-period - 1:-1]) / period
    slope = "上彎" if ma_val > ma_prev else "下彎"
    position = "站上" if volumes[-1] > ma_val else "跌破"
    return {"ma": ma_val, "ma_prev": ma_prev, "slope": slope, "position": position}


def compute_kd(ohlc, period=9, k_smooth=3, d_smooth=3):
    """標準 KD 指標 (9,3,3)。回傳依日期排序的 [{date, k, d}]，前 period-1 筆因資料不足為 None。"""
    n = len(ohlc)
    rsv_list = [None] * n
    for i in range(n):
        if i < period - 1:
            continue
        window = ohlc[i - period + 1: i + 1]
        low_n = min(r["low"] for r in window)
        high_n = max(r["high"] for r in window)
        close = ohlc[i]["close"]
        rsv = 50.0 if high_n == low_n else (close - low_n) / (high_n - low_n) * 100
        rsv_list[i] = rsv

    k_list = [None] * n
    d_list = [None] * n
    prev_k, prev_d = 50.0, 50.0
    for i in range(n):
        if rsv_list[i] is None:
            continue
        k = prev_k + (rsv_list[i] - prev_k) / k_smooth
        d = prev_d + (k - prev_d) / d_smooth
        k_list[i] = k
        d_list[i] = d
        prev_k, prev_d = k, d

    return [{"date": ohlc[i]["date"], "k": k_list[i], "d": d_list[i]} for i in range(n)]


def compute_ema(values, period):
    """回傳跟 values 等長的 EMA 序列，前面資料不足處用簡單平均遞推 (第一筆 EMA = 第一筆值)。"""
    ema = []
    k = 2 / (period + 1)
    prev = None
    for v in values:
        if prev is None:
            prev = v
        else:
            prev = v * k + prev * (1 - k)
        ema.append(prev)
    return ema


def compute_macd(ohlc, fast=12, slow=26, signal=9):
    """標準 MACD (12,26,9)。回傳 [{date, dif, dea, hist}]。"""
    closes = [r["close"] for r in ohlc]
    ema_fast = compute_ema(closes, fast)
    ema_slow = compute_ema(closes, slow)
    dif = [f - s for f, s in zip(ema_fast, ema_slow)]
    dea = compute_ema(dif, signal)
    hist = [d - e for d, e in zip(dif, dea)]
    return [{"date": ohlc[i]["date"], "dif": dif[i], "dea": dea[i], "hist": hist[i]} for i in range(len(ohlc))]


# ==========================================
# 3. Cross / Divergence Detection (簡化版，僅供參考)
# ==========================================
def detect_cross(fast_list, slow_list, lookback=1):
    """通用交叉偵測：檢查最近 lookback 天內 fast 是否由下往上(黃金)或由上往下(死亡)穿越 slow。
    回傳 "golden" / "dead" / None。"""
    n = len(fast_list)
    for i in range(n - lookback, n):
        if i <= 0 or fast_list[i] is None or slow_list[i] is None or fast_list[i - 1] is None or slow_list[i - 1] is None:
            continue
        if fast_list[i - 1] <= slow_list[i - 1] and fast_list[i] > slow_list[i]:
            return "golden"
        if fast_list[i - 1] >= slow_list[i - 1] and fast_list[i] < slow_list[i]:
            return "dead"
    return None


def detect_simple_divergence(ohlc, indicator_values, lookback=20):
    """簡化版背離偵測：比較最近 lookback 天內，價格的最高/最低點，跟指標的最高/最低點是否同向。
    回傳 "top_bearish"(價格創高但指標未創高，高檔背離看空) / "bottom_bullish"(價格創低但指標未創低，
    低檔背離看多) / None。此為簡化啟發式判斷，非嚴謹型態辨識，僅供參考，建議人工覆核。"""
    n = len(ohlc)
    if n < lookback:
        return None
    window_price = [r["close"] for r in ohlc[-lookback:]]
    window_ind = [v for v in indicator_values[-lookback:]]
    if any(v is None for v in window_ind):
        return None

    price_max_idx = window_price.index(max(window_price))
    price_min_idx = window_price.index(min(window_price))
    ind_max_idx = window_ind.index(max(window_ind))
    ind_min_idx = window_ind.index(min(window_ind))

    # 價格創高點落在窗口最後幾天，但指標高點出現在更早之前 -> 高檔背離
    if price_max_idx >= lookback - 3 and ind_max_idx < price_max_idx - 2:
        return "top_bearish"
    if price_min_idx >= lookback - 3 and ind_min_idx < price_min_idx - 2:
        return "bottom_bullish"
    return None


# ==========================================
# 4. Margin Balance (TWSE + TPEx 官方 Open API，自行加總)
# ==========================================
def fetch_twse_margin_total(timeout=20, credentials_path=CREDENTIALS_PATH):
    """加總上市個股融資今日/前日餘額 (張)，並透過 FinMind 官方彙總資料集取得金額(元)——
    TWSE 官方 MI_MARGN 本身只給張數，沒有金額欄位。回傳
    {today_balance, prev_balance, change, today_money, prev_money, change_money}
    (money 為元，today_balance/prev_balance/change 仍為張數以供備查)。"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    today_total, prev_total = 0, 0
    for r in data:
        try:
            today_total += int(str(r.get("融資今日餘額", "0")).replace(",", "") or 0)
            prev_total += int(str(r.get("融資前日餘額", "0")).replace(",", "") or 0)
        except ValueError:
            continue

    today_money, prev_money = 0, 0
    try:
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        records = _finmind_request("TaiwanStockTotalMarginPurchaseShortSale", "", start_date, credentials_path)
        money_records = [r for r in records if r.get("name") == "MarginPurchaseMoney"]
        if money_records:
            latest = max(money_records, key=lambda r: r["date"])
            today_money = latest.get("TodayBalance", 0)
            prev_money = latest.get("YesBalance", 0)
    except Exception:
        pass

    return {
        "today_balance": today_total, "prev_balance": prev_total, "change": today_total - prev_total,
        "today_money": today_money, "prev_money": prev_money, "change_money": today_money - prev_money,
    }


def fetch_tpex_margin_total(timeout=20):
    """加總上櫃個股融資餘額 (張)，並估算金額(元)——TPEx官方API同樣只給張數，沒有金額
    欄位，且FinMind的市場彙總資料集(TaiwanStockTotalMarginPurchaseShortSale)實際上只
    涵蓋上市(已於update_prices相關開發階段驗證)，故改用同一批 Fugle 熱力圖(上櫃)的收盤價，
    將個股張數 x 1000股/張 x 收盤價換算後加總估算金額(熱力圖查無收盤價者多為債券ETF等
    非普通股，直接跳過不列入金額加總，僅影響極小部分)。回傳
    {today_balance, prev_balance, change, today_money, prev_money, change_money}。"""
    url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_margin_balance"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    today_total, prev_total = 0, 0
    for r in data:
        try:
            today_total += int(str(r.get("MarginPurchaseBalance", "0")).replace(",", "") or 0)
            prev_total += int(str(r.get("MarginPurchaseBalancePreviousDay", "0")).replace(",", "") or 0)
        except ValueError:
            continue

    today_money, prev_money = 0, 0
    try:
        from sector_trend import fetch_heatmap, TPEX_SYMBOL
        heatmap_rows = fetch_heatmap(TPEX_SYMBOL, period=None)
        price_by_symbol = {
            r['symbol']: r.get('closePrice')
            for r in heatmap_rows if r.get('type') == 'EQUITY' and r.get('closePrice')
        }
        for r in data:
            symbol = r.get("SecuritiesCompanyCode")
            price = price_by_symbol.get(symbol)
            if not price:
                continue
            try:
                today_lots = int(str(r.get("MarginPurchaseBalance", "0")).replace(",", "") or 0)
                prev_lots = int(str(r.get("MarginPurchaseBalancePreviousDay", "0")).replace(",", "") or 0)
            except ValueError:
                continue
            today_money += today_lots * 1000 * price
            prev_money += prev_lots * 1000 * price
    except Exception:
        pass

    return {
        "today_balance": today_total, "prev_balance": prev_total, "change": today_total - prev_total,
        "today_money": today_money, "prev_money": prev_money, "change_money": today_money - prev_money,
    }


def fetch_margin_maintenance_ratio(start_date, credentials_path=CREDENTIALS_PATH):
    """回傳依日期排序的 [{date, ratio}]，來源 FinMind TaiwanTotalExchangeMarginMaintenance。"""
    records = _finmind_request("TaiwanTotalExchangeMarginMaintenance", "", start_date, credentials_path)
    records.sort(key=lambda r: r.get("date", ""))
    return [{"date": r["date"], "ratio": r.get("TotalExchangeMarginMaintenance")} for r in records]


# ==========================================
# 5. 三大法人現貨買賣超 (全市場)
# ==========================================
def fetch_institutional_investors_total(start_date, credentials_path=CREDENTIALS_PATH):
    """回傳最新一天 {date, foreign_net, investment_trust_net, dealer_net, total_net}
    (net = buy - sell，單位元)。"""
    records = _finmind_request("TaiwanStockTotalInstitutionalInvestors", "", start_date, credentials_path)
    if not records:
        return None
    latest_date = max(r["date"] for r in records)
    day_records = {r["name"]: r for r in records if r["date"] == latest_date}

    def net(name):
        r = day_records.get(name)
        return (r["buy"] - r["sell"]) if r else 0

    dealer_net = net("Dealer_self") + net("Dealer_Hedging") + net("Foreign_Dealer_Self")
    return {
        "date": latest_date,
        "foreign_net": net("Foreign_Investor"),
        "investment_trust_net": net("Investment_Trust"),
        "dealer_net": dealer_net,
        "total_net": net("total"),
    }


# ==========================================
# 6. 外資台指期未平倉
# ==========================================
def fetch_foreign_futures_position(start_date, futures_id="TX", credentials_path=CREDENTIALS_PATH):
    """回傳依日期排序的 [{date, long_oi, short_oi, net_oi}] (僅外資，futures_id 預設台指期 TX)。"""
    records = _finmind_request("TaiwanFuturesInstitutionalInvestors", futures_id, start_date, credentials_path)
    foreign_records = [r for r in records if r.get("institutional_investors") == "外資"]
    foreign_records.sort(key=lambda r: r.get("date", ""))
    out = []
    for r in foreign_records:
        long_oi = r.get("long_open_interest_balance_volume", 0)
        short_oi = r.get("short_open_interest_balance_volume", 0)
        out.append({"date": r["date"], "long_oi": long_oi, "short_oi": short_oi, "net_oi": long_oi - short_oi})
    return out
