"""
生成盤後大盤日報 (DailyReport - 一、大盤情況)。

用法：
    python generate_daily_report.py [YYYY-MM-DD]

若不帶日期參數，預設抓最新一個交易日的資料。目前僅實作「一、大盤情況」區塊
(指數/成交量/技術指標/融資/三大法人/外資期貨)，其餘區塊(族群強度/大戶整合/
個股買賣訊號)將於後續階段加入同一份報告。
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.market_data import (
    fetch_index_history,
    compute_index_ma,
    compute_bias,
    compute_volume_trend,
    compute_kd,
    compute_macd,
    detect_cross,
    detect_simple_divergence,
    fetch_twse_margin_total,
    fetch_tpex_margin_total,
    fetch_margin_maintenance_ratio,
    fetch_institutional_investors_total,
    fetch_foreign_futures_position,
    INDEX_MA_PERIODS,
)
from lib.report_pdf import render_markdown_to_pdf

OUTPUT_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Daily_Report"


def fmt_pct(v, decimals=2):
    return f"{v:+.{decimals}f}%" if v is not None else "N/A"


def fmt_num(v):
    return f"{v:,.0f}" if v is not None else "N/A"


def build_index_section(title, index_id, lookback_days=200):
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    ohlc = fetch_index_history(index_id, start_date)
    if not ohlc:
        return [f"### {title}", "*無法取得資料。*", ""], None

    latest = ohlc[-1]
    ma = compute_index_ma(ohlc)
    bias = compute_bias(ohlc)
    vol_trend, vol_change = compute_volume_trend(ohlc)

    kd = compute_kd(ohlc)
    macd = compute_macd(ohlc)
    k_list = [x["k"] for x in kd]
    d_list = [x["d"] for x in kd]
    dif_list = [x["dif"] for x in macd]
    dea_list = [x["dea"] for x in macd]

    kd_cross = detect_cross(k_list, d_list, lookback=1)
    macd_cross = detect_cross(dif_list, dea_list, lookback=1)
    kd_divergence = detect_simple_divergence(ohlc, k_list, lookback=20)
    macd_divergence = detect_simple_divergence(ohlc, dif_list, lookback=20)

    lines = [f"### {title}", ""]
    lines.append(f"* **日期**：{latest['date']}")
    lines.append(f"* **收盤**：{latest['close']:,.2f}（開 {latest['open']:,.2f}／高 {latest['high']:,.2f}／低 {latest['low']:,.2f}）")
    lines.append(f"* **成交量**：{fmt_num(latest['volume'])}（較前一日 {vol_trend}，{fmt_pct(vol_change)}）")
    lines.append("")

    lines.append("**均線與乖離**")
    lines.append("")
    lines.append("| 均線 | 數值 | 斜率 | 股價位置 | 乖離率 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for p in INDEX_MA_PERIODS:
        m = ma[p]
        b = bias[p]
        if m["val"] is None:
            lines.append(f"| {p}MA | N/A | N/A | N/A | N/A |")
            continue
        lines.append(f"| {p}MA | {m['val']:,.1f} | {m['slope']} | {m['close_vs_ma']} | {fmt_pct(b)} |")
    lines.append("")

    kd_cross_label = {"golden": "黃金交叉", "dead": "死亡交叉", None: "無交叉"}[kd_cross]
    macd_cross_label = {"golden": "黃金交叉", "dead": "死亡交叉", None: "無交叉"}[macd_cross]
    kd_div_label = {"top_bearish": "高檔背離(看空)", "bottom_bullish": "低檔背離(看多)", None: "無"}[kd_divergence]
    macd_div_label = {"top_bearish": "高檔背離(看空)", "bottom_bullish": "低檔背離(看多)", None: "無"}[macd_divergence]

    lines.append("**動能指標**")
    lines.append("")
    lines.append(f"* **KD**：K={k_list[-1]:.1f}／D={d_list[-1]:.1f}（{kd_cross_label}；背離：{kd_div_label}）")
    lines.append(f"* **MACD**：DIF={dif_list[-1]:.1f}／DEA={dea_list[-1]:.1f}（{macd_cross_label}；背離：{macd_div_label}）")
    lines.append("")
    lines.append("> **註**：背離偵測為簡化版高低點比對，非嚴謹型態辨識，僅供參考，建議人工覆核。")
    lines.append("")

    return lines, latest["date"]


def build_margin_section(index_date):
    lines = ["### 融資餘額與維持率", ""]

    try:
        twse = fetch_twse_margin_total()
        lines.append(f"* **上市融資餘額**：{fmt_num(twse['today_balance'])} 張（較前日 {twse['change']:+,.0f} 張）")
    except Exception as e:
        lines.append(f"* 上市融資餘額：抓取失敗 ({e})")

    try:
        tpex = fetch_tpex_margin_total()
        lines.append(f"* **上櫃融資餘額**：{fmt_num(tpex['today_balance'])} 張（較前日 {tpex['change']:+,.0f} 張）")
    except Exception as e:
        lines.append(f"* 上櫃融資餘額：抓取失敗 ({e})")

    try:
        start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        maint = fetch_margin_maintenance_ratio(start_date)
        if maint:
            latest_maint = maint[-1]
            prev_maint = maint[-2] if len(maint) >= 2 else None
            change_str = f"（較前日 {latest_maint['ratio'] - prev_maint['ratio']:+.2f}pp）" if prev_maint else ""
            lines.append(f"* **融資維持率**：{latest_maint['ratio']:.2f}%{change_str}（{latest_maint['date']}）")
    except Exception as e:
        lines.append(f"* 融資維持率：抓取失敗 ({e})")

    lines.append("")
    return lines


def build_institutional_section():
    lines = ["### 三大法人現貨買賣超", ""]
    try:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        inst = fetch_institutional_investors_total(start_date)
        if inst:
            lines.append(f"* **日期**：{inst['date']}")
            lines.append(f"* **外資**：{fmt_num(inst['foreign_net'])} 元")
            lines.append(f"* **投信**：{fmt_num(inst['investment_trust_net'])} 元")
            lines.append(f"* **自營商(合計)**：{fmt_num(inst['dealer_net'])} 元")
            lines.append(f"* **三大法人合計**：{fmt_num(inst['total_net'])} 元")
        else:
            lines.append("*無法取得資料。*")
    except Exception as e:
        lines.append(f"*抓取失敗 ({e})*")
    lines.append("")
    return lines


def build_futures_section():
    lines = ["### 外資台指期未平倉", ""]
    try:
        start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        futures = fetch_foreign_futures_position(start_date)
        if futures:
            latest = futures[-1]
            prev = futures[-2] if len(futures) >= 2 else None
            lines.append(f"* **日期**：{latest['date']}")
            lines.append(f"* **多單留倉**：{fmt_num(latest['long_oi'])} 口" + (f"（較前日 {latest['long_oi'] - prev['long_oi']:+,.0f} 口）" if prev else ""))
            lines.append(f"* **空單留倉**：{fmt_num(latest['short_oi'])} 口" + (f"（較前日 {latest['short_oi'] - prev['short_oi']:+,.0f} 口）" if prev else ""))
            lines.append(f"* **淨部位**：{latest['net_oi']:+,.0f} 口（{'偏多' if latest['net_oi'] > 0 else '偏空'}）" + (f"（較前日 {latest['net_oi'] - prev['net_oi']:+,.0f} 口）" if prev else ""))
        else:
            lines.append("*無法取得資料。*")
    except Exception as e:
        lines.append(f"*抓取失敗 ({e})*")
    lines.append("")
    return lines


def generate_report():
    today_str = datetime.now().strftime("%Y-%m-%d")
    report = []
    report.append("---")
    report.append("type: daily_report")
    report.append(f"date: {today_str}")
    report.append("author: 投資幕僚團隊")
    report.append("tags: [report/daily, market-overview]")
    report.append("---")
    report.append("")
    report.append(f"*{today_str}．投資幕僚團隊．盤後大盤日報*")
    report.append("")
    report.append(f"# 盤後大盤日報")
    report.append("### 一、大盤情況")
    report.append("")
    report.append("---")
    report.append("")

    taiex_lines, taiex_date = build_index_section("上市加權指數 (TAIEX)", "TAIEX")
    report.extend(taiex_lines)

    tpex_lines, tpex_date = build_index_section("上櫃指數 (TPEx)", "TPEx")
    report.extend(tpex_lines)

    report.append("---")
    report.append("")
    report.extend(build_margin_section(taiex_date))
    report.extend(build_institutional_section())
    report.extend(build_futures_section())

    filename_stem = f"{today_str.replace('-', '')}_DailyReport"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{filename_stem}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Generated Daily Report at: {output_path}")

    render_markdown_to_pdf(report, OUTPUT_DIR, filename_stem)

    return output_path


if __name__ == "__main__":
    generate_report()
