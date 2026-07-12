"""
全市場動能篩選掃描 (momentum_score) + 題材/產業位置動能彙總。

用法：
    python scan_momentum_score.py                  # 個股全市場掃描 (同financial_score流動性門檻) + 題材彙總
    python scan_momentum_score.py --limit 50        # 只掃前50檔市場個股 (測試用，題材彙總照常跑全部題材成員)
    python scan_momentum_score.py --tickers 2330,3443   # 只掃指定個股，略過題材彙總
    python scan_momentum_score.py --min-score 40    # 個股報告只保留分數 >= 40 的個股

規則依據 `97_Settings/動能篩選門檻.md` 的個股指標 (0分起累加，無上限) 與「報告顯示設定」
（啟用新標的掃描開關、各區塊顯示前幾名、資料庫個股分數門檻）。
題材/產業位置動能 = 彙總該分類全部成員的個股 momentum_score（平均分/前3高分成員），
成員清單直接讀 `97_Settings/概念股FPE合理區間.md`（與個股全市場掃描不同，題材成員不受
流動性門檻限制，因為部分題材成員本身就是規模較小的供應鏈個股）。輸出報告至
30_Projects/Momentum_Screen/。
"""
import argparse
import io
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.momentum_screen import (
    load_momentum_criteria, compute_momentum_score, fetch_taiex_history,
    fetch_price_history, fetch_institutional_flow, fetch_revenue_history,
    fetch_quarterly_gross_margin, fetch_whale_holding_ratio,
    load_report_display_settings,
)
from lib.financial_screen import fetch_stock_universe, apply_liquidity_filter, load_liquidity_settings
from lib.stock_signals import load_concept_fpe_table
from lib.report_pdf import render_markdown_to_pdf, assemble_report

STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"
OUTPUT_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Momentum_Screen"
CONCEPT_TOP_MEMBERS = 3  # 每個分類顯示前幾高分成員

# 三個表格欄位寬度統一：兩張表恰好都是 3 欄，且第1/2欄是短標籤+分數、第3欄是長列表
# (通過指標 / 最高分成員)，套同一組寬度比例即可。
MOMENTUM_TABLE_CSS = """
        table { table-layout: fixed; font-size: 8.3pt; }
        th:nth-child(1), td:nth-child(1) { width: 20%; } /* 分類 / 股票 */
        th:nth-child(2), td:nth-child(2) { width: 13%; } /* 平均分數 / 動能分數 */
        th:nth-child(3), td:nth-child(3) { width: 67%; } /* 最高分成員 / 通過指標 */
"""


def get_tracked_ticker_names():
    """回傳 {代號: 名稱} 對照，從 10_Stocks/ 現有檔名解析。"""
    names = {}
    for filename in os.listdir(STOCK_DIR):
        if not filename.endswith('.md'):
            continue
        m = re.match(r'^([0-9]+(?:\.[a-zA-Z0-9]+)?)(.+)\.md$', filename)
        if m:
            names[m.group(1)] = m.group(2)
    return names


def _fmt_score(v):
    return f"{v:g}"


def _apply_top_n(rows, top_n):
    return rows if not top_n or top_n <= 0 else rows[:top_n]


def _display_concept_label(concept):
    """拿掉產業位置分類檔名開頭的 Tier 編號與第一個底線，例如 "2_晶片層_感測_MCU"
    顯示成 "晶片層_感測_MCU"；題材/其他類分類（不是數字開頭）維持原樣不動。"""
    return re.sub(r'^\d+_', '', concept)


def _stock_cell(ticker, name):
    """股票欄位顯示成「代號」換行「名稱」兩行；沒有名稱時（如新發現標的裡查不到
    公司名稱者）只顯示代號。"""
    return f"{ticker}<br>{name}" if name else ticker


def _format_breakdown(breakdown):
    """把命中的指標整理成顯示字串：加分項只顯示名稱（跟以往一致），扣分項（如長黑K棒）
    額外標註分數，避免使用者誤以為那是加分條件。"""
    items = []
    for b in breakdown:
        if b["points_earned"] > 0:
            items.append(b["criterion"])
        elif b["points_earned"] < 0:
            items.append(f"{b['criterion']}({_fmt_score(b['points_earned'])}分)")
    return '、'.join(items)


def score_all(tickers, taiex_series, criteria, rate_limit_sec, progress_callback=None):
    """對一組代號逐一計算 momentum_score，回傳 {ticker: result}。"""
    scores = {}
    total = len(tickers)
    for i, ticker in enumerate(tickers):
        if progress_callback:
            progress_callback(i + 1, total, ticker)
        try:
            price = fetch_price_history(ticker, rate_limit_sec=rate_limit_sec)
            inst = fetch_institutional_flow(ticker, rate_limit_sec=rate_limit_sec)
            rev = fetch_revenue_history(ticker, rate_limit_sec=rate_limit_sec)
            gross_margin_avg = fetch_quarterly_gross_margin(ticker, rate_limit_sec=rate_limit_sec)
            whale_ratio_400 = fetch_whale_holding_ratio(ticker, rate_limit_sec=rate_limit_sec)
            scores[ticker] = compute_momentum_score(
                ticker, price, taiex_series, inst, rev, criteria,
                gross_margin_avg=gross_margin_avg, whale_ratio_400=whale_ratio_400,
            )
        except Exception as e:
            scores[ticker] = {"ticker": ticker, "total_score": 0, "breakdown": [],
                               "data_complete": False, "error": str(e)}
    return scores


