"""
個股融資維持率估算模組 (加權平均成本法)。

⚠️ 重要限制：TWSE/TPEx 不公開個股層級的融資維持率——維持率是券商依「各帳戶實際融資
成本」計算的帳戶級指標，不是公開資料。這裡改用「加權平均成本法」，從近 N 年逐日融資
買進/賣出/現金償還流量反推整體平均融資成本，屬於估算值，不代表任何真實帳戶的實際
維持率，僅供排序參考。

估算方法：
1. 回溯期開始日的融資餘額（不知道真實成本），用當天收盤價當作假設成本起點——這是模型
   最大的弱點來源，起始餘額占目前餘額比例越高，估算誤差通常越大。
2. 之後每個交易日：融資買進 → 用當天收盤價 × 融資成數增加融資金額；融資賣出/現金償還
   → 依「目前加權平均成本」按比例減少融資金額（移動平均法，不是先進先出）。
3. 融資金額（分母）+ 現價 × 目前融資餘額（分子）→ 估算維持率。
4. 用「重建出的融資股數」跟「TWSE/TPEx 官方回報的今日餘額」比對差異百分比，作為資料
   品質指標——差異越大，代表回溯期內可能有減資/股票股利/企業合併等公司行動，這些會讓
   官方餘額股數跳動但不會反映在買賣流量欄位裡，此時估算不可信。

分層原則：
- fetch_* : 純資料抓取 (FinMind 個股融資買賣餘額、股價、上市/上櫃別)
- compute_* : 純計算 (加權平均成本重建、維持率、資料品質指標)
"""
from datetime import datetime, timedelta

from .financial_screen import _finmind_request_with_retry

LOOKBACK_YEARS = 2   # 實測對過4764/2303後選定：融資部位通常不會抱超過2年，且窗口越短、
                      # 起始未知成本餘額占比越小，重建誤差通常也越低（詳見開發過程的窗口長度比較）
FINANCING_RATIO_TWSE = 0.6   # 上市股票標準融資成數
FINANCING_RATIO_TPEX = 0.5   # 上櫃股票標準融資成數
# 注意：個別股票若被列為注意股/處置股，融資成數可能被交易所臨時調降或暫停融資，
# 本模型未區分這種情況，一律套用市場標準成數，屬於已知簡化假設。


def fetch_margin_flow(ticker, start_date):
    """回傳依日期排序的逐日融資買賣流量紀錄 (FinMind TaiwanStockMarginPurchaseShortSale)。"""
    records = _finmind_request_with_retry("TaiwanStockMarginPurchaseShortSale", ticker, start_date)
    records.sort(key=lambda r: r.get("date", ""))
    return records


def fetch_price_history_by_date(ticker, start_date):
    """回傳 {date: close} 對照表 (FinMind TaiwanStockPrice)。"""
    records = _finmind_request_with_retry("TaiwanStockPrice", ticker, start_date)
    return {r["date"]: r["close"] for r in records if r.get("close") is not None}


def fetch_market_type_map():
    """一次批次查詢回傳 {stock_id: 'twse'|'tpex'} 全市場對照表，供融資成數判斷使用。
    比逐檔查詢省下上百次 API 呼叫 (TaiwanStockInfo data_id="" 回傳全市場資料)。"""
    records = _finmind_request_with_retry("TaiwanStockInfo", "", "2020-01-01")
    type_map = {}
    for r in records:
        sid = r.get("stock_id")
        t = r.get("type")
        if sid and t in ("twse", "tpex"):
            type_map[sid] = t
    return type_map


def compute_margin_maintenance(ticker, market_type=None, lookback_years=LOOKBACK_YEARS):
    """回傳單一個股的融資維持率估算 dict，資料不足時回傳 None：
    {ticker, ratio, financed_amount, collateral_value, avg_cost,
     reconstructed_shares, reported_shares, share_diff_pct, latest_date, latest_close,
     market_type, financing_ratio}
    market_type: 'twse' 或 'tpex'，None 時預設 'twse'（融資成數 60%）。
    """
    financing_ratio = FINANCING_RATIO_TPEX if market_type == "tpex" else FINANCING_RATIO_TWSE

    start_date = (datetime.now() - timedelta(days=lookback_years * 365)).strftime("%Y-%m-%d")
    margin = fetch_margin_flow(ticker, start_date)
    if not margin:
        return None
    price_by_date = fetch_price_history_by_date(ticker, start_date)
    if not price_by_date:
        return None

    # 起始日若剛好沒有收盤價 (停牌/未上市)，往後找第一個有價格的交易日當假設成本基準
    first_close = None
    for r in margin:
        c = price_by_date.get(r["date"])
        if c is not None:
            first_close = c
            break
    if first_close is None:
        return None

    total_shares = (margin[0].get("MarginPurchaseYesterdayBalance") or 0) * 1000
    total_financed = total_shares * first_close * financing_ratio

    for r in margin:
        d = r["date"]
        close = price_by_date.get(d)
        buy = (r.get("MarginPurchaseBuy") or 0) * 1000
        sell = (r.get("MarginPurchaseSell") or 0) * 1000
        repay = (r.get("MarginPurchaseCashRepayment") or 0) * 1000
        reduce_shares = sell + repay

        if buy > 0 and close is not None:
            total_shares += buy
            total_financed += buy * close * financing_ratio

        if reduce_shares > 0 and total_shares > 0:
            avg_cost_per_share = total_financed / total_shares
            actual_reduce = min(reduce_shares, total_shares)
            total_financed -= actual_reduce * avg_cost_per_share
            total_shares -= actual_reduce

    last = margin[-1]
    reported_shares = (last.get("MarginPurchaseTodayBalance") or 0) * 1000
    latest_close = price_by_date.get(last["date"])
    if latest_close is None or total_financed <= 0 or reported_shares <= 0:
        return None

    collateral_value = reported_shares * latest_close
    ratio = collateral_value / total_financed * 100
    avg_cost = (total_financed / total_shares / financing_ratio) if total_shares else None
    share_diff_pct = (total_shares - reported_shares) / reported_shares * 100

    return {
        "ticker": ticker,
        "ratio": ratio,
        "financed_amount": total_financed,
        "collateral_value": collateral_value,
        "avg_cost": avg_cost,
        "reconstructed_shares": total_shares,
        "reported_shares": reported_shares,
        "share_diff_pct": share_diff_pct,
        "latest_date": last["date"],
        "latest_close": latest_close,
        "market_type": market_type or "twse",
        "financing_ratio": financing_ratio,
    }
