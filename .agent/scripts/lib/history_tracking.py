"""族群強度延續性歷史紀錄共用模組。

「二、股票族群情況」每天只看當日/近週漲幅排行，沒有跨日記憶，回答不了「這個族群
是連續第幾天強勢」。本模組把每天的強勢族群寫進 CSV（同日重跑報告時覆蓋當日舊資料，
不會重複累積），並提供「連續上榜天數」的查詢。

動能篩選的延續性不走這裡——Momentum_Screen 每天產出的報告 .md 本身就是逐日留檔的
歷史紀錄，generate_daily_report.build_momentum_section() 直接解析歷次報告檔算分數
變化與連續上榜，不需要另建資料檔。
"""
import csv
import os

DATA_DIR = r"C:\Users\User\Desktop\LucasBrain\.agent\data"
SECTOR_HISTORY_CSV = os.path.join(DATA_DIR, "sector_strength_history.csv")
SECTOR_FIELDNAMES = ["date", "market", "industry", "change_pct"]


def record_daily_rows(csv_path, fieldnames, date_str, rows):
    """把 rows (list[dict]) 寫進 csv。同一 date 的舊資料先移除再寫入，
    因此同一天重跑報告是冪等的，不會造成連續天數誤判。"""
    existing = []
    if os.path.exists(csv_path):
        with open(csv_path, newline='', encoding='utf-8') as f:
            existing = [r for r in csv.DictReader(f) if r.get("date") != date_str]
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in existing:
            writer.writerow(r)
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})


def load_history(csv_path):
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def consecutive_streak(history, key_field, key_value):
    """從最近的紀錄日期往回數，key_value 連續出現在幾個日期中（含最新日期，一斷即停）。
    紀錄天數以「有寫入紀錄的日期」為單位（即交易日），非日曆日。"""
    by_date = {}
    for r in history:
        by_date.setdefault(r["date"], set()).add(r[key_field])
    streak = 0
    for d in sorted(by_date.keys(), reverse=True):
        if key_value in by_date[d]:
            streak += 1
        else:
            break
    return streak


def record_sector_strength(date_str, market_label, industries):
    """寫入某市場(上市/上櫃)當日的強勢族群清單。industries: [{name, change_pct}]。
    只增補該市場的列，同日另一市場已寫入的資料保留。"""
    history = load_history(SECTOR_HISTORY_CSV)
    kept = [r for r in history if not (r["date"] == date_str and r["market"] == market_label)]
    new_rows = kept + [
        {"date": date_str, "market": market_label, "industry": ind["name"],
         "change_pct": f"{ind['change_pct']:.2f}"}
        for ind in industries
    ]
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SECTOR_HISTORY_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=SECTOR_FIELDNAMES)
        writer.writeheader()
        for r in new_rows:
            writer.writerow({k: r.get(k, "") for k in SECTOR_FIELDNAMES})


def sector_streaks(market_label):
    """回傳 {industry: 連續上榜天數}（只計該市場的紀錄）。"""
    history = [r for r in load_history(SECTOR_HISTORY_CSV) if r["market"] == market_label]
    industries = {r["industry"] for r in history}
    return {ind: consecutive_streak(history, "industry", ind) for ind in industries}
