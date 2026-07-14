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
MARKET_SCORE_BASE = 80  # 讀取失敗時的備援預設值，正常情況下由 load_market_score_settings() 覆蓋
MARKET_SCORE_SETTINGS_PATH = r"C:\Users\User\Desktop\LucasBrain\97_Settings\大盤分數計算方式.md"

# 漲跌停判定容忍值：台股現制漲跌幅限制為10%，用9.5%緩衝涵蓋零股捨入誤差，非精確鎖死判定
LIMIT_MOVE_THRESHOLD_PCT = 9.5


def _split_table_row(line):
    """依 | 切欄，但保護 [[頁面|別名]] wikilink 內部的 |。與 financial_screen.py 內同名函式
    邏輯相同，這裡自帶一份副本是為了避免 market_data.py 既有的 sys.path 插入方式與
    financial_screen.py 內部 relative import 互相打架（見開發記錄：兩者匯入慣例不同，
    market_data.py 用裸式 import 直接讀 lib/ 目錄下的模組，financial_screen.py 則假設自己
    是以 lib.financial_screen 套件形式載入，混用會觸發 ImportError）。"""
    protected = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', lambda m: f'[[{m.group(1)}\x00{m.group(2)}]]', line)
    return [c.replace('\x00', '|') for c in protected.split('|')]


def _parse_markdown_table(lines, header_predicate):
    """從整份 markdown 中找出所有符合 header_predicate 的表格，回傳資料列清單。副本說明同上。"""
    rows = []
    header = None
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('|'):
            header = None
            continue
        cols = [c.strip() for c in _split_table_row(stripped)[1:-1]]
        if header is None:
            if header_predicate(cols):
                header = cols
            continue
        if all(c.startswith(':') or set(c) <= {':', '-'} for c in cols):
            continue
        rows.append(dict(zip(header, cols)))
    return rows


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
    """回傳依日期排序的 [{date, ratio}]，來源 FinMind TaiwanTotalExchangeMarginMaintenance。
    已由 fetch_margin_maintenance_ratio_macromicro() 取代為 generate_daily_report.py 的實際來源
    (2026-07-13)，本函式保留供對照/回退使用。"""
    records = _finmind_request("TaiwanTotalExchangeMarginMaintenance", "", start_date, credentials_path)
    records.sort(key=lambda r: r.get("date", ""))
    return [{"date": r["date"], "ratio": r.get("TotalExchangeMarginMaintenance")} for r in records]


