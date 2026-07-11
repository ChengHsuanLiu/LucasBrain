"""
全市場財務指標篩選掃描 (financial_score)。

用法：
    python scan_financial_score.py                  # 掃描全市場 (twse+tpex，約2000檔)
    python scan_financial_score.py --limit 100       # 只掃前100檔 (測試用)
    python scan_financial_score.py --tickers 2330,3443,2454   # 只掃指定個股
    python scan_financial_score.py --min-score 60    # 只保留分數 >= 60 的個股於報告中

規則依據 `40_Library/財務指標篩選機制.md` 的 10 項指標、100 分制配分表，資料來源
FinMind 財報三表 (付費 Backer 方案)。輸出報告至 30_Projects/Financial_Screen/。
"""
import argparse
import io
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.financial_screen import fetch_stock_universe, scan_market
from lib.report_pdf import render_markdown_to_pdf

STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"
OUTPUT_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Financial_Screen"


def get_tracked_tickers():
    """回傳資料庫 10_Stocks/ 現有已追蹤的個股代號集合。"""
    tracked = set()
    for filename in os.listdir(STOCK_DIR):
        if not filename.endswith('.md'):
            continue
        m = re.match(r'^([0-9]+(?:\.[a-zA-Z0-9]+)?)', filename)
        if m:
            tracked.add(m.group(1))
    return tracked


def _fmt_score(v):
    return f"{v:g}"


def build_report(results, tracked_tickers, min_score, universe_size):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = []
    lines.append(f"# 財務指標篩選機制 全市場掃描 ({today})")
    lines.append("")
    lines.append(f"> 依 `[[財務指標篩選機制]]` 10 項指標 100 分制規則，掃描 {universe_size} 檔上市櫃個股"
                  f"（已排除 ETF/ETN/存託憑證/金融保險業）。資料來源：FinMind 財報三表。")
    lines.append("")
    if min_score is not None:
        lines.append(f"> 僅列出總分 >= {min_score} 分的個股，共 {len(results)} 檔。")
    else:
        lines.append(f"> 列出全部 {len(results)} 檔已計算個股，依總分排序。")
    lines.append("")

    complete = [r for r in results if r.get("data_complete")]
    incomplete = [r for r in results if not r.get("data_complete")]
    lines.append(f"> 其中 {len(complete)} 檔史料完整（滿5季，可完整計算全部10項指標），"
                  f"{len(incomplete)} 檔史料不足（新上市/資料不全，僅計算可用指標，配分基準已相應調整不吃虧）。")
    lines.append("")
    lines.append("---")
    lines.append("")

    new_candidates = [r for r in complete if r["ticker"] not in tracked_tickers]
    tracked_scored = [r for r in complete if r["ticker"] in tracked_tickers]

    lines.append(f"## 🆕 新發現標的（不在現有 10_Stocks/ 追蹤清單中，共 {len(new_candidates)} 檔）")
    lines.append("")
    lines.append("| 股票 | 總分 | 最新季度 | 通過指標 |")
    lines.append("| :--- | :--- | :--- | :--- |")
    for r in new_candidates[:50]:
        passed = [b["criterion"] for b in r["breakdown"] if b["points_earned"] > 0]
        lines.append(f"| {r['ticker']} {r.get('name') or ''} | {_fmt_score(r['total_score'])} | {r['latest_quarter']} | {'、'.join(passed)} |")
    if not new_candidates:
        lines.append("| (無) | | | |")
    lines.append("")

    lines.append(f"## 📌 既有追蹤標的財務評分（10_Stocks/ 已收錄，共 {len(tracked_scored)} 檔）")
    lines.append("")
    lines.append("| 股票 | 總分 | 最新季度 | 通過指標 |")
    lines.append("| :--- | :--- | :--- | :--- |")
    for r in tracked_scored:
        passed = [b["criterion"] for b in r["breakdown"] if b["points_earned"] > 0]
        lines.append(f"| {r['ticker']} {r.get('name') or ''} | {_fmt_score(r['total_score'])} | {r['latest_quarter']} | {'、'.join(passed)} |")
    if not tracked_scored:
        lines.append("| (無) | | | |")
    lines.append("")

    if incomplete:
        lines.append(f"## ⚠️ 史料不足個股（{len(incomplete)} 檔，未列入上方排行）")
        lines.append("")
        lines.append("| 股票 | 部分分數 | 最新季度 |")
        lines.append("| :--- | :--- | :--- |")
        for r in incomplete[:30]:
            lines.append(f"| {r['ticker']} {r.get('name') or ''} | {_fmt_score(r['total_score'])}/{_fmt_score(r['max_possible_score'])} | {r.get('latest_quarter') or '無資料'} |")
        if len(incomplete) > 30:
            lines.append(f"| ... 另有 {len(incomplete) - 30} 檔 | | |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📄 原始文件與連結 (Original Documents)")
    lines.append("- 篩選規則定義：`[[財務指標篩選機制]]`")
    lines.append(f"- 產生腳本：`.agent/scripts/scan_financial_score.py`（{today} 執行）")
    lines.append("")

    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只掃描前N檔 (測試用)")
    parser.add_argument("--tickers", type=str, default=None, help="逗號分隔的個股代號清單，指定時忽略 --limit")
    parser.add_argument("--min-score", type=int, default=None, help="只在報告中保留分數 >= 此值的個股")
    parser.add_argument("--rate-limit", type=float, default=0.15, help="每次 FinMind API 呼叫間隔秒數")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    if args.tickers:
        ticker_list = [t.strip() for t in args.tickers.split(",") if t.strip()]
        universe = [{"stock_id": t, "stock_name": None} for t in ticker_list]
        print(f"Scanning {len(universe)} specified tickers...")
    else:
        print("Fetching stock universe from FinMind...")
        universe = fetch_stock_universe()
        if args.limit:
            universe = universe[:args.limit]
        print(f"Universe size: {len(universe)}")

    def progress(i, total, ticker):
        if i % 50 == 0 or i == total:
            print(f"  [{i}/{total}] {ticker}...")

    results = scan_market(rate_limit_sec=args.rate_limit, min_score=args.min_score,
                           progress_callback=progress, universe=universe)

    tracked = get_tracked_tickers()
    report_lines = build_report(results, tracked, args.min_score, len(universe))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename_stem = f"{datetime.now().strftime('%Y%m%d')}_財務指標篩選"
    output_path = os.path.join(OUTPUT_DIR, f"{filename_stem}.md")
    with io.open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\nGenerated report at: {output_path}")

    try:
        render_markdown_to_pdf(report_lines, OUTPUT_DIR, filename_stem)
        print(f"Generated PDF at: {os.path.join(OUTPUT_DIR, filename_stem + '.pdf')}")
    except Exception as e:
        print(f"Warning: Failed to generate PDF: {e}")


if __name__ == "__main__":
    main()