def build_concept_section(concepts, scores, ticker_names, top_n, min_avg):
    """彙總每個題材/產業位置的動能分數，回傳依平均分排序的 markdown 行。"""
    rows = []
    for c in concepts:
        member_scores = [(t, scores[t]) for t in c["members"] if t in scores]
        if not member_scores:
            continue
        total = sum(s["total_score"] for _, s in member_scores)
        avg = total / len(member_scores)
        member_scores.sort(key=lambda x: x[1]["total_score"], reverse=True)
        top_members = member_scores[:CONCEPT_TOP_MEMBERS]
        rows.append({
            "concept": c["concept"], "avg": avg, "member_count": len(member_scores),
            "top_members": [(t, ticker_names.get(t, ""), s["total_score"]) for t, s in top_members],
        })
    rows = [r for r in rows if r["avg"] > min_avg]
    rows.sort(key=lambda r: r["avg"], reverse=True)
    total_qualified = len(rows)
    rows = _apply_top_n(rows, top_n)

    lines = [f"## 🔥 產業/題材 動能排行（共 {total_qualified} 個分類）", "",
             "| 分類 | 平均分數 | 最高分成員 |",
             "| :--- | :--- | :--- |"]
    for r in rows:
        top_str = "、".join(f"{t}{name} ({_fmt_score(score)}分)" for t, name, score in r["top_members"])
        lines.append(f"| `[[{r['concept']}|{_display_concept_label(r['concept'])}]]` | "
                      f"{_fmt_score(round(r['avg'], 1))} | {top_str} |")
    if not rows:
        lines.append("| (無) | | |")
    lines.append("")
    return lines


def build_tracked_section(scores, universe_tickers, tracked_names, top_n, min_score):
    complete = [scores[t] for t in universe_tickers if t in scores]
    complete.sort(key=lambda r: r["total_score"], reverse=True)

    tracked_ticker_set = set(tracked_names.keys())
    tracked_scored = [r for r in complete if r["ticker"] in tracked_ticker_set and r["total_score"] >= min_score]
    total_qualified = len(tracked_scored)
    rows = _apply_top_n(tracked_scored, top_n)

    lines = [f"## 📌 資料庫個股 動能排行（共 {total_qualified} 檔，動能分數 >= {min_score} 分）", ""]
    lines.append("| 股票 | 動能分數 | 通過指標 |")
    lines.append("| :--- | :--- | :--- |")
    for r in rows:
        name = tracked_names.get(r["ticker"], "")
        lines.append(f"| {_stock_cell(r['ticker'], name)} | {_fmt_score(r['total_score'])} | {_format_breakdown(r['breakdown'])} |")
    if not rows:
        lines.append("| (無) | | |")
    lines.append("")
    return lines


def build_new_section(scores, universe_tickers, tracked_names, top_n, market_ticker_names):
    complete = [scores[t] for t in universe_tickers if t in scores]
    complete.sort(key=lambda r: r["total_score"], reverse=True)

    tracked_ticker_set = set(tracked_names.keys())
    new_candidates = [r for r in complete if r["ticker"] not in tracked_ticker_set]
    total_qualified = len(new_candidates)
    rows = _apply_top_n(new_candidates, top_n)

    lines = [f"## 🆕 新發現動能標的（共 {total_qualified} 檔，不在現有 10_Stocks/ 追蹤清單中）", ""]
    lines.append("| 股票 | 動能分數 | 通過指標 |")
    lines.append("| :--- | :--- | :--- |")
    for r in rows:
        name = market_ticker_names.get(r["ticker"], "")
        lines.append(f"| {_stock_cell(r['ticker'], name)} | {_fmt_score(r['total_score'])} | {_format_breakdown(r['breakdown'])} |")
    if not rows:
        lines.append("| (無) | | |")
    lines.append("")
    return lines


def build_title_block(today):
    return ["# 宇宙資本 動能篩選股", "", f"**{today}**", ""]


