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
    compute_volume_ma,
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
    get_fpe_range_for_ticker,
    compute_stock_signal,
    compute_technical_signals,
    format_5ma_strategy_reasons,
    format_60ma_support_reason,
    format_sell_reasons,
    extract_investment_blurb,
    is_foreign_listing,
    BUY_EV_THRESHOLD_5MA_STRATEGY,
    BUY_EV_THRESHOLD_60MA_SUPPORT,
    SELL_EV_THRESHOLD_TRIM,
    SELL_EV_THRESHOLD_BREAK_5MA,
)
from lib.stock_metrics import parse_target_eps
from lib.whale_tracking import (
    get_latest_snapshot_per_whale,
    compute_position_deltas,
    get_consensus_stocks_latest,
)
from lib.sector_trend import top_gaining_industries_with_stocks, TWSE_SYMBOL, TPEX_SYMBOL
from lib.report_pdf import render_markdown_to_pdf

OUTPUT_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Daily_Report"
STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"

SECTOR_TOP_N_INDUSTRIES = 3
SECTOR_TOP_N_INDUSTRIES_WEEKLY = 5
SECTOR_TOP_N_STOCKS = 5

# 大盤情況區塊(均線/動能指標、融資/法人/期貨)用左右並排的精簡橫式排版，
# 靠 md_in_html 擴充讓 markdown="1" 的 <div> 內容照常轉表格/清單。
# num-up/num-down/flag-red 供全報告的數字上色（漲橘跌綠慣例）與五日線首日站上的特別標紅提醒。
DAILY_REPORT_EXTRA_CSS = """
    .idx-flex {
        display: flex;
        gap: 20px;
        margin: 4px 0 10px 0;
    }
    .idx-col {
        flex: 1;
        min-width: 0;
    }
    .idx-col table {
        font-size: 7.6pt;
        margin: 4px 0 6px 0;
    }
    .idx-col th, .idx-col td {
        padding: 3px 5px;
    }
    .idx-col p {
        margin: 0 0 4px 0;
    }
    .idx-col ul {
        margin: 0 0 4px 0;
        padding-left: 16px;
    }
    .idx-col li {
        margin-bottom: 2px;
        font-size: 8.6pt;
    }
    .num-up { color: #d6480f; font-weight: 700; }
    .num-down { color: #15803d; font-weight: 700; }
    .flag-red { color: #dc2626; font-weight: 800; }
    .text-blue { color: #2563eb; }
    .text-muted { color: #4b5563; font-weight: 400; }
    .whale-consensus table th:nth-child(5),
    .whale-consensus table td:nth-child(5) {
        min-width: 100px;
    }
"""


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


def get_tracked_ticker_filepaths():
    """回傳資料庫 10_Stocks/ 現有個股代號 -> 檔案路徑的對照，供共識標的算「目標價上緣」時查詢EPS用。"""
    mapping = {}
    for filename in os.listdir(STOCK_DIR):
        if not filename.endswith('.md'):
            continue
        m = re.match(r'^([0-9]+(?:\.[a-zA-Z0-9]+)?)', filename)
        if m:
            mapping[m.group(1)] = os.path.join(STOCK_DIR, filename)
    return mapping


def fmt_pct(v, decimals=2):
    return f"{v:+.{decimals}f}%" if v is not None else "N/A"


def fmt_num(v):
    return f"{v:,.0f}" if v is not None else "N/A"


def colorize(text, is_up, bold=True):
    cls = "num-up" if is_up else "num-down"
    style = "" if bold else ' style="font-weight:400;"'
    return f'<span class="{cls}"{style}>{text}</span>'


def colorize_signed(value, fmt="{:+.2f}%", flip=False, bold=True):
    """依正負號幫數字上色：預設正值(含0)用亮橘紅色、負值用綠色（本報告全篇「漲橘跌綠」慣例）。
    bold=False 時保留顏色但不加粗（用於族群表格等不需要粗體強調的欄位）。"""
    if value is None:
        return "N/A"
    text = fmt.format(value)
    is_up = (value >= 0) if not flip else (value < 0)
    return colorize(text, is_up, bold=bold)


def flag_red(text):
    return f'<span class="flag-red">{text}</span>'