def fetch_margin_maintenance_ratio_macromicro(start_date=None, credentials_path=CREDENTIALS_PATH, timeout=15):
    """回傳依日期排序的 [{date, ratio}]，來源 MacroMicro 圖表 53117（台灣大盤融資維持率）。

    數值四捨五入至小數點後1位（macromicro_token 使用者指定的精度）。start_date 僅用於回傳前
    的客戶端篩選，MacroMicro 這支 API 本身不接受日期範圍參數，每次呼叫回傳其預設區間。

    需要 credentials.json 內的 macromicro_token —— 這是從瀏覽器登入後的網路請求截取出來的
    session token，不是官方公開發行的長期 API key，可能會過期。過期時這裡會拋出
    HTTPError(401/403) 或 KeyError，須回瀏覽器登入 macromicro.me 重新截取
    (F12 > Network > 找 charts/data/53117 請求 > 複製 authorization header 的 Bearer 值)
    後更新 credentials.json 的 macromicro_token 欄位。"""
    with open(credentials_path, 'r', encoding='utf-8') as cf:
        token = json.load(cf).get("macromicro_token")
    if not token:
        raise RuntimeError("credentials.json 缺少 macromicro_token")

    url = "https://www.macromicro.me/charts/data/53117"
    body = json.dumps({"ignoredCharts": [], "limitedCharts": [53117]}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.macromicro.me/charts/53117/taiwan-taiex-maintenance-margin",
        "Origin": "https://www.macromicro.me",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        res_data = json.loads(response.read().decode("utf-8"))

    series = res_data["data"]["c:53117"]["series"][0]  # [[date, value], ...]；index 0 = 維持率, index 1 = 加權指數
    out = [{"date": d, "ratio": round(float(v), 1)} for d, v in series]
    out.sort(key=lambda r: r["date"])
    if start_date:
        out = [r for r in out if r["date"] >= start_date]
    return out


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


# ==========================================
# 7. 大盤分數 (綜合漲跌/乖離/均線/動能/成交量/籌碼六大類的簡化評分)
# ==========================================
def load_market_score_settings(settings_path=MARKET_SCORE_SETTINGS_PATH):
    """讀取 97_Settings/大盤分數計算方式.md，回傳 {"points": {規則代號: 配分}（僅含啟用=Y的規則），
    "base": 基準分數, "tier_weak": 弱勢門檻, "tier_strong": 強勢門檻, "tier_super": 超級強勢門檻}。
    讀取失敗或缺列時個別退回程式內建預設值，確保報告仍可正常產生。"""
    settings = {"points": {}, "base": MARKET_SCORE_BASE, "tier_weak": 40, "tier_strong": 70, "tier_super": 80}
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
    except Exception as e:
        print(f"Warning: Failed to read market score settings: {e}")
        return settings

    rows = _parse_markdown_table(lines, lambda cols: cols[:3] == ['啟用', '分類', '規則說明'])
    for r in rows:
        if r.get('啟用', '').strip().upper() != 'Y':
            continue
        key = r.get('規則代號', '').replace('`', '').strip()
        if not key:
            continue
        try:
            settings["points"][key] = float(r.get('配分', ''))
        except ValueError:
            continue

    tier_rows = _parse_markdown_table(lines, lambda cols: cols[:2] == ['設定項', '目前值'])
    tier_map = {
        '基準分數': 'base', '弱勢門檻（<=此值）': 'tier_weak',
        '強勢門檻（>=此值）': 'tier_strong', '超級強勢門檻（>此值）': 'tier_super',
    }
    for r in tier_rows:
        key = tier_map.get(r.get('設定項', '').strip())
        if not key:
            continue
        try:
            settings[key] = float(r.get('目前值', '')) if key == 'base' else int(r.get('目前值', ''))
        except ValueError:
            continue

    return settings


def compute_market_score(index_summary, stats_summary, settings=None):
    """依 index_summary(單一指數的漲跌%/均線/乖離/KD·MACD方向與背離/成交量趨勢與均量位置)
    與 stats_summary(融資維持率) 逐項加減分，配分數字讀自 `[[大盤分數計算方式]]`
    （settings=None 時自動呼叫 load_market_score_settings() 讀取，呼叫端也可自行載入一次
    後傳入以避免重複讀檔）。條件判定的門檻數字（跌幅2%/5%、乖離率5%、維持率170/175/155%等）
    暫時仍寫在程式邏輯裡，只有「是否啟用」與「配分」讀自設定檔。
    stats_summary 除了原本的 margin_maintenance_ratio，還可帶入 db_above_ma20_pct（資料庫
    個股月線以上家數百分比）、market_up/market_down（全市場漲跌家數）、
    institutional_total_net（三大法人現貨合計買賣超）、futures_short_oi_change（外資台指期
    空單較前日增減）——缺任一鍵時該條規則自動略過，不影響其餘規則計算。
    另有兩條補充規則：跌幅<1%且成交量縮；5MA乖離率介於-1.5%~0%之間（現價跌破5日線但缺口
    不到1.5%，代表只要反彈1.5%就足以站上5日線，是「隨時可能收復」的訊號，並非要求當天已
    實際上漲1.5%）。
    回傳 (score, reasons, notes)：reasons 為 [(說明文字, 分數增減)] 依檢查順序排列（配分為0
    或規則被停用時不列入）；notes 為觸發到「其他規則」兩條補充規則時，各自附帶的一句白話
    解讀文字列表。"""
    if settings is None:
        settings = load_market_score_settings()
    points = settings["points"]
    score = settings.get("base", MARKET_SCORE_BASE)
    reasons = []
    notes = []

    def apply(rule_key, text):
        delta = points.get(rule_key)
        if not delta:
            return
        nonlocal score
        score += delta
        reasons.append((text, delta))

    change_pct = index_summary.get("change_pct")
    if change_pct is not None and change_pct < 0:
        decline = abs(change_pct)
        if decline >= 5:
            apply("decline_ge5", f"跌幅 {decline:.2f}%（>=5%）")
        elif decline >= 2:
            apply("decline_2to5", f"跌幅 {decline:.2f}%（2%~5%）")
        else:
            apply("decline_lt2", f"跌幅 {decline:.2f}%（<2%）")

    bias5 = (index_summary.get("bias") or {}).get(5)
    if bias5 is not None:
        if bias5 > 5:
            apply("bias5_high", f"5MA乖離率 {bias5:+.2f}%（>5%）")
        elif bias5 < -5:
            apply("bias5_low", f"5MA乖離率 {bias5:+.2f}%（<-5%）")

    ma = index_summary.get("ma") or {}
    for period, key_down, key_break in ((5, "ma5_down", "ma5_break"), (20, "ma20_down", "ma20_break"), (60, "ma60_down", "ma60_break")):
        m = ma.get(period)
        if not m or m.get("val") is None:
            continue
        if m.get("slope") == "下彎":
            apply(key_down, f"{period}MA下彎")
        if m.get("close_vs_ma") == "跌破":
            apply(key_break, f"{period}MA跌破")
    for period, key_up in ((20, "ma20_up"), (60, "ma60_up")):
        m = ma.get(period)
        if m and m.get("slope") == "上彎":
            apply(key_up, f"{period}MA上彎")

    if index_summary.get("kd_direction") == "交叉往下":
        apply("kd_cross_down", "KD交叉往下")
    if index_summary.get("macd_direction") == "交叉往下":
        apply("macd_cross_down", "MACD交叉往下")
    if index_summary.get("kd_divergence") == "top_bearish":
        apply("kd_top_bearish", "KD高檔背離")
    if index_summary.get("macd_divergence") == "top_bearish":
        apply("macd_top_bearish", "MACD高檔背離")

    vol_trend = index_summary.get("vol_trend")
    if change_pct is not None and vol_trend == "量增":
        if change_pct < 0:
            apply("vol_up_decline", "指數下跌且成交量增")
        else:
            apply("vol_up_rise", "指數上漲且成交量增")
    vol_ma = index_summary.get("vol_ma") or {}
    if vol_ma.get("position") == "跌破":
        apply("vol_break_5ma", "成交量跌破五日均量線")

    # 其他規則
    if change_pct is not None and change_pct < 0 and abs(change_pct) < 1 and vol_trend == "量縮":
        apply("small_decline_vol_shrink", f"跌幅 {abs(change_pct):.2f}%（<1%）且成交量縮")
        if "small_decline_vol_shrink" in points and points["small_decline_vol_shrink"]:
            notes.append("下跌 < 1% 且 成交量縮，尚未恐慌")

    if bias5 is not None and -1.5 <= bias5 < 0:
        apply("bias5_near_zero", f"5MA乖離率 {bias5:+.2f}%（現價距5日線不到1.5%，上漲1.5%即可站上）")
        if "bias5_near_zero" in points and points["bias5_near_zero"]:
            notes.append("若上漲 1.5% 就可以漲超過五日線，可觀察震盪狀況，看是否很快站回")

    ratio = stats_summary.get("margin_maintenance_ratio")
    if ratio is not None:
        if ratio > 170:
            apply("margin_high", f"融資維持率 {ratio:.2f}%（>170%）")
        if ratio > 175:
            apply("margin_high2", f"融資維持率 {ratio:.2f}%（>175%）")
        if ratio < 155:
            apply("margin_low", f"融資維持率 {ratio:.2f}%（<155%）")

    db_above_ma20_pct = stats_summary.get("db_above_ma20_pct")
    if db_above_ma20_pct is not None and db_above_ma20_pct < 50:
        apply("db_ma20_below_half", f"資料庫個股月線以上家數 {db_above_ma20_pct:.0f}%（<50%）")

    market_up = stats_summary.get("market_up")
    market_down = stats_summary.get("market_down")
    if market_up is not None and market_down is not None and market_down > market_up:
        apply("market_decliners_more", "下跌家數 > 上漲家數")

    inst_total_net = stats_summary.get("institutional_total_net")
    futures_short_change = stats_summary.get("futures_short_oi_change")
    if inst_total_net is not None and inst_total_net < 0 and futures_short_change is not None and futures_short_change > 0:
        apply("inst_sell_and_short_up", "三大法人賣超 且 外資期貨空單增加")

    return score, reasons, notes


# ==========================================
# 8. 市場寬度 (全市場上漲/下跌/漲停/跌停家數)
# ==========================================
def fetch_market_breadth(date, credentials_path=CREDENTIALS_PATH):
    """回傳當日全市場(上市+上櫃合計，以4碼純數字代號近似排除ETF/權證/受益憑證等非普通股)
    {up, down, flat, limit_up, limit_down, total} 家數統計。用 FinMind 批次查詢
    (data_id="") 一次取得全市場當日價格，比逐檔查詢省下上千次 API 呼叫。
    漲跌停以當日漲跌幅 >= +9.5% / <= -9.5% 近似判定（見 LIMIT_MOVE_THRESHOLD_PCT 註解）。"""
    records = _finmind_request("TaiwanStockPrice", "", date, credentials_path)
    up = down = flat = limit_up = limit_down = 0
    for r in records:
        stock_id = r.get("stock_id", "")
        if not re.fullmatch(r"\d{4}", stock_id):
            continue
        spread = r.get("spread")
        close = r.get("close")
        if spread is None or close is None:
            continue
        if spread > 0:
            up += 1
        elif spread < 0:
            down += 1
        else:
            flat += 1
        prev_close = close - spread
        if prev_close:
            pct = spread / prev_close * 100
            if pct >= LIMIT_MOVE_THRESHOLD_PCT:
                limit_up += 1
            elif pct <= -LIMIT_MOVE_THRESHOLD_PCT:
                limit_down += 1
    return {"up": up, "down": down, "flat": flat, "limit_up": limit_up, "limit_down": limit_down, "total": up + down + flat}
