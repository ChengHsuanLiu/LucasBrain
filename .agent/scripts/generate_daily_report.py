"""
生成盤後大盤日報 (DailyReport - 一、大盤情況 + 二、族群強度 + 三、大戶籌碼 + 四、個股買賣訊號)。

用法：
    python generate_daily_report.py [YYYY-MM-DD]

若不帶日期參數，預設抓最新一個交易日的資料。四大區塊皆已實作完成。
"""
import os
import re
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
from lib.stock_signals import (
    load_concept_fpe_table,
    compute_stock_signal,
    BUY_EXPECTED_VALUE_THRESHOLD,
)
from lib.whale_tracking import (
    get_latest_snapshot_per_whale,
    compute_position_deltas,
    get_consensus_stocks_latest,
)
from lib.sector_trend import top_gaining_sectors
from lib.report_pdf import render_markdown_to_pdf

OUTPUT_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Daily_Report"
STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"


def get_tracked_tickers():
    """回傳資料庫 10_Stocks/ 現有的個股代號集合，供大戶持股/共識標的比對是否為已追蹤個股。"""
    tickers = set()
    for filename in os.listdir(STOCK_DIR):
        if not filename.endswith('.md'):
            continue
        m = re.match(r'^([0-9]+(?:\.[a-zA-Z0-9]+)?)', filename)
        if m:
            tickers.add(m.group(1))
    return tickers


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


def build_sector_trend_section():
    lines = ["### 二、股票族群情況", ""]

    lines.append("#### 當日強勢族群 Top 3（不限資料庫股票）")
    lines.append("")
    try:
        today_top = top_gaining_sectors("1day", top_n=3)
        if today_top:
            lines.append("| 排名 | 族群 | 漲幅 |")
            lines.append("| :--- | :--- | :--- |")
            for i, s in enumerate(today_top, 1):
                lines.append(f"| {i} | {s['name']} | {s['diff_percentage']:+.2f}% |")
        else:
            lines.append("*今日無明顯強勢族群。*")
    except Exception as e:
        lines.append(f"*抓取失敗 ({e})*")
    lines.append("")

    lines.append("#### 近幾日強勢族群 Top 3")
    lines.append("")
    for period, label in [("1week", "近1週"), ("1month", "近1月")]:
        lines.append(f"**{label}**")
        lines.append("")
        try:
            top = top_gaining_sectors(period, top_n=3)
            if top:
                lines.append("| 排名 | 族群 | 漲幅 |")
                lines.append("| :--- | :--- | :--- |")
                for i, s in enumerate(top, 1):
                    lines.append(f"| {i} | {s['name']} | {s['diff_percentage']:+.2f}% |")
            else:
                lines.append(f"*{label}無明顯強勢族群。*")
        except Exception as e:
            lines.append(f"*抓取失敗 ({e})*")
        lines.append("")

    lines.append(
        "> **註**：資料來源為 Statementdog 公開市場熱力圖 API，涵蓋全市場概念股標籤，"
        "不限於本資料庫已建檔個股。"
    )
    lines.append("")

    return lines