def flag_blue(text):
    """均線斜率下彎、或股價位置跌破均線時，用藍色標記凸顯偏弱訊號。"""
    return f'<span class="text-blue">{text}</span>'


def gray_muted(text):
    """族群內領漲個股的漲跌幅用深灰色淡化顯示，不用漲跌上色慣例（凸顯個股名稱本身）。"""
    return f'<span class="text-muted">{text}</span>'


def short_rating_badge(rating_text):
    """把「均線評分佳/普通/差」類的完整敘述簡化為單一「差」或「佳」並上色
    （差=綠色、佳=亮橘紅色，比照本報告「漲橘跌綠」配色慣例）。"""
    short = "差" if "差" in rating_text else "佳"
    return colorize(short, is_up=(short == "佳"))


def build_index_section(title, index_id, lookback_days=200):
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    ohlc = fetch_index_history(index_id, start_date)
    if not ohlc:
        return [f"### {title}", "*無法取得資料。*", ""], None

    latest = ohlc[-1]
    ma = compute_index_ma(ohlc)
    bias = compute_bias(ohlc)
    vol_trend, vol_change = compute_volume_trend(ohlc)
    vol_ma = compute_volume_ma(ohlc)

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

    spread = latest.get("spread") or 0.0
    prev_close = latest["close"] - spread
    change_pct = (spread / prev_close * 100) if prev_close else 0.0
    money_yi = (latest.get("money") or 0) / 1e8

    lines = [f"### {title}", ""]
    lines.append(
        f"* **收盤價**：{latest['close']:,.2f}（{colorize_signed(spread, '{:+,.2f}')}，{colorize_signed(change_pct)}）"
    )
    vol_ma_position_str = flag_blue(vol_ma["position"]) if vol_ma["position"] == "跌破" else vol_ma["position"]
    vol_ma_slope_str = flag_blue(vol_ma["slope"]) if vol_ma["slope"] == "下彎" else vol_ma["slope"]
    lines.append(
        f"* **成交量**：{money_yi:,.0f} 億（較前一日 {vol_trend}，{colorize_signed(vol_change)}；"
        f"5日均量線 {vol_ma_position_str}，5日均量 {vol_ma_slope_str}）"
    )
    lines.append("")

    lines.append('<div class="idx-flex" markdown="1">')
    lines.append('<div class="idx-col" markdown="1">')
    lines.append("")
    lines.append("**均線與乖離**")
    lines.append("")
    lines.append("| 均線 | 數值 | 斜率 | 位置 | 乖離率 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for p in INDEX_MA_PERIODS:
        m = ma[p]
        b = bias[p]
        if m["val"] is None:
            lines.append(f"| {p}MA | N/A | N/A | N/A | N/A |")
            continue
        slope_str = flag_blue(m["slope"]) if m["slope"] == "下彎" else m["slope"]
        pos_str = flag_blue(m["close_vs_ma"]) if m["close_vs_ma"] == "跌破" else m["close_vs_ma"]
        lines.append(f"| {p}MA | {m['val']:,.0f} | {slope_str} | {pos_str} | {colorize_signed(b)} |")
    lines.append("")
    lines.append('</div>')

    kd_cross_label = {"golden": "黃金交叉", "dead": "死亡交叉", None: "無交叉"}[kd_cross]
    macd_cross_label = {"golden": "黃金交叉", "dead": "死亡交叉", None: "無交叉"}[macd_cross]
    kd_div_label = {"top_bearish": "高檔背離", "bottom_bullish": "低檔背離", None: "無背離"}[kd_divergence]
    macd_div_label = {"top_bearish": "高檔背離", "bottom_bullish": "低檔背離", None: "無背離"}[macd_divergence]
    kd_direction_label = "交叉往上" if k_list[-1] > d_list[-1] else "交叉往下"
    macd_direction_label = "交叉往上" if dif_list[-1] > dea_list[-1] else "交叉往下"

    lines.append('<div class="idx-col" markdown="1">')
    lines.append("")
    lines.append("**動能指標**")
    lines.append("")
    lines.append(f"* **KD**：K={k_list[-1]:.1f}／D={d_list[-1]:.1f}（{kd_cross_label}／{kd_div_label}／{kd_direction_label}）")
    lines.append(f"* **MACD**：DIF={dif_list[-1]:.1f}／DEA={dea_list[-1]:.1f}（{macd_cross_label}／{macd_div_label}／{macd_direction_label}）")
    lines.append("")
    lines.append('</div>')
    lines.append('</div>')
    lines.append("")

    summary = {
        "date": latest["date"],
        "close": latest["close"],
        "spread": spread,
        "change_pct": change_pct,
        "vol_trend": vol_trend,
    }
    return lines, summary


def build_market_stats_section():
    """融資餘額與維持率／三大法人現貨買賣超／外資台指期未平倉，橫向三欄精簡排版。
    回傳 (lines, summary)，summary 供文末的大盤情況總結使用。"""
    lines = ['<div class="idx-flex" markdown="1">']
    summary = {}

    lines.append('<div class="idx-col" markdown="1">')
    lines.append("")
    lines.append("**融資餘額與維持率**")
    lines.append("")
    try:
        twse = fetch_twse_margin_total()
        lines.append(f"* 上市：{twse['today_money'] / 1e8:,.0f} 億（{colorize_signed(twse['change_money'] / 1e8, '{:+,.1f} 億')}）")
        summary["margin_change_twse"] = twse["change_money"]
    except Exception as e:
        lines.append(f"* 上市：抓取失敗 ({e})")
    try:
        tpex = fetch_tpex_margin_total()
        lines.append(f"* 上櫃：{tpex['today_money'] / 1e8:,.0f} 億（{colorize_signed(tpex['change_money'] / 1e8, '{:+,.1f} 億')}）")
        summary["margin_change_tpex"] = tpex["change_money"]
    except Exception as e:
        lines.append(f"* 上櫃：抓取失敗 ({e})")
    try:
        start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        maint = fetch_margin_maintenance_ratio(start_date)
        if maint:
            latest_maint = maint[-1]
            prev_maint = maint[-2] if len(maint) >= 2 else None
            change_str = f"（{colorize_signed(latest_maint['ratio'] - prev_maint['ratio'], '{:+.2f}pp')}）" if prev_maint else ""
            lines.append(f"* 維持率：{latest_maint['ratio']:.2f}%{change_str}")
    except Exception as e:
        lines.append(f"* 維持率：抓取失敗 ({e})")
    lines.append("")
    lines.append('</div>')

    lines.append('<div class="idx-col" markdown="1">')
    lines.append("")
    lines.append("**三大法人現貨買賣超**")
    lines.append("")
    try:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        inst = fetch_institutional_investors_total(start_date)
        if inst:
            lines.append(f"* 外資：{colorize_signed(inst['foreign_net'] / 1e8, '{:+,.1f} 億')}")
            lines.append(f"* 投信：{colorize_signed(inst['investment_trust_net'] / 1e8, '{:+,.1f} 億')}")
            lines.append(f"* 自營商：{colorize_signed(inst['dealer_net'] / 1e8, '{:+,.1f} 億')}")
            lines.append(f"* 合計：{colorize_signed(inst['total_net'] / 1e8, '{:+,.1f} 億')}")
            summary["institutional_total_net"] = inst["total_net"]
        else:
            lines.append("*無法取得資料。*")
    except Exception as e:
        lines.append(f"*抓取失敗 ({e})*")
    lines.append("")
    lines.append('</div>')

    lines.append('<div class="idx-col" markdown="1">')
    lines.append("")
    lines.append("**外資台指期未平倉**")
    lines.append("")
    try:
        start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        futures = fetch_foreign_futures_position(start_date)
        if futures:
            latest = futures[-1]
            prev = futures[-2] if len(futures) >= 2 else None
            long_delta = f"（{colorize_signed(latest['long_oi'] - prev['long_oi'], '{:+,.0f}')}）" if prev else ""
            short_delta = f"（{colorize_signed(latest['short_oi'] - prev['short_oi'], '{:+,.0f}')}）" if prev else ""
            net_delta = f"（{colorize_signed(latest['net_oi'] - prev['net_oi'], '{:+,.0f}')}）" if prev else ""
            lines.append(f"* 多單：{fmt_num(latest['long_oi'])} 口{long_delta}")
            lines.append(f"* 空單：{fmt_num(latest['short_oi'])} 口{short_delta}")
            lines.append(f"* 淨部位：{colorize_signed(latest['net_oi'], '{:+,.0f} 口')}（{'偏多' if latest['net_oi'] > 0 else '偏空'}）{net_delta}")
            summary["futures_net_oi"] = latest["net_oi"]
        else:
            lines.append("*無法取得資料。*")
    except Exception as e:
        lines.append(f"*抓取失敗 ({e})*")
    lines.append("")
    lines.append('</div>')

    lines.append('</div>')
    lines.append("")
    return lines, summary


def build_market_overview_summary(taiex_summary, tpex_summary, stats_summary):
    """大盤情況總結：綜合指數漲跌、三大法人、外資期貨與融資變化，給一段簡短總評。"""
    lines = ["**大盤情況總結**", ""]
    parts = []
    bullish_votes = 0
    bearish_votes = 0

    if taiex_summary:
        up = taiex_summary["change_pct"] >= 0
        bullish_votes += 1 if up else 0
        bearish_votes += 0 if up else 1
        parts.append(f"加權指數{'上漲' if up else '下跌'}{abs(taiex_summary['change_pct']):.2f}%（{taiex_summary['vol_trend']}）")
    if tpex_summary:
        up = tpex_summary["change_pct"] >= 0
        bullish_votes += 1 if up else 0
        bearish_votes += 0 if up else 1
        parts.append(f"櫃買指數{'上漲' if up else '下跌'}{abs(tpex_summary['change_pct']):.2f}%（{tpex_summary['vol_trend']}）")

    total_net = stats_summary.get("institutional_total_net")
    if total_net is not None:
        up = total_net >= 0
        bullish_votes += 1 if up else 0
        bearish_votes += 0 if up else 1
        parts.append(f"三大法人合計{'買超' if up else '賣超'}{abs(total_net) / 1e8:.1f}億")

    net_oi = stats_summary.get("futures_net_oi")
    if net_oi is not None:
        up = net_oi > 0
        bullish_votes += 1 if up else 0
        bearish_votes += 0 if up else 1
        parts.append(f"外資台指期{'偏多' if up else '偏空'}留倉 {abs(net_oi):,.0f} 口")

    margin_twse = stats_summary.get("margin_change_twse")
    margin_tpex = stats_summary.get("margin_change_tpex")
    if margin_twse is not None or margin_tpex is not None:
        total_margin_change = (margin_twse or 0) + (margin_tpex or 0)
        parts.append(f"融資餘額{'增加' if total_margin_change >= 0 else '減少'}")

    if not parts:
        lines.append("*資料不足，無法產生總結。*")
        lines.append("")
        return lines

    if bullish_votes > bearish_votes:
        verdict = "整體偏多"
    elif bearish_votes > bullish_votes:
        verdict = "整體偏空"
    else:
        verdict = "多空訊號不一"

    lines.append("、".join(parts) + f"，{verdict}。")
    lines.append("")
    return lines


def _format_industry_rows(top_industries):
    lines = ["| 排名 | 產業 | 漲跌幅 | 族群內領漲個股 |", "| :--- | :--- | :--- | :--- |"]
    for i, ind in enumerate(top_industries, 1):
        stock_parts = []
        for s in ind["top_stocks"]:
            pct_str = gray_muted(f"({s['change_pct']:+.2f}%)")
            stock_parts.append(f"{s['symbol']}**{s['name']}**{pct_str}")
        stocks_str = " / ".join(stock_parts) or "-"
        lines.append(f"| {i} | {ind['name']} | {colorize_signed(ind['change_pct'], bold=False)} | {stocks_str} |")
    return lines


def build_sector_trend_section():
    lines = ["### 二、股票族群情況", ""]

    for market_label, market_symbol in [("上市", TWSE_SYMBOL), ("上櫃", TPEX_SYMBOL)]:
        lines.append(f"#### {market_label}當日強勢族群 Top{SECTOR_TOP_N_INDUSTRIES}")
        lines.append("")
        try:
            top = top_gaining_industries_with_stocks(
                market_symbol, period=None,
                top_n_industries=SECTOR_TOP_N_INDUSTRIES, top_n_stocks=SECTOR_TOP_N_STOCKS
            )
            if top:
                lines.extend(_format_industry_rows(top))
            else:
                lines.append("*今日無明顯強勢族群。*")
        except Exception as e:
            lines.append(f"*抓取失敗 ({e})*")
        lines.append("")

    lines.append(f"#### 近一週強勢族群 Top{SECTOR_TOP_N_INDUSTRIES_WEEKLY}")
    lines.append("")
    for market_label, market_symbol in [("上市", TWSE_SYMBOL), ("上櫃", TPEX_SYMBOL)]:
        lines.append(f"**{market_label}**")
        lines.append("")
        try:
            top = top_gaining_industries_with_stocks(
                market_symbol, period="1w",
                top_n_industries=SECTOR_TOP_N_INDUSTRIES_WEEKLY, top_n_stocks=SECTOR_TOP_N_STOCKS
            )
            if top:
                lines.extend(_format_industry_rows(top))
            else:
                lines.append(f"*{market_label}近一週無明顯強勢族群。*")
        except Exception as e:
            lines.append(f"*抓取失敗 ({e})*")
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
                highlights.append(f"加碼{mark} {entry['ticker']}{entry['name']}（{colorize_signed(entry['shares_delta'], '{:+,.0f}股')}）")
            top_decreased = sorted(deltas["decreased"], key=lambda e: e["shares_delta"])[:3]
            for entry in top_decreased:
                mark = "［已追蹤］" if entry["ticker"] in tracked_tickers else ""
                highlights.append(f"減碼{mark} {entry['ticker']}{entry['name']}（{colorize_signed(entry['shares_delta'], '{:+,.0f}股')}）")

            summary = "；".join(highlights) if highlights else "無明顯變化"
            lines.append(f"* **{whale_id}**（{whale_date}）：{summary}")
        lines.append("")

    lines.append("#### 共識標的（2位以上大戶同時持有）")
    lines.append("")
    consensus, _ = get_consensus_stocks_latest(min_whales=2)
    if consensus:
        concept_table = load_concept_fpe_table()
        ticker_filepaths = get_tracked_ticker_filepaths()
        target_year = datetime.now().year + 1

        lines.append('<div class="whale-consensus" markdown="1">')
        lines.append("")
        lines.append("| 股票 | 當前價格 | 持有大戶 | 總市值 | 目標價上緣 | 買進/加碼提醒 | 賣出/減碼提醒 |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for c in consensus:
            ticker = c["ticker"]
            tech = None
            if not is_foreign_listing(ticker):
                tech = compute_technical_signals(ticker)

            current_price_str = f"{tech['current_price']:.2f}" if tech else "-"

            buy_str, sell_str = "-", "-"
            if tech:
                buy_reasons = format_5ma_strategy_reasons(tech) + format_60ma_support_reason(tech)
                if buy_reasons:
                    buy_str = "/".join(flag_red(text) for text, _ in buy_reasons)
                sell_reasons = format_sell_reasons(tech)
                if sell_reasons:
                    sell_str = "/".join(sell_reasons)

            target_upper_str = "-"
            filepath = ticker_filepaths.get(ticker)
            if filepath and tech and tech["current_price"]:
                target_eps = parse_target_eps(filepath, target_year)
                fpe_range = get_fpe_range_for_ticker(ticker, concept_table)
                if target_eps is not None and target_eps > 0 and fpe_range is not None:
                    target_price_upper = target_eps * fpe_range["high"]
                    proi = (target_price_upper / tech["current_price"] - 1) * 100
                    target_upper_str = f"TP {target_price_upper:,.0f}<br>(PROI {colorize_signed(proi, '{:+.0f}%')})"

            whale_letters = "、".join(w.replace("大戶", "") for w in c["whale_ids"])
            whale_combined = f"{whale_letters}({c['whale_count']}位)"
            market_value_yi = f"{c['total_market_value'] / 1e8:.1f} 億"
            lines.append(
                f"| {ticker}<br>{c['name']} | {current_price_str} | {whale_combined} | "
                f"{market_value_yi} | {target_upper_str} | {buy_str} | {sell_str} |"
            )
        lines.append("")
        lines.append('</div>')
    else:
        lines.append("*目前無2位以上大戶同時持有的共識標的。*")
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
        if is_foreign_listing(ticker):
            continue
        sig = compute_stock_signal(ticker, fp, target_year, concept_table)
        if sig:
            sig["name"] = name
            sig["filepath"] = fp
            results.append(sig)

    buy_list = sorted(
        (r for r in results if r["signal"] == "BUY"),
        key=lambda r: r["expected_value_pct"], reverse=True
    )
    sell_list = sorted(
        (r for r in results if r["signal"] == "SELL"),
        key=lambda r: r["expected_value_pct"] if r["expected_value_pct"] is not None else 999
    )

    lines.append(
        f"#### 買進訊號（五日線戰法 EV>{BUY_EV_THRESHOLD_5MA_STRATEGY:.0f}% 或 急跌至長線支撐 EV>{BUY_EV_THRESHOLD_60MA_SUPPORT:.0f}%）"
    )
    lines.append("")
    if buy_list:
        lines.append("| 股票 | 現價 | 目標價 | 期望值 | 均線評分 | 乖離評分 | 觸發原因 | 投資簡述 |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in buy_list:
            reason_parts = [
                flag_red(reason) if (r["highlight_first_day"] and "首日站上" in reason) else reason
                for reason in r["reasons"]
            ]
            reason_str = "；".join(reason_parts) if reason_parts else "-"
            blurb = extract_investment_blurb(r["filepath"]) or "-"
            lines.append(
                f"| {r['ticker']}{r['name']} | {r['current_price']:.2f} | {r['target_price']:.2f} | "
                f"{colorize_signed(r['expected_value_pct'])} | {short_rating_badge(r['ma_rating'])} | "
                f"{short_rating_badge(r['bias_rating'])} | {reason_str} | {blurb} |"
            )
    else:
        lines.append("*今日無符合門檻的買進訊號。*")
    lines.append("")

    lines.append(
        f"#### 賣出/減碼訊號（期望值<{SELL_EV_THRESHOLD_TRIM:.0f}% 或 期望值<{SELL_EV_THRESHOLD_BREAK_5MA:.0f}%且跌破5日線）"
    )
    lines.append("")
    if sell_list:
        lines.append("| 股票 | 現價 | 目標價 | 期望值 | 均線評分 | 乖離評分 | 觸發原因 |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in sell_list:
            target_price_str = f"{r['target_price']:.2f}" if r['target_price'] is not None else "待補充"
            ev_str = colorize_signed(r['expected_value_pct']) if r['expected_value_pct'] is not None else "待補充"
            reason_str = "；".join(r["reasons"]) if r["reasons"] else "-"
            lines.append(
                f"| {r['ticker']}{r['name']} | {r['current_price']:.2f} | {target_price_str} | "
                f"{ev_str} | {short_rating_badge(r['ma_rating'])} | {short_rating_badge(r['bias_rating'])} | {reason_str} |"
            )
    else:
        lines.append("*今日無觸發賣出/減碼條件的個股。*")
    lines.append("")

    no_fpe_cnt = sum(1 for r in results if r["fpe_range"] is None)
    lines.append(
        f"> **註**：目標價 = 隔年({target_year})預估EPS × 所屬概念股FPE中緣（同屬多個概念取平均，"
        f"見 `[[概念股FPE合理區間]]`）；期望值 = (目標價/現價 - 1)。不含非台股標的（如 .SH/.HK）。"
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
    report.append(f"# 宇宙資本盤後日報 {today_str}")
    report.append("### 一、大盤情況")
    report.append("")

    taiex_lines, taiex_summary = build_index_section("上市加權指數 (TAIEX)", "TAIEX")
    report.extend(taiex_lines)

    tpex_lines, tpex_summary = build_index_section("上櫃指數 (TPEx)", "TPEx")
    report.extend(tpex_lines)

    report.append("---")
    report.append("")
    stats_lines, stats_summary = build_market_stats_section()
    report.extend(stats_lines)

    report.append("---")
    report.append("")
    report.extend(build_market_overview_summary(taiex_summary, tpex_summary, stats_summary))

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

    render_markdown_to_pdf(report, OUTPUT_DIR, filename_stem, extra_css=DAILY_REPORT_EXTRA_CSS)

    return output_path


if __name__ == "__main__":
    generate_report()
