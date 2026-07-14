"""
生成盤後大盤日報 (DailyReport)。五大區塊：
一、大盤情況　二、族群強度（含連N日上榜延續性）　三、大戶籌碼（共識表賣出提醒有EV閘門）
四、個股買賣訊號（估值EPS年度模式可調、BUY表含動能分數與轉強置頂）　五、動能篩選重點（含分數變化/連續上榜）

用法：
    python generate_daily_report.py [YYYY-MM-DD]

若不帶日期參數，預設抓最新一個交易日的資料。
"""
import csv
import glob
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
    fetch_market_breadth,
    compute_market_score,
    load_market_score_settings,
    INDEX_MA_PERIODS,
)
from lib.stock_signals import (
    load_concept_fpe_table,
    load_valuation_mode,
    get_fpe_range_for_ticker,
    compute_stock_signal,
    compute_technical_signals,
    format_5ma_strategy_reasons,
    format_20ma_support_reason,
    format_60ma_support_reason,
    format_sell_reasons,
    extract_investment_blurb,
    is_foreign_listing,
    BUY_EV_THRESHOLD_5MA_STRATEGY,
    BUY_EV_THRESHOLD_20MA_SUPPORT,
    BUY_EV_THRESHOLD_60MA_SUPPORT,
    SELL_EV_THRESHOLD_TRIM,
    SELL_EV_THRESHOLD_BREAK_5MA,
)
from lib.stock_metrics import parse_valuation_eps
from lib.history_tracking import record_sector_strength, sector_streaks
from lib.whale_tracking import (
    get_latest_snapshot_per_whale,
    compute_position_deltas,
    get_consensus_stocks_latest,
)
from lib.sector_trend import top_gaining_industries_with_stocks, TWSE_SYMBOL, TPEX_SYMBOL
from lib.report_pdf import render_markdown_to_pdf
from lib.financial_screen import _parse_markdown_table
from lib.report_style import (
    fmt_pct,
    fmt_num,
    colorize,
    colorize_signed,
    flag_red,
    flag_green,
    flag_blue,
    flag_purple,
)

OUTPUT_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Daily_Report"
STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"
MOMENTUM_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Momentum_Screen"