def build_whale_section():
    lines = ["### 三、主力大戶（Whale）籌碼動向", ""]
    tracked_tickers = get_tracked_tickers()

    _, latest_date_by_whale = get_latest_snapshot_per_whale()
    lines.append("#### 各大戶當日買進/賣出重點")
    lines.append("")
    if not latest_date_by_whale:
        lines.append("*尚無大戶持股資料，請先執行「更新大戶持股」。*")
        lines.append("")
    else:
        for whale_id in sorted(latest_date_by_whale.keys()):
            whale_date = latest_date_by_whale[whale_id]
            deltas = compute_position_deltas(whale_id, whale_date)

            if not deltas["prev_date"]:
                # 首次記錄，沒有前一筆快照可比較，deltas["new"] 會把整個庫存都列為「新建倉」——
                # 這種情況下逐檔列出並非真正的「當日重點」，只需標註尚無比較基準即可。
                holdings_cnt = len(deltas["new"])
                lines.append(
                    f"* **{whale_id}**（{whale_date}）：首次記錄，尚無前次快照可比較"
                    f"（共 {holdings_cnt} 檔持股，總市值 {deltas['total_value_now']:,.0f}）"
                )
                continue

            highlights = []
            for entry in deltas["new"]:
                mark = "［已追蹤］" if entry["ticker"] in tracked_tickers else ""
                highlights.append(f"新建倉{mark} {entry['ticker']}{entry['name']}（市值 {entry['market_value']:,.0f}）")
            for entry in deltas["closed"]:
                mark = "［已追蹤］" if entry["ticker"] in tracked_tickers else ""
                highlights.append(f"出清{mark} {entry['ticker']}{entry['name']}")

            top_increased = sorted(deltas["increased"], key=lambda e: e["market_value"], reverse=True)[:3]
            for entry in top_increased:
                mark = "［已追蹤］" if entry["ticker"] in tracked_tickers else ""
                highlights.append(f"加碼{mark} {entry['ticker']}{entry['name']}（+{entry['shares_delta']:,.0f}股）")
            top_decreased = sorted(deltas["decreased"], key=lambda e: e["shares_delta"])[:3]
            for entry in top_decreased:
                mark = "［已追蹤］" if entry["ticker"] in tracked_tickers else ""
                highlights.append(f"減碼{mark} {entry['ticker']}{entry['name']}（{entry['shares_delta']:,.0f}股）")

            summary = "；".join(highlights) if highlights else "無明顯變化"
            lines.append(f"* **{whale_id}**（{whale_date}）：{summary}")
        lines.append("")

    lines.append("#### 共識標的（2位以上大戶同時持有）")
    lines.append("")
    consensus, _ = get_consensus_stocks_latest(min_whales=2)
    if consensus:
        lines.append("| 股票 | 大戶數 | 持有大戶 | 總市值 | 資料庫個股 |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for c in consensus:
            mark = "是" if c["ticker"] in tracked_tickers else "-"
            lines.append(
                f"| {c['ticker']}{c['name']} | {c['whale_count']} | {'、'.join(c['whale_ids'])} | "
                f"{c['total_market_value']:,.0f} | {mark} |"
            )
    else:
        lines.append("*目前無2位以上大戶同時持有的共識標的。*")
    lines.append("")

    lines.append(
        "> **註**：大戶代號為匿名代碼（大戶A/B/C...），資料來源為使用者每日手動取得的持股快照。"
        "各大戶回報日期可能因帳戶類型（現股/融資/股票期貨）不同而不同步，詳見上方各大戶標註日期；"
        "「資料庫個股」欄標示該檔是否已存在於 `10_Stocks/` 現有研究筆記中。"
    )
    lines.append("")

    return lines


def build_stock_signals_section():
    lines = ["### 四、資料庫個股買進/賣出訊號", ""]

    concept_table = load_concept_fpe_table()
    target_year = datetime.now().year + 1

    files = [os.path.join(STOCK_DIR, f) for f in os.listdir(STOCK_DIR) if f.endswith('.md')]
    results = []
    for fp in files:
        filename = os.path.basename(fp)
        m = re.match(r'^([0-9]+(?:\.[a-zA-Z0-9]+)?)(.*?)\.md$', filename)
        if not m:
            continue
        ticker, name = m.group(1).strip(), m.group(2).strip()
        sig = compute_stock_signal(ticker, fp, target_year, concept_table)
        if sig:
            sig["name"] = name
            results.append(sig)

    buy_list = sorted(
        (r for r in results if r["signal"] == "BUY"),
        key=lambda r: r["expected_value_pct"], reverse=True
    )
    sell_list = sorted(
        (r for r in results if r["signal"].startswith("SELL")),
        key=lambda r: r["expected_value_pct"] if r["expected_value_pct"] is not None else 999
    )

    lines.append(f"#### 買進訊號（期望值 > {BUY_EXPECTED_VALUE_THRESHOLD:.0f}%）")
    lines.append("")
    if buy_list:
        lines.append("| 股票 | 現價 | 目標價 | 期望值 | 均線評分 | 乖離評分 | 提醒 |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in buy_list:
            alert_str = "；".join(r["alerts"]) if r["alerts"] else "-"
            lines.append(
                f"| {r['ticker']}{r['name']} | {r['current_price']:.2f} | {r['target_price']:.2f} | "
                f"{r['expected_value_pct']:+.1f}% | {r['ma_rating']} | {r['bias_rating']} | {alert_str} |"
            )
    else:
        lines.append("*今日無符合門檻的買進訊號。*")
    lines.append("")

    lines.append("#### 賣出/減碼訊號")
    lines.append("")
    if sell_list:
        lines.append("| 股票 | 現價 | 目標價 | 期望值 | 均線評分 | 乖離評分 | 觸發原因 |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        sell_reason_labels = {
            "SELL_逢高減碼": "期望值<30%，逢高減碼",
            "SELL_跌破5MA": "跌破5日線且期望值<60%",
            "SELL_乖離過熱": "乖離率評分過低，逢高減碼",
        }
        for r in sell_list:
            target_price_str = f"{r['target_price']:.2f}" if r['target_price'] is not None else "待補充"
            ev_str = f"{r['expected_value_pct']:+.1f}%" if r['expected_value_pct'] is not None else "待補充"
            reason_str = sell_reason_labels.get(r["signal"], r["signal"])
            lines.append(
                f"| {r['ticker']}{r['name']} | {r['current_price']:.2f} | {target_price_str} | "
                f"{ev_str} | {r['ma_rating']} | {r['bias_rating']} | {reason_str} |"
            )
    else:
        lines.append("*今日無觸發賣出/減碼條件的個股。*")
    lines.append("")

    no_fpe_cnt = sum(1 for r in results if r["fpe_range"] is None)
    lines.append(
        f"> **註**：目標價 = 隔年({target_year})預估EPS × 所屬概念股FPE中緣（同屬多個概念取平均，"
        f"見 `[[概念股FPE合理區間]]`）；期望值 = (目標價/現價 - 1)。"
        f"目前資料庫 {len(results)} 檔個股中有 {no_fpe_cnt} 檔缺EPS預估或概念分類，"
        f"標記為「待補充」，未納入買賣訊號判定。"
    )
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

    report.append('<div class="step-page-break"></div>')
    report.append("")
    report.extend(build_sector_trend_section())

    report.append('<div class="step-page-break"></div>')
    report.append("")
    report.extend(build_whale_section())

    report.append('<div class="step-page-break"></div>')
    report.append("")
    report.extend(build_stock_signals_section())

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
