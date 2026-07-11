"""
更新大戶持股追蹤。

用法：
    python track_whale_positions.py <YYYY-MM-DD> <snapshot_input.csv>

snapshot_input.csv 需含欄位：whale_id, ticker, name, position_type, shares,
cost_price, market_price, cost_basis, market_value, unrealized_pnl, pnl_pct
（date 欄位由本腳本自動補上，不需在輸入檔中提供）

執行內容：
1. 將輸入快照併入 .agent/data/whale_positions.csv（主表，全歷史）。
2. 對每位大戶計算與前一次快照的部位變化（新增/加碼/減碼/出清）。
3. 計算當天的共識標的（預設 2 位以上大戶同時持有）。
4. 重新產生 30_Projects/Whale_Tracking/大戶籌碼追蹤.md 彙總筆記。
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.whale_tracking import (
    append_snapshot,
    compute_position_deltas,
    get_consensus_stocks_latest,
    get_dates,
    DATA_PATH,
    SUMMARY_NOTE_PATH,
    FIELDS,
)

CONSENSUS_MIN_WHALES = 2


def read_input_snapshot(input_path, date):
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            row["date"] = date
            rows.append({k: row.get(k, "") for k in FIELDS})
        return rows


def format_money(v):
    return f"{v:,.0f}"


def generate_summary_markdown(as_of_date):
    lines = []
    lines.append("---")
    lines.append("type: industry")
    lines.append('title: "大戶籌碼追蹤"')
    lines.append(f"updated: {as_of_date}")
    lines.append("tags: [chip-tracking, whale-positions]")
    lines.append('source_type: "manual_snapshot"')
    lines.append("---")
    lines.append("")
    lines.append("# 大戶籌碼追蹤")
    lines.append("")
    lines.append("> [!NOTE]")
    lines.append(f"> 資料來源：使用者每日手動取得追蹤中大戶的券商庫存截圖，經視覺辨識萃取。大戶身分以匿名代號標示（大戶A、大戶B...），非公開資訊，僅供自身投資決策參考。各大戶回報日期可能不同步（現股/融資帳戶與股票期貨帳戶常非同一天更新），下方共識分析一律採用「每位大戶各自最新一筆」資料，並標示其實際資料日期。最後更新：**{as_of_date}**。")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Consensus stocks (取每位大戶各自最新一筆，不要求同一天)
    consensus, whale_dates = get_consensus_stocks_latest(min_whales=CONSENSUS_MIN_WHALES)
    lines.append(f"## 共識標的（{CONSENSUS_MIN_WHALES} 位以上大戶同時持有，各取最新資料）")
    lines.append("")
    if consensus:
        lines.append("| 股票 | 持有大戶數 | 持有大戶 (資料日期) | 合計股數 | 合計市值 (元) |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for c in consensus:
            whale_labels = "、".join(f"{w}({c['whale_dates'][w]})" for w in c["whale_ids"])
            lines.append(
                f"| {c['ticker']} {c['name']} | {c['whale_count']} | {whale_labels} | "
                f"{format_money(c['total_shares'])} | {format_money(c['total_market_value'])} |"
            )
    else:
        lines.append("*目前沒有符合門檻的共識標的。*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 2. Per-whale summary — 顯示系統中所有已知大戶（各自最新一筆），非僅本次輸入的批次
    lines.append("## 各大戶部位總覽")
    lines.append("")
    for whale_id in sorted(whale_dates.keys()):
        whale_date = whale_dates[whale_id]
        delta = compute_position_deltas(whale_id, whale_date)
        lines.append(f"### {whale_id} (資料日期：{whale_date})")
        if delta["prev_date"]:
            change = delta["total_value_now"] - delta["total_value_prev"]
            change_pct = (change / delta["total_value_prev"] * 100) if delta["total_value_prev"] else 0
            lines.append(
                f"* **總市值**：{format_money(delta['total_value_now'])} 元 "
                f"(較 {delta['prev_date']}：{change:+,.0f} 元，{change_pct:+.2f}%)"
            )
        else:
            lines.append(f"* **總市值**：{format_money(delta['total_value_now'])} 元 (首次建立基準，尚無比較對象)")

        if delta["new"]:
            items = "、".join(f"{i['ticker']}{i['name']}" for i in delta["new"])
            lines.append(f"* **新增部位**：{items}")
        if delta["increased"]:
            items = "、".join(f"{i['ticker']}{i['name']}(+{i['shares_delta']:,.0f}股)" for i in delta["increased"])
            lines.append(f"* **加碼**：{items}")
        if delta["decreased"]:
            items = "、".join(f"{i['ticker']}{i['name']}({i['shares_delta']:,.0f}股)" for i in delta["decreased"])
            lines.append(f"* **減碼**：{items}")
        if delta["closed"]:
            items = "、".join(f"{i['ticker']}{i['name']}" for i in delta["closed"])
            lines.append(f"* **出清**：{items}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 歷史快照日期")
    lines.append("")
    all_dates = get_dates()
    lines.append("、".join(all_dates) if all_dates else "*尚無資料*")
    lines.append("")

    os.makedirs(os.path.dirname(SUMMARY_NOTE_PATH), exist_ok=True)
    with open(SUMMARY_NOTE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    if len(sys.argv) < 3:
        print("Usage: python track_whale_positions.py <YYYY-MM-DD> <snapshot_input.csv>")
        sys.exit(1)
    date = sys.argv[1].strip()
    input_path = sys.argv[2].strip()

    rows = read_input_snapshot(input_path, date)
    if not rows:
        print(f"No rows found in {input_path}.")
        sys.exit(1)

    added, skipped = append_snapshot(rows, DATA_PATH)
    print(f"Appended {added} rows to {DATA_PATH} ({skipped} duplicates skipped).")

    generate_summary_markdown(date)
    print(f"Updated summary note at {SUMMARY_NOTE_PATH}")

    consensus, whale_dates = get_consensus_stocks_latest(min_whales=CONSENSUS_MIN_WHALES)
    print(f"\nConsensus stocks ({CONSENSUS_MIN_WHALES}+ whales, each whale's latest snapshot):")
    for c in consensus:
        labels = ", ".join(f"{w}@{c['whale_dates'][w]}" for w in c["whale_ids"])
        print(f"  {c['ticker']} {c['name']}: {c['whale_count']} whales ({labels})")


if __name__ == "__main__":
    main()