SECTOR_TOP_N_INDUSTRIES = 3
SECTOR_TOP_N_INDUSTRIES_WEEKLY = 5
SECTOR_TOP_N_STOCKS = 5
MOMENTUM_TOP_N_CONCEPTS = 3
MOMENTUM_TOP_N_STOCKS = 10
MOMENTUM_HIGHLIGHT_MIN = 80        # BUY表「轉強高動能」置頂標記所需的動能分數下限

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
    .ma5-label { color: #f59e0b; }
    .ma20-label { color: #7c3aed; }
    .ma60-label { color: #0d9488; }
    .whale-consensus table th:nth-child(5),
    .whale-consensus table td:nth-child(5) {
        min-width: 100px;
    }
    .stock-sell-table table th:nth-child(1), .stock-sell-table table td:nth-child(1) {
        min-width: 78px;
        white-space: nowrap;
    }
    .stock-sell-table table th:nth-child(3), .stock-sell-table table td:nth-child(3) {
        min-width: 110px;
    }
    .stock-sell-table table th:nth-child(4), .stock-sell-table table td:nth-child(4),
    .stock-sell-table table th:nth-child(5), .stock-sell-table table td:nth-child(5) {
        width: 45px;
    }
    .stock-sell-table table th:nth-child(6), .stock-sell-table table td:nth-child(6) {
        min-width: 160px;
    }
    .stock-buy-table table th:nth-child(1), .stock-buy-table table td:nth-child(1) {
        min-width: 78px;
        white-space: nowrap;
    }
    .stock-buy-table table th:nth-child(3), .stock-buy-table table td:nth-child(3) {
        min-width: 110px;
    }
    .stock-buy-table table th:nth-child(4), .stock-buy-table table td:nth-child(4),
    .stock-buy-table table th:nth-child(5), .stock-buy-table table td:nth-child(5),
    .stock-buy-table table th:nth-child(6), .stock-buy-table table td:nth-child(6) {
        width: 45px;
    }
    .stock-buy-table table th:nth-child(7), .stock-buy-table table td:nth-child(7) {
        min-width: 140px;
    }
    .stock-buy-table table th:nth-child(8), .stock-buy-table table td:nth-child(8) {
        min-width: 160px;
    }
    .momentum-stock-table table th:nth-child(1), .momentum-stock-table table td:nth-child(1) {
        min-width: 78px;
        white-space: nowrap;
    }
    .momentum-stock-table table th:nth-child(2), .momentum-stock-table table td:nth-child(2) {
        min-width: 92px;
        white-space: nowrap;
    }
    .momentum-stock-table table th:nth-child(3), .momentum-stock-table table td:nth-child(3) {
        width: 45%;
    }
    .sector-trend-table table th:nth-child(1), .sector-trend-table table td:nth-child(1) {
        width: 30px;
    }
    .sector-trend-table table th:nth-child(2), .sector-trend-table table td:nth-child(2) {
        width: 48px;
        white-space: nowrap;
    }
    .sector-trend-table table th:nth-child(3), .sector-trend-table table td:nth-child(3) {
        width: 42px;
    }
    .sector-trend-table table th:nth-child(4), .sector-trend-table table td:nth-child(4) {
        width: 55%;
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


BREAK_5MA_NOTE = "，且已跌破5日線"


def highlight_break_5ma_note(text):
    """賣出/減碼觸發原因若提到「且已跌破5日線」，把這段子字串標成綠色（本報告「漲橘跌綠」慣例），
    凸顯這是額外確認的技術面弱勢訊號，而非只有期望值偏低。"""
    return text.replace(BREAK_5MA_NOTE, flag_green(BREAK_5MA_NOTE))


def ma_label(period):
    """均線週期標籤上色：5MA橘黃色、20MA紫色、60MA湖水綠，其餘週期不上色。"""
    cls = {5: "ma5-label", 20: "ma20-label", 60: "ma60-label"}.get(period)
    if not cls:
        return f"{period}MA"
    return f'<span class="{cls}">{period}MA</span>'


def short_rating_badge(rating_text):
    """把「均線評分佳/普通/差」類的完整敘述簡化為單一「差」或「佳」並上色
    （差=綠色、佳=亮橘紅色，比照本報告「漲橘跌綠」配色慣例）。"""
    short = "差" if "差" in rating_text else "佳"
    return colorize(short, is_up=(short == "佳"))


def build_index_section(title, index_id, lookback_days=200):
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    ohlc = fetch_index_history(index_id, start_date)
    if not ohlc:
        return [f"#### {title}", "*無法取得資料。*", ""], None

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
    prev_money_yi = (ohlc[-2].get("money") or 0) / 1e8 if len(ohlc) >= 2 else None

    lines = [f"#### {title}", ""]
    lines.append(
        f"* **收盤價**：{latest['close']:,.2f}（{colorize_signed(spread, '{:+,.2f}')}，{colorize_signed(change_pct)}）"
    )
    vol_ma_position_str = colorize(vol_ma["position"], is_up=(vol_ma["position"] == "站上"))
    vol_ma_slope_str = colorize(vol_ma["slope"], is_up=(vol_ma["slope"] == "上彎"))
    prev_money_str = f"{prev_money_yi:,.0f}億" if prev_money_yi is not None else "N/A"
    lines.append(
        f"* **成交量**：{money_yi:,.0f} 億（較前日 {prev_money_str}{vol_trend} {colorize_signed(vol_change)}；"
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
            lines.append(f"| {ma_label(p)} | N/A | N/A | N/A | N/A |")
            continue
        slope_str = colorize(m["slope"], is_up=(m["slope"] == "上彎"))
        pos_str = colorize(m["close_vs_ma"], is_up=(m["close_vs_ma"] == "漲過"))
        lines.append(f"| {ma_label(p)} | {m['val']:,.0f} | {slope_str} | {pos_str} | {colorize_signed(b)} |")
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
        "ma": ma,
        "bias": bias,
        "vol_ma": vol_ma,
        "kd_direction": kd_direction_label,
        "macd_direction": macd_direction_label,
        "kd_divergence": kd_divergence,
        "macd_divergence": macd_divergence,
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
            # FinMind TaiwanTotalExchangeMarginMaintenance 與 MacroMicro 圖表53117(市場慣用參考來源)
            # 口徑不同（分子是否計入ETF等未知），Lucas 對過15個交易日後，觀察到穩定落差約25.5pp，
            # 因此在這裡扣減校正，讓顯示值貼近市場慣用的 MacroMicro 數字。這是經驗校正值，非官方
            # 換算公式；若 Lucas 回報數字對不上，第一件事應該是重新比對這個 25.5 是否還成立。
            MACROMICRO_ADJUSTMENT = -25.5
            for row in maint:
                row["ratio"] = round(row["ratio"] + MACROMICRO_ADJUSTMENT, 1)
            latest_maint = maint[-1]
            prev_maint = maint[-2] if len(maint) >= 2 else None
            change_str = f"（{colorize_signed(latest_maint['ratio'] - prev_maint['ratio'], '{:+.1f}pp')}）" if prev_maint else ""
            lines.append(f"* 維持率：{latest_maint['ratio']:.1f}%{change_str}")
            summary["margin_maintenance_ratio"] = latest_maint["ratio"]
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
            if prev:
                summary["futures_short_oi_change"] = latest["short_oi"] - prev["short_oi"]
        else:
            lines.append("*無法取得資料。*")
    except Exception as e:
        lines.append(f"*抓取失敗 ({e})*")
    lines.append("")
    lines.append('</div>')

    lines.append('</div>')
    lines.append("")
    return lines, summary


def build_breadth_section(date, results):
    """全市場漲跌/漲跌停家數（FinMind批次查詢，見 fetch_market_breadth）＋資料庫個股
    月線(20MA)以上家數（沿用「四、個股買賣訊號」已計算好的 results，不重複抓價）。
    回傳 (lines, breadth_summary)：breadth_summary 供大盤技術分析評分的市場寬度規則使用，
    key 為 market_up/market_down/db_above_ma20_pct，缺資料時對應鍵不存在。"""
    lines = ['<div class="idx-flex" markdown="1">']
    breadth_summary = {}
    lines.append('<div class="idx-col" markdown="1">')
    lines.append("")
    lines.append("**全市場漲跌與漲跌停家數**")
    lines.append("")
    try:
        breadth = fetch_market_breadth(date)
        breadth_summary["market_up"] = breadth["up"]
        breadth_summary["market_down"] = breadth["down"]
        lines.append(
            f"* 上漲：{colorize(fmt_num(breadth['up']), is_up=True)} 家　"
            f"下跌：{colorize(fmt_num(breadth['down']), is_up=False)} 家　平盤：{fmt_num(breadth['flat'])} 家"
        )
        lines.append(
            f"* 漲停：{colorize(fmt_num(breadth['limit_up']), is_up=True)} 家　"
            f"跌停：{colorize(fmt_num(breadth['limit_down']), is_up=False)} 家"
        )
    except Exception as e:
        lines.append(f"*抓取失敗 ({e})*")
    lines.append("")
    lines.append('</div>')

    lines.append('<div class="idx-col" markdown="1">')
    lines.append("")
    lines.append("**資料庫個股月線(20MA)以上家數**")
    lines.append("")
    sufficient = [r for r in results if r.get("current_price")]
    if sufficient:
        above = sum(1 for r in sufficient if r.get("above_ma20"))
        total = len(sufficient)
        pct = above / total * 100 if total else 0
        breadth_summary["db_above_ma20_pct"] = pct
        lines.append(f"* {colorize(f'{pct:.0f}%', is_up=(pct >= 50))} （{above} / {total} 檔）")
    else:
        lines.append("*資料不足。*")
    lines.append("")
    lines.append('</div>')
    lines.append('</div>')
    lines.append("")
    return lines, breadth_summary


def market_score_tier(score, settings=None):
    """依大盤分數換算級距標籤：<=弱勢門檻 弱勢、~強勢門檻 一般、~超級強勢門檻 強勢、
    >超級強勢門檻 超級強勢。門檻數字讀自 `[[大盤分數計算方式]]`（見 load_market_score_settings）。"""
    if settings is None:
        settings = load_market_score_settings()
    weak, strong, super_ = settings["tier_weak"], settings["tier_strong"], settings["tier_super"]
    if score <= weak:
        return "弱勢"
    elif score < strong:
        return "一般"
    elif score <= super_:
        return "強勢"
    else:
        return "超級強勢"


def build_market_overview_summary(taiex_summary, tpex_summary, stats_summary):
    """「大盤技術分析評分」段落：以加權指數為基準的量化評分＋加分/扣分項。
    （2026-07-14 起移除原本後接的「大盤情況總結」文字段落，只保留本評分區塊。）"""
    lines = []
    if not taiex_summary:
        lines.append("*資料不足，無法計算大盤技術分析評分。*")
        lines.append("")
        return lines

    settings = load_market_score_settings()
    score, reasons, notes = compute_market_score(taiex_summary, stats_summary, settings=settings)
    tier = market_score_tier(score, settings=settings)
    gain_reasons = [text for text, delta in reasons if delta > 0]
    loss_reasons = [text for text, delta in reasons if delta < 0]
    lines.append(flag_blue(f"**大盤技術分析評分：{score} 分（{tier}）**"))
    lines.append("")
    for note in notes:
        lines.append(flag_purple(note))
        lines.append("")
    lines.append(f"{flag_red('加分')}：{' | '.join(gain_reasons) if gain_reasons else '無'}")
    lines.append("")
    lines.append(f"{flag_green('扣分')}：{' | '.join(loss_reasons) if loss_reasons else '無'}")
    lines.append("")
    return lines


def _qualifying_leader_parts(ind):
    """族群內漲幅超越產業漲幅的領漲個股顯示片段；不足兩檔時該產業不具「族群性」不顯示。"""
    parts = []
    for s in ind["top_stocks"]:
        if s["change_pct"] <= ind["change_pct"]:
            continue
        parts.append(f"{s['symbol']}**{s['name']}**({s['change_pct']:+.2f}%)")
    return parts


def _format_industry_rows(top_industries, streaks=None):
    """streaks: {產業名: 連續上榜天數}，>=2 天才顯示徽章（第1天沒有延續性可言），
    一律換行後紅字顯示「連N日」凸顯延續性。"""
    lines = ['<div class="sector-trend-table" markdown="1">', "",
             "| 排名 | 產業 | 漲跌幅 | 族群內領漲個股 |", "| :--- | :--- | :--- | :--- |"]
    rank = 0
    for ind in top_industries:
        stock_parts = _qualifying_leader_parts(ind)
        if len(stock_parts) < 2:
            continue
        rank += 1
        badge = ""
        if streaks:
            n = streaks.get(ind["name"], 0)
            if n >= 2:
                badge = f"<br>{flag_red(f'連{n}日')}"
        stocks_str = " / ".join(stock_parts)
        lines.append(f"| {rank} | {ind['name']}{badge} | {colorize_signed(ind['change_pct'], bold=False)} | {stocks_str} |")
    lines.append("")
    lines.append('</div>')
    return lines


def build_sector_trend_section():
    lines = ["### 二、股票族群情況", ""]
    today_str = datetime.now().strftime("%Y-%m-%d")

    for market_label, market_symbol in [("上市", TWSE_SYMBOL), ("上櫃", TPEX_SYMBOL)]:
        lines.append(f"#### {flag_blue(f'{market_label}當日強勢族群 Top{SECTOR_TOP_N_INDUSTRIES}')}")
        lines.append("")
        try:
            top = top_gaining_industries_with_stocks(
                market_symbol, period=None,
                top_n_industries=SECTOR_TOP_N_INDUSTRIES, top_n_stocks=SECTOR_TOP_N_STOCKS
            )
            if top:
                # 只把「有顯示出來」的族群寫入歷史（與報告呈現一致），再回頭算連續上榜天數
                displayed = [ind for ind in top if len(_qualifying_leader_parts(ind)) >= 2]
                record_sector_strength(today_str, market_label, displayed)
                streaks = sector_streaks(market_label)
                lines.extend(_format_industry_rows(top, streaks))
            else:
                lines.append("*今日無明顯強勢族群。*")
        except Exception as e:
            lines.append(f"*抓取失敗 ({e})*")
        lines.append("")

    lines.append(f"#### {flag_blue(f'近一週強勢族群 Top{SECTOR_TOP_N_INDUSTRIES_WEEKLY}')}")
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
    lines.append(f"#### {flag_blue('各大戶當日買進/賣出重點')}")
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
                    f"* **{whale_id}**（{whale_date}）：尚無前次快照可比較"
                    f"（共 {holdings_cnt} 檔持股，總市值 {deltas['total_value_now']:,.0f}）"
                )
                continue

            highlights = []
            for entry in deltas["new"]:
                mark = "［已追蹤］" if entry["ticker"] in tracked_tickers else ""
                highlights.append(flag_red(f"新建倉{mark} {entry['ticker']}{entry['name']}（市值 {entry['market_value']:,.0f}）"))
            for entry in deltas["closed"]:
                mark = "［已追蹤］" if entry["ticker"] in tracked_tickers else ""
                highlights.append(flag_green(f"出清{mark} {entry['ticker']}{entry['name']}"))

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

    lines.append(f"#### {flag_blue('共識標的（2位以上大戶同時持有）')}")
    lines.append("")
    consensus, _ = get_consensus_stocks_latest(min_whales=2)
    if consensus:
        concept_table = load_concept_fpe_table()
        valuation_mode = load_valuation_mode()
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

            # 先算估值期望值，後面的賣出提醒要拿它當閘門
            target_upper_str = "-"
            proi = None
            filepath = ticker_filepaths.get(ticker)
            if filepath and tech and tech["current_price"]:
                target_eps = parse_valuation_eps(filepath, target_year, valuation_mode)
                fpe_range = get_fpe_range_for_ticker(ticker, concept_table)
                if target_eps is not None and target_eps > 0 and fpe_range is not None:
                    fpe_used = fpe_range["high"]
                    target_price_upper = target_eps * fpe_used
                    proi = (target_price_upper / tech["current_price"] - 1) * 100
                    target_upper_str = (
                        f"TP {target_price_upper:,.0f}<br>"
                        f"({fpe_used:.0f}x EPS {target_eps:.1f})<br>"
                        f"(期望值 {colorize_signed(proi, '{:+.0f}%')})"
                    )

            buy_str, sell_str = "-", "-"
            if tech:
                buy_reasons = (format_5ma_strategy_reasons(tech) + format_20ma_support_reason(tech)
                               + format_60ma_support_reason(tech))
                if buy_reasons:
                    buy_str = "<br>".join(flag_red(text) for text, _ in buy_reasons)
                sell_reasons = format_sell_reasons(tech)
                if sell_reasons:
                    if proi is not None and proi > SELL_EV_THRESHOLD_TRIM:
                        # 期望值仍高的股票，技術轉弱降級為中性的「回檔觀察」——
                        # 基本面沒變差、只是技術回檔的持股，不該被純技術雜訊嚇出場
                        sell_str = f"回檔觀察：<br>{'、'.join(sell_reasons)}"
                    else:
                        sell_str = "<br>".join(sell_reasons)

            whale_letters = "、".join(w.replace("大戶", "") for w in c["whale_ids"])
            whale_combined = f"{whale_letters} ({c['whale_count']}位)"
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


MOMENTUM_SCORES_CSV_PATH = r"C:\Users\User\Desktop\LucasBrain\.agent\data\momentum_scores_latest.csv"


def _load_latest_momentum_scores():
    """讀取 scan_momentum_score.py 每次執行覆蓋寫出的完整分數快照 {ticker: 動能分數}——
    不透過 Momentum_Screen 報告裡「資料庫個股動能排行」表格，因為那張表只列出達
    顯示門檻(預設>=80分)的個股，BUY訊號股只要分數<80就查不到，會誤顯示「-」讓人
    誤以為沒算過動能分數。查不到的 ticker 代表真的未被掃描到（例如流動性門檻排除），
    才顯示 '-'。"""
    if not os.path.exists(MOMENTUM_SCORES_CSV_PATH):
        return {}
    scores = {}
    with open(MOMENTUM_SCORES_CSV_PATH, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                scores[row["ticker"]] = float(row["total_score"])
            except (ValueError, KeyError):
                continue
    return scores


def compute_all_stock_signals():
    """對 10_Stocks/ 全部個股計算買進/賣出訊號，回傳 results 清單。獨立成函式是因為
    「一、大盤情況」的月線以上家數統計與「四、個股買賣訊號」需要共用同一組計算結果，
    避免同一份資料重複計算兩次（每檔都要抓歷史股價，重算一次成本不低）。"""
    concept_table = load_concept_fpe_table()
    valuation_mode = load_valuation_mode()
    target_year = datetime.now().year + 1
    momentum_scores = _load_latest_momentum_scores()

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
        sig = compute_stock_signal(ticker, fp, target_year, concept_table, valuation_mode)
        if sig:
            sig["name"] = name
            sig["filepath"] = fp
            sig["momentum_score"] = momentum_scores.get(ticker)
            # 轉強高動能：技術面剛轉強（首日站上5MA/扣抵偏低）且動能分數達標，最值得優先看
            sig["breakout_momentum"] = bool(
                sig["breakout"] and sig["momentum_score"] is not None
                and sig["momentum_score"] >= MOMENTUM_HIGHLIGHT_MIN
            )
            results.append(sig)
    return results, valuation_mode


def build_stock_signals_section(results, valuation_mode):
    lines = ["### 四、資料庫個股買進/賣出訊號", ""]

    lines.append(f"估值模式：**{valuation_mode}EPS × FPE上緣**（於 `[[概念股FPE合理區間]]` 的「目標價估值設定」表調整）")
    lines.append("")

    buy_list = sorted(
        (r for r in results if r["signal"] == "BUY"),
        key=lambda r: (r["breakout_momentum"], r["expected_value_pct"]), reverse=True
    )
    sell_list = sorted(
        (r for r in results if r["signal"] == "SELL"),
        key=lambda r: r["expected_value_pct"] if r["expected_value_pct"] is not None else 999
    )

    lines.append(
        f"#### {flag_blue(f'買進訊號（五日線戰法 EV>{BUY_EV_THRESHOLD_5MA_STRATEGY:.0f}% / 回測上升月線 EV>{BUY_EV_THRESHOLD_20MA_SUPPORT:.0f}% / 急跌至上升季線 EV>{BUY_EV_THRESHOLD_60MA_SUPPORT:.0f}%）')}"
    )
    lines.append("")
    if buy_list:
        lines.append('<div class="stock-buy-table" markdown="1">')
        lines.append("")
        lines.append("| 股票 | 現價 | 目標價上緣 | 動能 | 均線 | 乖離 | 觸發原因 | 投資簡述 |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in buy_list:
            reason_parts = [
                flag_red(reason) if (
                    (r["highlight_first_day"] and "首日站上" in reason) or "扣抵偏低" in reason
                ) else reason
                for reason in r["reasons"]
            ]
            if r["breakout_momentum"]:
                reason_parts.insert(0, flag_red("轉強高動能"))
            reason_str = "<br>".join(reason_parts) if reason_parts else "-"
            momentum_str = f"{r['momentum_score']:.0f}" if r["momentum_score"] is not None else "-"
            blurb = extract_investment_blurb(r["filepath"]) or "-"
            fpe_used = r["fpe_range"]["high"] if r["fpe_range"] else None
            if fpe_used is not None and r["target_eps"] is not None:
                target_str = (
                    f"TP {r['target_price']:,.0f}<br>"
                    f"({fpe_used:.0f}x EPS {r['target_eps']:.1f})<br>"
                    f"(期望值 {colorize_signed(r['expected_value_pct'], '{:+.0f}%')})"
                )
            else:
                target_str = f"TP {r['target_price']:,.0f}"
            lines.append(
                f"| {r['ticker']}<br>{r['name']} | {r['current_price']:.2f} | {target_str} | "
                f"{momentum_str} | {short_rating_badge(r['ma_rating'])} | "
                f"{short_rating_badge(r['bias_rating'])} | {reason_str} | {blurb} |"
            )
        lines.append("")
        lines.append("</div>")
    else:
        lines.append("*今日無符合門檻的買進訊號。*")
    lines.append("")

    lines.append(
        f"#### {flag_blue(f'賣出/減碼訊號（期望值<{SELL_EV_THRESHOLD_TRIM:.0f}% 或 期望值<{SELL_EV_THRESHOLD_BREAK_5MA:.0f}%且跌破5日線）')}"
    )
    lines.append("")
    if sell_list:
        lines.append('<div class="stock-sell-table" markdown="1">')
        lines.append("")
        lines.append("| 股票 | 現價 | 目標價上緣 | 均線 | 乖離 | 觸發原因 |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in sell_list:
            fpe_used = r["fpe_range"]["high"] if r["fpe_range"] else None
            if r["target_price"] is not None and fpe_used is not None and r["target_eps"] is not None:
                target_str = (
                    f"TP {r['target_price']:,.0f}<br>"
                    f"({fpe_used:.0f}x EPS {r['target_eps']:.1f})<br>"
                    f"(期望值 {colorize_signed(r['expected_value_pct'], '{:+.0f}%')})"
                )
            elif r["target_price"] is not None:
                target_str = f"TP {r['target_price']:,.0f}"
            else:
                target_str = "待補充"
            reason_str = "<br>".join(highlight_break_5ma_note(reason) for reason in r["reasons"]) if r["reasons"] else "-"
            lines.append(
                f"| {r['ticker']}<br>{r['name']} | {r['current_price']:.2f} | {target_str} | "
                f"{short_rating_badge(r['ma_rating'])} | {short_rating_badge(r['bias_rating'])} | {reason_str} |"
            )
        lines.append("")
        lines.append("</div>")
    else:
        lines.append("*今日無觸發賣出/減碼條件的個股。*")
    lines.append("")

    return lines


def build_momentum_section():
    """讀取 scan_momentum_score.py 產出的最新一份 Momentum_Screen 報告，摘要前幾名熱門
    題材與動能股。「連N日／新進榜／分數變化」現在是該報告自己內嵌好的資訊（見
    lib/momentum_screen.py 的 load_momentum_history 相關函式，由 scan_momentum_score.py
    在寫檔當下算好），這裡單純讀取最新一份、依 MOMENTUM_TOP_N_* 篩前幾名顯示，
    不再自己解析多份歷史報告重算一次——避免同一套邏輯兩處維護、數字對不上的風險。"""
    lines = ["### 五、動能篩選重點", ""]

    candidates = sorted(glob.glob(os.path.join(MOMENTUM_DIR, "*_動能篩選.md")))
    if not candidates:
        lines.append("*尚無動能篩選報告，請先執行 `scan_momentum_score.py`（或等待每日 15:00 排程執行）。*")
        lines.append("")
        return lines

    latest_path = candidates[-1]
    filename_stem = os.path.splitext(os.path.basename(latest_path))[0]
    report_date = filename_stem[:8]
    report_date_fmt = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:8]}"
    today_str = datetime.now().strftime("%Y-%m-%d")

    staleness_note = ""
    if report_date_fmt != today_str:
        staleness_note = f"（{flag_red('非當日資料')}，最新一份為 {report_date_fmt}，可能是當天 15:00 排程未執行成功，請檢查 `.agent/scheduled_logs/`）"

    lines.append(f"完整報告見 `[[{filename_stem}]]`{staleness_note}")
    lines.append("")

    with open(latest_path, "r", encoding="utf-8") as f:
        md_lines = f.read().split("\n")
    concept_rows = _parse_markdown_table(md_lines, lambda cols: cols[:3] == ['分類', '平均分數', '最高分成員'])
    stock_rows = _parse_markdown_table(md_lines, lambda cols: cols[:3] == ['股票', '動能分數', '通過指標'])

    if concept_rows:
        lines.append(f"#### {flag_blue(f'熱門題材/產業位置（前{MOMENTUM_TOP_N_CONCEPTS}名）')}")
        lines.append("")
        lines.append("| 分類 | 平均分數 | 最高分成員 |")
        lines.append("| :--- | :--- | :--- |")
        for row in concept_rows[:MOMENTUM_TOP_N_CONCEPTS]:
            lines.append(f"| {row['分類']} | {row['平均分數']} | {row['最高分成員']} |")
        lines.append("")

    if stock_rows:
        lines.append(f"#### {flag_blue(f'資料庫個股動能排行（前{MOMENTUM_TOP_N_STOCKS}名）')}")
        lines.append("")
        lines.append('<div class="momentum-stock-table" markdown="1">')
        lines.append("")
        lines.append("| 股票 | 動能分數 | 通過指標 |")
        lines.append("| :--- | :--- | :--- |")
        for row in stock_rows[:MOMENTUM_TOP_N_STOCKS]:
            lines.append(f"| {row['股票']} | {row['動能分數']} | {row['通過指標']} |")
        lines.append("")
        lines.append('</div>')
        lines.append("")

    if not concept_rows and not stock_rows:
        lines.append("*最新一份動能篩選報告目前沒有符合門檻的標的。*")
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
    report.append(f"# 宇宙資本-盤後日報 {today_str}")
    report.append("")
    report.append("")
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

    # 個股買賣訊號只算一次，「一、大盤情況」的月線以上家數統計與「四、個股買賣訊號」表格共用同一份結果
    stock_signal_results, valuation_mode = compute_all_stock_signals()

    report.append("---")
    report.append("")
    breadth_date = (taiex_summary or {}).get("date") or today_str
    breadth_lines, breadth_summary = build_breadth_section(breadth_date, stock_signal_results)
    report.extend(breadth_lines)
    stats_summary.update(breadth_summary)

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
    report.extend(build_stock_signals_section(stock_signal_results, valuation_mode))

    report.append('<div class="step-page-break"></div>')
    report.append("")
    report.extend(build_momentum_section())

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
