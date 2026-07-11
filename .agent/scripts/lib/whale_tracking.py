"""
大戶持股追蹤共用模組。

資料來源是使用者每日手動取得的大戶(重要投資人)券商庫存截圖/PDF，經視覺辨識萃取為
結構化快照後，寫入 .agent/data/whale_positions.csv 這份時間序列資料表——這類資料是
「多大戶 x 多股票 x 每日」的結構化數字，用 Markdown 筆記儲存無法有效查詢/疊加，
因此獨立於 10_Stocks/20_Garden 之外，用 CSV 存放。

分層原則：
- load_positions / append_snapshot : 純資料存取 (讀寫 whale_positions.csv)
- compute_position_deltas : 純計算，比較某大戶兩個日期之間的部位變化 (新增/加碼/減碼/出清)
- get_consensus_stocks : 純計算，找出當天被 N 位以上大戶同時持有的股票
- generate_summary_markdown : 格式化，把上述計算結果轉成人類可讀的彙總筆記
"""
import csv
import os
from collections import defaultdict

DATA_PATH = r"C:\Users\User\Desktop\LucasBrain\.agent\data\whale_positions.csv"
SUMMARY_NOTE_PATH = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Whale_Tracking\大戶籌碼追蹤.md"

FIELDS = [
    "date", "whale_id", "ticker", "name", "position_type",
    "shares", "cost_price", "market_price", "cost_basis",
    "market_value", "unrealized_pnl", "pnl_pct",
]


