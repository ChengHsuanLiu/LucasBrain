"""
個股融資維持率估算報告 (近N年逐日流量加權平均成本法，預設窗口見 lib/margin_maintenance.LOOKBACK_YEARS)。

⚠️ 這是估算值，非官方數字。TWSE/TPEx 不公開個股層級融資維持率（那是券商依各帳戶實際
成本計算的帳戶級指標），本報告改用「加權平均成本法」從逐日融資買進/賣出/現金償還流量
反推估算，方法論與已知限制詳見 `lib/margin_maintenance.py` 模組說明。「股數重建誤差」
欄位是資料品質指標：誤差絕對值越大，代表回溯期內可能有減資/股票股利/企業合併等公司
行動未被模型捕捉，估算越不可信。

用法：
    python calc_margin_maintenance.py
"""
import os
import re
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.margin_maintenance import compute_margin_maintenance, fetch_market_type_map, LOOKBACK_YEARS
from lib.report_pdf import render_markdown_to_pdf

STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"
OUTPUT_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Stock_Margin"
FOREIGN_LISTING_SUFFIXES = (".SH", ".HK", ".SS")
RATE_LIMIT_SEC = 0.15
MAX_SHARE_DIFF_PCT = 5.0  # 股數重建誤差絕對值超過此門檻視為不可信，直接濾掉不顯示

REPORT_CSS = """
    table { table-layout: fixed; font-size: 8.6pt; }
    th:nth-child(1), td:nth-child(1) { width: 22%; }
    th:nth-child(2), td:nth-child(2) { width: 14%; }
    th:nth-child(3), td:nth-child(3) { width: 20%; }
    th:nth-child(4), td:nth-child(4) { width: 20%; }
"""


def get_tracked_stocks():
    """回傳 [(ticker, name), ...]，從 10_Stocks/ 現有檔名解析，排除非台股掛牌（美股/中股ADR等）。"""
    stocks = []
    for filename in os.listdir(STOCK_DIR):
        if not filename.endswith('.md'):
            continue
        m = re.match(r'^([0-9]+(?:\.[a-zA-Z0-9]+)?)(.*?)\.md$', filename)
        if not m:
            continue
        ticker, name = m.group(1).strip(), m.group(2).strip()
        if any(suffix in ticker for suffix in FOREIGN_LISTING_SUFFIXES):
            continue
        stocks.append((ticker, name))
    return sorted(stocks, key=lambda x: x[0])


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    stocks = get_tracked_stocks()
    print(f"追蹤個股數（排除海外掛牌）：{len(stocks)}")

    print("批次查詢全市場上市/上櫃別...")
    market_type_map = fetch_market_type_map()

    results = []
    failed = []
    for i, (ticker, name) in enumerate(stocks, 1):
        if i % 20 == 0 or i == len(stocks):
            print(f"  [{i}/{len(stocks)}] {ticker}{name} ...")
        market_type = market_type_map.get(ticker)
        try:
            r = compute_margin_maintenance(ticker, market_type=market_type)
            if r:
                r["name"] = name
                results.append(r)
            else:
                failed.append((ticker, name, "無融資資料或資料不足"))
        except Exception as e:
            failed.append((ticker, name, str(e)))
        time.sleep(RATE_LIMIT_SEC)

    total_computed = len(results)
    results = [r for r in results if r["share_diff_pct"] is not None and abs(r["share_diff_pct"]) <= MAX_SHARE_DIFF_PCT]
    excluded_unreliable = total_computed - len(results)
    total_excluded = excluded_unreliable + len(failed)
    results.sort(key=lambda r: r["ratio"])

    today = datetime.now().strftime("%Y-%m-%d")
    filename_stem = f"{datetime.now().strftime('%Y%m%d')}_宇宙資本_融資維持率"

    lines = []
    lines.append("---")
    lines.append("type: project_report")
    lines.append(f"date: {today}")
    lines.append("author: 投資幕僚團隊")
    lines.append("tags: [report/margin-maintenance]")
    lines.append("---")
    lines.append("")
    lines.append(f"# 宇宙資本 個股融資維持率估算 {today}")
    lines.append("")
    lines.append("> [!CAUTION]")
    lines.append(
        f"> **這是估算值，不是官方數字。** TWSE/TPEx 不公開個股層級的融資維持率（維持率是券商依各帳戶實際成本計算的帳戶級指標，非公開資料）。"
        f"本報告用「加權平均成本法」，從近 {LOOKBACK_YEARS} 年逐日融資買進/賣出/現金償還流量反推估算整體平均融資成本，"
        f"再算出擔保品市值對融資金額的比率，僅供排序參考，不代表任何真實帳戶的實際維持率。"
        f"**「股數重建誤差」欄位是資料品質指標**：反推出的融資股數跟官方回報餘額差距越大，"
        f"代表該股在回溯窗口內可能歷經減資、股票股利、企業合併等公司行動而未被此模型捕捉，估算可信度越低。"
        f"已自動濾掉誤差絕對值超過 {MAX_SHARE_DIFF_PCT:.0f}% 的個股與資料不足無法計算者（共 {total_excluded} 檔），"
        f"以下僅列出估算相對可信的標的。"
    )
    lines.append("")
    lines.append("| 股名 | 代號 | 融資維持率 | 股數重建誤差 |")
    lines.append("| :--- | :--- | :--- | :--- |")
    for r in results:
        diff = r["share_diff_pct"]
        diff_str = f"{diff:+.1f}%" if diff is not None else "N/A"
        lines.append(f"| {r['name']} | {r['ticker']} | {r['ratio']:.1f}% | {diff_str} |")
    lines.append("")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{filename_stem}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nGenerated report at: {output_path}")

    try:
        render_markdown_to_pdf(lines, OUTPUT_DIR, filename_stem, extra_css=REPORT_CSS)
        print(f"Generated PDF at: {os.path.join(OUTPUT_DIR, filename_stem + '.pdf')}")
    except Exception as e:
        print(f"Warning: Failed to generate PDF: {e}")


if __name__ == "__main__":
    main()
