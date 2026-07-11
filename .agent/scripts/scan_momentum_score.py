"""
全市場動能篩選掃描 (momentum_score) + 題材/產業位置動能彙總。

用法：
    python scan_momentum_score.py                  # 個股全市場掃描 (同financial_score流動性門檻) + 題材彙總
    python scan_momentum_score.py --limit 50        # 只掃前50檔市場個股 (測試用，題材彙總照常跑全部題材成員)
    python scan_momentum_score.py --tickers 2330,3443   # 只掃指定個股，略過題材彙總
    python scan_momentum_score.py --min-score 40    # 個股報告只保留分數 >= 40 的個股

規則依據 `97_Settings/動能篩選門檻.md` 的 14 項個股指標 (0分起累加，無上限)。
題材/產業位置動能 = 彙總該分類全部成員的個股 momentum_score（平均分/廣度/最高分成員），
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
)
from lib.financial_screen import fetch_stock_universe, apply_liquidity_filter, load_liquidity_settings
from lib.stock_signals import load_concept_fpe_table
from lib.report_pdf import render_markdown_to_pdf

STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"
OUTPUT_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Momentum_Screen"
BREADTH_THRESHOLD = 40  # 題材廣度指標：成員動能分數 >= 此值視為「該股正在動」
CONCEPT_MIN_AVG = 60  # 題材/產業位置動能排行：平均動能分數需超過此值才列入報告
TRACKED_MIN_SCORE = 80  # 個股動能 - 既有追蹤標的：動能分數需 >= 此值才列入報告


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


def build_concept_section(concepts, scores, ticker_names):
    """彙總每個題材/產業位置的動能分數，回傳依平均分排序的 markdown 行。"""
    rows = []
    for c in concepts:
        member_scores = [(t, scores[t]) for t in c["members"] if t in scores]
        if not member_scores:
            continue
        total = sum(s["total_score"] for _, s in member_scores)
        avg = total / len(member_scores)
        hot_count = sum(1 for _, s in member_scores if s["total_score"] >= BREADTH_THRESHOLD)
        breadth_pct = hot_count / len(member_scores) * 100.0
        top_ticker, top_score_obj = max(member_scores, key=lambda x: x[1]["total_score"])
        top_name = ticker_names.get(top_ticker, "")
        rows.append({
            "concept": c["concept"], "avg": avg, "breadth_pct": breadth_pct,
            "member_count": len(member_scores), "hot_count": hot_count,
            "top_ticker": top_ticker, "top_name": top_name, "top_score": top_score_obj["total_score"],
        })
    rows = [r for r in rows if r["avg"] > CONCEPT_MIN_AVG]
    rows.sort(key=lambda r: r["avg"], reverse=True)

    lines = ["## 🔥 題材/產業位置動能排行", "",
             f"> 廣度計算門檻：成員個股動能分數 >= {BREADTH_THRESHOLD} 分視為「該股正在動」。"
             f"只列出平均動能分數 > {CONCEPT_MIN_AVG} 分的分類。", "",
             "| 分類 | 平均動能分數 | 廣度 | 最高分成員 |",
             "| :--- | :--- | :--- | :--- |"]
    for r in rows:
        lines.append(f"| `[[{r['concept']}]]` | {_fmt_score(round(r['avg'], 1))} | "
                      f"{r['hot_count']}/{r['member_count']} ({r['breadth_pct']:.0f}%) | "
                      f"{r['top_ticker']}{r['top_name']} ({_fmt_score(r['top_score'])}分) |")
    lines.append("")
    return lines


def build_individual_section(scores, universe_tickers, tracked_names):
    complete = [scores[t] for t in universe_tickers if t in scores]
    complete.sort(key=lambda r: r["total_score"], reverse=True)

    tracked_ticker_set = set(tracked_names.keys())
    new_candidates = [r for r in complete if r["ticker"] not in tracked_ticker_set]
    tracked_scored = [r for r in complete if r["ticker"] in tracked_ticker_set and r["total_score"] >= TRACKED_MIN_SCORE]

    lines = [f"## 🆕 個股動能 - 新發現標的（不在現有 10_Stocks/ 追蹤清單中，共 {len(new_candidates)} 檔）", "",
              "| 股票 | 動能分數 | 通過指標 |", "| :--- | :--- | :--- |"]
    for r in new_candidates[:50]:
        passed = [b["criterion"] for b in r["breakdown"] if b["points_earned"] > 0]
        lines.append(f"| {r['ticker']} | {_fmt_score(r['total_score'])} | {'、'.join(passed)} |")
    if not new_candidates:
        lines.append("| (無) | | |")
    lines.append("")

    lines.append(f"## 📌 個股動能 - 既有追蹤標的（10_Stocks/ 已收錄，動能分數 >= {TRACKED_MIN_SCORE} 分，共 {len(tracked_scored)} 檔）")
    lines.append("")
    lines.append("| 股票 | 動能分數 | 通過指標 |")
    lines.append("| :--- | :--- | :--- |")
    for r in tracked_scored:
        name = tracked_names.get(r["ticker"], "")
        passed = [b["criterion"] for b in r["breakdown"] if b["points_earned"] > 0]
        lines.append(f"| {r['ticker']}{name} | {_fmt_score(r['total_score'])} | {'、'.join(passed)} |")
    if not tracked_scored:
        lines.append("| (無) | | |")
    lines.append("")
    return lines


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

    print("Fetching TAIEX index history...")
    taiex_series = fetch_taiex_history()

    do_concepts = not args.tickers
    concepts = load_concept_fpe_table() if do_concepts else []

    if args.tickers:
        market_tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
        print(f"Scanning {len(market_tickers)} specified tickers (no liquidity filter, no concept rollup)...")
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

    tracked_names = get_tracked_ticker_names()

    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# 動能篩選 momentum_score 全市場掃描 ({today})", "",
              f"> 依 `[[動能篩選門檻]]` 14 項個股指標 (0分起累加無上限)。個股全市場掃描 {len(market_tickers)} 檔"
              f"（已排除殭屍股）；題材/產業位置動能彙總涵蓋 `[[概念股FPE合理區間]]` 全部 {len(concepts)} 個分類、"
              f"{len(concept_member_tickers)} 檔不重複成員（不受流動性門檻限制）。", "",
              "---", ""]

    if do_concepts:
        lines += build_concept_section(concepts, scores, tracked_names)
        lines.append("---")
        lines.append("")

    lines += build_individual_section(scores, market_tickers_for_report, tracked_names)

    lines.append("---")
    lines.append("")
    lines.append("## 📄 原始文件與連結 (Original Documents)")
    lines.append("- 規則定義：`[[動能篩選門檻]]`")
    lines.append(f"- 產生腳本：`.agent/scripts/scan_momentum_score.py`（{today} 執行）")
    lines.append("")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename_stem = f"{datetime.now().strftime('%Y%m%d')}_動能篩選"
    output_path = os.path.join(OUTPUT_DIR, f"{filename_stem}.md")
    with io.open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nGenerated report at: {output_path}")

    try:
        render_markdown_to_pdf(lines, OUTPUT_DIR, filename_stem)
        print(f"Generated PDF at: {os.path.join(OUTPUT_DIR, filename_stem + '.pdf')}")
    except Exception as e:
        print(f"Warning: Failed to generate PDF: {e}")


if __name__ == "__main__":
    main()