def load_positions(data_path=DATA_PATH):
    """讀取全部歷史快照，回傳 list of dict。"""
    if not os.path.exists(data_path):
        return []
    with open(data_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            for key in ("shares", "cost_price", "market_price", "cost_basis",
                        "market_value", "unrealized_pnl", "pnl_pct"):
                try:
                    row[key] = float(row[key])
                except (ValueError, TypeError):
                    row[key] = 0.0
            rows.append(row)
        return rows


def append_snapshot(snapshot_rows, data_path=DATA_PATH):
    """把一天份的快照 rows (list of dict，需含 FIELDS 全部欄位) 附加進主表。
    若同一 (date, whale_id, ticker, position_type) 已存在，視為重跑同一天，直接跳過重複列。
    """
    existing = load_positions(data_path)
    existing_keys = {
        (r["date"], r["whale_id"], r["ticker"], r["position_type"]) for r in existing
    }

    new_rows = []
    skipped = 0
    for row in snapshot_rows:
        key = (row["date"], row["whale_id"], row["ticker"], row["position_type"])
        if key in existing_keys:
            skipped += 1
            continue
        new_rows.append(row)
        existing_keys.add(key)

    file_exists = os.path.exists(data_path)
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    with open(data_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        for row in new_rows:
            writer.writerow(row)

    return len(new_rows), skipped


def get_dates(data_path=DATA_PATH):
    """回傳資料表中所有出現過的日期，由新到舊排序。"""
    rows = load_positions(data_path)
    return sorted({r["date"] for r in rows}, reverse=True)


def get_snapshot(date, data_path=DATA_PATH):
    """回傳指定日期的所有快照 rows。"""
    return [r for r in load_positions(data_path) if r["date"] == date]


def compute_position_deltas(whale_id, current_date, data_path=DATA_PATH):
    """比較某大戶在 current_date 與其前一筆快照日期之間的部位變化。
    回傳 {new: [...], increased: [...], decreased: [...], closed: [...], unchanged: [...],
          total_value_now, total_value_prev, prev_date}。
    若找不到更早的快照，prev_date 為 None，只回傳 new 部位（無從比較加減碼）。
    """
    # 只看這位大戶自己實際回報過的日期，不能用全體大戶的日期聯集——否則會誤把「其他
    # 大戶存在、但這位大戶根本沒有資料」的日期當成比較基準，算出假的 0 -> 100% 變化。
    whale_dates = sorted({r["date"] for r in load_positions(data_path) if r["whale_id"] == whale_id}, reverse=True)
    prior_dates = [d for d in whale_dates if d < current_date]
    prev_date = prior_dates[0] if prior_dates else None

    current_rows = [r for r in get_snapshot(current_date, data_path) if r["whale_id"] == whale_id]
    current_by_ticker = defaultdict(lambda: {"shares": 0.0, "market_value": 0.0, "name": ""})
    for r in current_rows:
        current_by_ticker[r["ticker"]]["shares"] += r["shares"]
        current_by_ticker[r["ticker"]]["market_value"] += r["market_value"]
        current_by_ticker[r["ticker"]]["name"] = r["name"]

    total_value_now = sum(v["market_value"] for v in current_by_ticker.values())

    if not prev_date:
        return {
            "new": [{"ticker": t, **v} for t, v in current_by_ticker.items()],
            "increased": [], "decreased": [], "closed": [], "unchanged": [],
            "total_value_now": total_value_now, "total_value_prev": None, "prev_date": None,
        }

    prev_rows = [r for r in get_snapshot(prev_date, data_path) if r["whale_id"] == whale_id]
    prev_by_ticker = defaultdict(lambda: {"shares": 0.0, "market_value": 0.0, "name": ""})
    for r in prev_rows:
        prev_by_ticker[r["ticker"]]["shares"] += r["shares"]
        prev_by_ticker[r["ticker"]]["market_value"] += r["market_value"]
        prev_by_ticker[r["ticker"]]["name"] = r["name"]

    total_value_prev = sum(v["market_value"] for v in prev_by_ticker.values())

    new, increased, decreased, closed, unchanged = [], [], [], [], []
    all_tickers = set(current_by_ticker) | set(prev_by_ticker)
    for t in all_tickers:
        cur = current_by_ticker.get(t)
        prev = prev_by_ticker.get(t)
        if cur and not prev:
            new.append({"ticker": t, **cur})
        elif prev and not cur:
            closed.append({"ticker": t, **prev})
        else:
            diff = cur["shares"] - prev["shares"]
            entry = {"ticker": t, "name": cur["name"], "shares": cur["shares"],
                     "shares_prev": prev["shares"], "shares_delta": diff,
                     "market_value": cur["market_value"]}
            if diff > 0:
                increased.append(entry)
            elif diff < 0:
                decreased.append(entry)
            else:
                unchanged.append(entry)

    return {
        "new": new, "increased": increased, "decreased": decreased,
        "closed": closed, "unchanged": unchanged,
        "total_value_now": total_value_now, "total_value_prev": total_value_prev,
        "prev_date": prev_date,
    }


def get_consensus_stocks(date, min_whales=2, data_path=DATA_PATH):
    """找出指定日期被 min_whales 位以上大戶同時持有的股票，按持有大戶數排序。
    回傳 [{ticker, name, whale_count, whale_ids, total_shares, total_market_value}]。
    嚴格要求同一天有資料——若大戶回報日期不同步，請改用 get_consensus_stocks_latest()。
    """
    rows = get_snapshot(date, data_path)
    return _aggregate_consensus(rows, min_whales)


def get_latest_snapshot_per_whale(data_path=DATA_PATH):
    """每位大戶回報資料的日期不一定同步（例如現股/融資帳戶跟股票期貨帳戶常常不同天更新），
    此函式取每位大戶「各自最新一次」的快照 rows 合併回傳，讓共識分析不受回報日期落差影響。"""
    rows = load_positions(data_path)
    latest_date_by_whale = {}
    for r in rows:
        w = r["whale_id"]
        if w not in latest_date_by_whale or r["date"] > latest_date_by_whale[w]:
            latest_date_by_whale[w] = r["date"]
    return [r for r in rows if r["date"] == latest_date_by_whale.get(r["whale_id"])], latest_date_by_whale


def get_consensus_stocks_latest(min_whales=2, data_path=DATA_PATH):
    """跟 get_consensus_stocks() 相同，但取每位大戶各自最新一筆快照做比對，不要求同一天。
    回傳值額外附上 whale_dates，標示每位大戶的資料實際來自哪一天。"""
    rows, latest_date_by_whale = get_latest_snapshot_per_whale(data_path)
    consensus = _aggregate_consensus(rows, min_whales)
    for c in consensus:
        c["whale_dates"] = {w: latest_date_by_whale[w] for w in c["whale_ids"]}
    return consensus, latest_date_by_whale


def _aggregate_consensus(rows, min_whales):
    by_ticker = defaultdict(lambda: {"whales": set(), "shares": 0.0, "market_value": 0.0, "name": ""})
    for r in rows:
        entry = by_ticker[r["ticker"]]
        entry["whales"].add(r["whale_id"])
        entry["shares"] += r["shares"]
        entry["market_value"] += r["market_value"]
        entry["name"] = r["name"]

    consensus = [
        {
            "ticker": t, "name": v["name"], "whale_count": len(v["whales"]),
            "whale_ids": sorted(v["whales"]), "total_shares": v["shares"],
            "total_market_value": v["market_value"],
        }
        for t, v in by_ticker.items() if len(v["whales"]) >= min_whales
    ]
    consensus.sort(key=lambda x: (-x["whale_count"], -x["total_market_value"]))
    return consensus


def get_whale_positions_for_ticker(ticker, data_path=DATA_PATH):
    """給 StockReport 等其他報告呼叫：回傳目前追蹤的大戶中，最新一天有誰持有這檔股票。"""
    dates = get_dates(data_path)
    if not dates:
        return []
    latest = dates[0]
    rows = [r for r in get_snapshot(latest, data_path) if r["ticker"] == ticker]
    by_whale = defaultdict(lambda: {"shares": 0.0, "market_value": 0.0})
    for r in rows:
        by_whale[r["whale_id"]]["shares"] += r["shares"]
        by_whale[r["whale_id"]]["market_value"] += r["market_value"]
    return [{"whale_id": w, "date": latest, **v} for w, v in by_whale.items()]