def build_note_block(market_ticker_count, concept_count, concept_member_count):
    return [f"> 依 `[[動能篩選門檻]]` 個股指標 (0分起累加無上限)。個股全市場掃描 {market_ticker_count} 檔"
            f"（已排除殭屍股）；題材/產業位置動能彙總涵蓋 `[[概念股FPE合理區間]]` 全部 {concept_count} 個分類、"
            f"{concept_member_count} 檔不重複成員（不受流動性門檻限制）。"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只掃描前N檔市場個股 (測試用)")
    parser.add_argument("--tickers", type=str, default=None, help="逗號分隔的個股代號清單，指定時略過題材彙總")
    parser.add_argument("--min-score", type=int, default=None, help="個股報告只保留分數 >= 此值")
    parser.add_argument("--rate-limit", type=float, default=0.15, help="每次 FinMind API 呼叫間隔秒數")
    parser.add_argument("--skip-liquidity-filter", action="store_true", help="關閉流動性/市值篩選")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    criteria = load_momentum_criteria()
    print(f"Loaded {len(criteria)} momentum criteria.")

    display_settings = load_report_display_settings()
    print(f"Report display settings: {display_settings}")

    print("Fetching TAIEX index history...")
    taiex_series = fetch_taiex_history()

    do_concepts = not args.tickers
    concepts = load_concept_fpe_table() if do_concepts else []

    tracked_names = get_tracked_ticker_names()
    market_ticker_names = {}

    if args.tickers:
        market_tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
        print(f"Scanning {len(market_tickers)} specified tickers (no liquidity filter, no concept rollup)...")
    elif not display_settings["scan_new"]:
        market_tickers = sorted(tracked_names.keys())
        if args.limit:
            market_tickers = market_tickers[:args.limit]
        print(f"啟用新標的掃描=N，只掃描資料庫既有 {len(market_tickers)} 檔追蹤個股（略過全市場新標的掃描）...")
    else:
        print("Fetching stock universe from FinMind...")
        universe = fetch_stock_universe()
        print(f"Universe size (category filter only): {len(universe)}")

        liquidity_settings = load_liquidity_settings()
        if liquidity_settings["enabled"] and not args.skip_liquidity_filter:
            print("Applying liquidity/market-cap filter...")
            before = len(universe)
            universe, excluded = apply_liquidity_filter(universe, settings=liquidity_settings)
            print(f"  {before} -> {len(universe)} (excluded {excluded} zombie stocks)")

        if args.limit:
            universe = universe[:args.limit]
        market_tickers = [s["stock_id"] for s in universe]
        market_ticker_names = {s["stock_id"]: s.get("stock_name", "") for s in universe}
        print(f"Market scan universe size: {len(market_tickers)}")

    concept_member_tickers = set()
    for c in concepts:
        concept_member_tickers.update(c["members"])

    union_tickers = sorted(set(market_tickers) | concept_member_tickers)
    print(f"Total unique tickers to score (market ∪ concept members): {len(union_tickers)}")

    def progress(i, total, ticker):
        if i % 50 == 0 or i == total:
            print(f"  [{i}/{total}] {ticker}...")

    scores = score_all(union_tickers, taiex_series, criteria, args.rate_limit, progress_callback=progress)

    if args.min_score is not None:
        market_tickers_for_report = [t for t in market_tickers if scores.get(t, {}).get("total_score", 0) >= args.min_score]
    else:
        market_tickers_for_report = market_tickers

    today = datetime.now().strftime("%Y-%m-%d")

    title_block = build_title_block(today)
    note_block = build_note_block(len(market_tickers), len(concepts), len(concept_member_tickers))

    body = []
    if do_concepts:
        body += build_concept_section(concepts, scores, tracked_names,
                                       display_settings["top_n_concepts"], display_settings["concept_min_avg"])
        body.append("---")
        body.append("")

    body += build_tracked_section(scores, market_tickers_for_report, tracked_names,
                                   display_settings["top_n_tracked"], display_settings["tracked_min_score"])

    # 啟用新標的掃描=N 時，market_tickers 本來就只含資料庫既有個股，這裡永遠是 0 檔——
    # 與其顯示一個空區塊，乾脆整段（標題+空表格）都不輸出，比較乾淨。
    if display_settings["scan_new"]:
        body.append("---")
        body.append("")
        body += build_new_section(scores, market_tickers_for_report, tracked_names,
                                   display_settings["top_n_new"], market_ticker_names)

    original_docs = [
        "---", "",
        "## 📄 原始文件與連結 (Original Documents)",
        "- 規則定義：`[[動能篩選門檻]]`",
        f"- 產生腳本：`.agent/scripts/scan_momentum_score.py`（{today} 執行）",
        "",
    ]

    # .md 檔保留說明區塊與原始文件連結給自己看；PDF 版拿掉這兩段，避免每次印出來都
    # 先看到一長串技術性說明文字，且原始文件連結在紙本報告上沒有意義。
    md_lines, pdf_lines = assemble_report(title_block, body, note_block=note_block, original_docs=original_docs)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename_stem = f"{datetime.now().strftime('%Y%m%d')}_動能篩選"
    output_path = os.path.join(OUTPUT_DIR, f"{filename_stem}.md")
    with io.open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"\nGenerated report at: {output_path}")

    try:
        render_markdown_to_pdf(pdf_lines, OUTPUT_DIR, filename_stem, extra_css=MOMENTUM_TABLE_CSS)
        print(f"Generated PDF at: {os.path.join(OUTPUT_DIR, filename_stem + '.pdf')}")
    except Exception as e:
        print(f"Warning: Failed to generate PDF: {e}")


if __name__ == "__main__":
    main()
