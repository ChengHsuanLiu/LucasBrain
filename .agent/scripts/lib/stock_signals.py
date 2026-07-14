"""
個股技術面訊號與買進/賣出訊號計算模組。

`compute_technical_signals()` 是純技術面訊號 (不含估值期望值)，供「三、主力大戶
共識標的」的買賣提醒與「四、資料庫個股買進/賣出訊號」共用：
- 五日線戰法：已站上5日線 (首日站上特別標註) 或 5日線扣抵值偏低現價一定幅度以內
- 回測月線支撐：現價貼近上升中的20日均線
- 急跌至季線支撐：現價貼近上升中的60日均線
- 賣出提醒：跌破5日線 / 5日線下彎 / 月線下彎

`compute_stock_signal()` 疊加估值面 (估值EPS x 概念股FPE上緣算出目標價與期望值%)，
估值EPS依 load_valuation_mode() 的模式取明年或明年後年平均。三種買進訊號都需要
期望值門檻 + 對應技術面觸發同時成立；兩種賣出訊號則只看期望值。
"""
import os
import re

from .stock_metrics import (
    get_historical_prices_fallback,
    compute_ma_metrics,
    compute_tactical_score,
    parse_target_eps,
    parse_valuation_eps,
)
from .financial_screen import _parse_markdown_table

STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"
FPE_TABLE_PATH = r"C:\Users\User\Desktop\LucasBrain\97_Settings\概念股FPE合理區間.md"
SIGNAL_THRESHOLDS_PATH = r"C:\Users\User\Desktop\LucasBrain\97_Settings\個股買賣訊號門檻.md"

_SIGNAL_THRESHOLD_DEFAULTS = {
    "五日線戰法期望值門檻(%)": ("BUY_EV_THRESHOLD_5MA_STRATEGY", 60.0),
    "回測月線期望值門檻(%)": ("BUY_EV_THRESHOLD_20MA_SUPPORT", 70.0),
    "急跌季線期望值門檻(%)": ("BUY_EV_THRESHOLD_60MA_SUPPORT", 80.0),
    "5日線扣抵偏低容忍度(%)": ("DEDUCTION_LOW_MAX_GAP_PCT", 6.0),
    "回測月線乖離容忍度(%)": ("MA20_SUPPORT_TOLERANCE_PCT", 2.5),
    "急跌季線乖離容忍度(%)": ("MA60_SUPPORT_TOLERANCE_PCT", 3.0),
    "賣出減碼期望值門檻(%)": ("SELL_EV_THRESHOLD_TRIM", 25.0),
    "賣出跌破5日線期望值門檻(%)": ("SELL_EV_THRESHOLD_BREAK_5MA", 50.0),
}


def load_signal_thresholds(settings_path=SIGNAL_THRESHOLDS_PATH):
    """讀取 97_Settings/個股買賣訊號門檻.md，回傳 {常數名稱: 數值} dict。
    讀取失敗或缺列時個別退回 _SIGNAL_THRESHOLD_DEFAULTS 內建預設值，確保報告仍可正常產生。"""
    values = {const_name: default for const_name, default in _SIGNAL_THRESHOLD_DEFAULTS.values()}
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
    except Exception as e:
        print(f"Warning: Failed to read signal thresholds settings: {e}")
        return values

    rows = _parse_markdown_table(lines, lambda cols: cols[:2] == ['設定項', '目前值'])
    for r in rows:
        mapping = _SIGNAL_THRESHOLD_DEFAULTS.get(r.get('設定項', '').strip())
        if not mapping:
            continue
        const_name, _ = mapping
        try:
            values[const_name] = float(r.get('目前值', ''))
        except ValueError:
            continue
    return values


_thresholds = load_signal_thresholds()

# 買進訊號門檻（期望值下限依「逆勢程度」遞增：順勢的五日線戰法最低，逆勢承接季線最高）
# 數值讀自 `[[個股買賣訊號門檻]]`（見 load_signal_thresholds），改設定檔後下次執行即生效，不需改程式碼。
BUY_EV_THRESHOLD_5MA_STRATEGY = _thresholds["BUY_EV_THRESHOLD_5MA_STRATEGY"]   # 五日線戰法所需期望值下限
BUY_EV_THRESHOLD_20MA_SUPPORT = _thresholds["BUY_EV_THRESHOLD_20MA_SUPPORT"]   # 回測上升月線所需期望值下限
BUY_EV_THRESHOLD_60MA_SUPPORT = _thresholds["BUY_EV_THRESHOLD_60MA_SUPPORT"]   # 急跌至上升季線所需期望值下限（門檻最高，因屬逆勢承接）
DEDUCTION_LOW_MAX_GAP_PCT = _thresholds["DEDUCTION_LOW_MAX_GAP_PCT"]           # 5日線扣抵值需低於現價、但差距在此百分比以內才算「偏低」
MA20_SUPPORT_TOLERANCE_PCT = _thresholds["MA20_SUPPORT_TOLERANCE_PCT"]         # 現價與20日均線乖離在正負此百分比內，視為「貼近測試月線」
MA60_SUPPORT_TOLERANCE_PCT = _thresholds["MA60_SUPPORT_TOLERANCE_PCT"]         # 現價與60日均線乖離在正負此百分比內，視為「貼近測試支撐」

# 賣出訊號門檻
SELL_EV_THRESHOLD_TRIM = _thresholds["SELL_EV_THRESHOLD_TRIM"]                # 期望值低於此值 -> 逢高減碼
SELL_EV_THRESHOLD_BREAK_5MA = _thresholds["SELL_EV_THRESHOLD_BREAK_5MA"]       # 期望值低於此值且跌破5日線 -> 提醒賣出

FOREIGN_LISTING_SUFFIXES = (".SH", ".HK", ".SS")


def is_foreign_listing(ticker):
    return any(suffix in ticker for suffix in FOREIGN_LISTING_SUFFIXES)


def load_concept_fpe_table(filepath=FPE_TABLE_PATH):
    """解析 概念股FPE合理區間.md 的主表格，回傳 [{concept, low, mid, high, members:[ticker,...]}]。
    只讀取「## 概念股分類與現有成員」小節底下、且下/中/上緣皆已填數字的列（跳過使用者尚未填寫的列）。
    表格第一欄為「類型」(產業位置/題材/其他)，第二欄才是概念股分類名稱。"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f"Warning: Failed to read FPE table: {e}")
        return []

    concepts = []
    in_main_table = False
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('## 概念股分類與現有成員'):
            in_main_table = True
            continue
        if in_main_table and stripped.startswith('## '):
            break
        if not in_main_table or not stripped.startswith('|'):
            continue

        cols = [c.strip() for c in stripped.split('|')[1:-1]]
        if len(cols) < 6 or cols[0].startswith(':') or cols[1].startswith('概念股分類'):
            continue

        m_concept = re.search(r'\[\[([^\]|]+)', cols[1])
        concept_key = m_concept.group(1) if m_concept else cols[1]

        def _to_float(s):
            try:
                return float(s)
            except ValueError:
                return None

        low, mid, high = _to_float(cols[2]), _to_float(cols[3]), _to_float(cols[4])
        if low is None or mid is None or high is None:
            continue

        member_tickers = []
        for member in cols[5].split('、'):
            m_ticker = re.match(r'^([0-9]+(?:\.[a-zA-Z]+)?)', member.strip())
            if m_ticker:
                member_tickers.append(m_ticker.group(1))

        concepts.append({"concept": concept_key, "low": low, "mid": mid, "high": high, "members": member_tickers})
    return concepts


def load_valuation_mode(filepath=FPE_TABLE_PATH):
    """讀取 概念股FPE合理區間.md「目標價估值設定」表的「估值EPS年度模式」，
    回傳 '明年' 或 '明年後年平均'；讀取失敗或未設定時預設 '明年'（原始行為）。"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f"Warning: Failed to read valuation mode: {e}")
        return "明年"
    m = re.search(r'\|\s*估值EPS年度模式\s*\|\s*([^|]+)\|', content)
    if m:
        value = m.group(1).strip()
        if value in ("明年", "明年後年平均"):
            return value
        print(f"Warning: 未知的估值EPS年度模式 '{value}'，退回預設 '明年'")
    return "明年"


def get_fpe_range_for_ticker(ticker, concept_table):
    """回傳該股所屬所有概念的FPE平均 (low, mid, high, matched_concepts)；無匹配則回傳 None。"""
    matched = [c for c in concept_table if ticker in c["members"]]
    if not matched:
        return None
    return {
        "low": sum(c["low"] for c in matched) / len(matched),
        "mid": sum(c["mid"] for c in matched) / len(matched),
        "high": sum(c["high"] for c in matched) / len(matched),
        "matched_concepts": [c["concept"] for c in matched],
    }


def compute_five_day_deduction(prices, max_gap_pct=DEDUCTION_LOW_MAX_GAP_PCT):
    """5日線扣抵值：明日即將被移出5日窗口的舊收盤價。若目前價格 > 扣抵值，代表明日窗口
    滾動時换掉的是較低的舊值，5MA 有望維持/轉為上彎；`low_near_price` 額外要求這個差距
    不超過 max_gap_pct%（避免扣抵值過度偏低這種極端值也被誤判為五日線戰法訊號）。"""
    if len(prices) < 5:
        return None
    deduction_value = prices[-5]
    current_price = prices[-1]
    turning_up_likely = current_price > deduction_value
    gap_pct = (current_price - deduction_value) / current_price * 100 if current_price else None
    low_near_price = bool(turning_up_likely and gap_pct is not None and gap_pct <= max_gap_pct)
    return {
        "deduction_value": deduction_value,
        "turning_up_likely": turning_up_likely,
        "gap_pct": gap_pct,
        "low_near_price": low_near_price,
    }


def compute_5ma_cross_status(prices):
    """是否站上5日線，以及「今日首日站上」/「貼近5日線隨時可能跌破」的簡化判斷。"""
    if len(prices) < 6:
        return None
    today_ma5 = sum(prices[-5:]) / 5
    yesterday_ma5 = sum(prices[-6:-1]) / 5
    today_close = prices[-1]
    yesterday_close = prices[-2]

    above_today = today_close > today_ma5
    above_yesterday = yesterday_close > yesterday_ma5
    bias_pct = (today_close - today_ma5) / today_ma5 * 100 if today_ma5 else 0.0

    return {
        "above_5ma": above_today,
        "just_crossed_above": above_today and not above_yesterday,
        "about_to_fall": above_today and 0 <= bias_pct < 1.0,
        "bias_pct": bias_pct,
    }


def _is_ma_rising_support(ma_metrics, period, tolerance_pct):
    """判斷現價是否「回測到上升中的 N 日均線」：該均線斜率為上彎，且現價與均線乖離
    幅度在正負 tolerance_pct% 容忍範圍內（含小幅跌破或貼近測試），視為支撐測試訊號。"""
    m = ma_metrics.get(period)
    if not m or m["val"] is None:
        return False
    if m["slope"] != "上彎":
        return False
    return -tolerance_pct <= m["bias"] <= tolerance_pct


def is_ma60_rising_support(ma_metrics, tolerance_pct=MA60_SUPPORT_TOLERANCE_PCT):
    return _is_ma_rising_support(ma_metrics, 60, tolerance_pct)


def is_ma20_rising_support(ma_metrics, tolerance_pct=MA20_SUPPORT_TOLERANCE_PCT):
    return _is_ma_rising_support(ma_metrics, 20, tolerance_pct)


def compute_technical_signals(ticker):
    """純技術面訊號 (不含估值期望值)，供「三、大戶共識標的」買賣提醒與「四、個股買賣
    訊號」共用。股價資料不足(<6天)時回傳 None。"""
    prices = get_historical_prices_fallback(ticker)
    if not prices or len(prices) < 6:
        return None

    ma_metrics = compute_ma_metrics(prices)
    cross_status = compute_5ma_cross_status(prices)
    deduction = compute_five_day_deduction(prices)
    ma20_support = is_ma20_rising_support(ma_metrics)
    ma60_support = is_ma60_rising_support(ma_metrics)

    above_5ma = bool(cross_status and cross_status["above_5ma"])
    just_crossed_above = bool(cross_status and cross_status["just_crossed_above"])
    deduction_low = bool(deduction and deduction["low_near_price"])

    return {
        "current_price": prices[-1],
        "ma_metrics": ma_metrics,
        "above_5ma": above_5ma,
        "just_crossed_above": just_crossed_above,
        "deduction": deduction,
        "deduction_low": deduction_low,
        "five_day_strategy_trigger": above_5ma or deduction_low,
        "ma20_support": ma20_support,
        "ma60_support": ma60_support,
        "ma5_down": ma_metrics[5]["slope"] == "下彎",
        "ma5_up": ma_metrics[5]["slope"] == "上彎",
        "ma20_down": ma_metrics[20]["slope"] == "下彎",
    }


def format_5ma_strategy_reasons(tech):
    """回傳 [(文字, 是否需標紅提醒)]。首日站上5日線是最值得注意的時點，標紅凸顯。"""
    reasons = []
    if tech["just_crossed_above"]:
        reasons.append(("首日站上5日線", True))
    elif tech["above_5ma"]:
        reasons.append(("已站上5日線", False))
    if tech["deduction_low"] and tech["deduction"]:
        reasons.append((f"5日線扣抵偏低現價{tech['deduction']['gap_pct']:.1f}%以內", False))
    if tech.get("ma5_up"):
        reasons.append(("5日線上彎", False))
    return reasons


def format_20ma_support_reason(tech):
    if tech["ma20_support"]:
        return [("回測上升中的月線支撐", False)]
    return []


def format_60ma_support_reason(tech):
    if tech["ma60_support"]:
        return [("急跌至上升中的季線支撐", False)]
    return []


def format_sell_reasons(tech):
    reasons = []
    if not tech["above_5ma"]:
        reasons.append("跌破5日線")
    if tech["ma5_down"]:
        reasons.append("5日線下彎")
    if tech["ma20_down"]:
        reasons.append("月線下彎")
    return reasons


_BLURB_STRONG_TERMINATORS = "。！？"
_BLURB_SOFT_BREAKS = "，、；："


def _truncate_at_boundary(text, max_len):
    """在 max_len 字以內截斷，優先找最靠近上限的標點斷點（句尾標點。！？ 或次要的
    ，、；：），避免斷在字詞中間；標點位置太靠前（低於 max_len 一半）則放棄找標點，
    直接在 max_len 硬切並加「…」——寧可斷得生硬，也不要犧牲太多可顯示的資訊量。
    截在句尾標點（。！？）時該標點本身已有收尾感，不再加「…」；截在次要標點則補「…」
    提示後面還有內容。"""
    if len(text) <= max_len:
        return text
    window = text[:max_len]
    cut = -1
    for i in range(len(window) - 1, -1, -1):
        if window[i] in _BLURB_STRONG_TERMINATORS or window[i] in _BLURB_SOFT_BREAKS:
            cut = i
            break
    if cut >= max_len // 2:
        truncated = window[:cut + 1]
        if window[cut] in _BLURB_STRONG_TERMINATORS:
            return truncated
        return truncated + "…"
    return window.rstrip() + "…"


def extract_investment_blurb(filepath, max_len=80):
    """從個股筆記的「核心論點」抓取第一條重點，簡化為 max_len 字以內的買進理由摘要
    （見 _truncate_at_boundary：優先在標點處截斷，不會為了找標點而超過 max_len）。
    找不到時回傳空字串（呼叫端應自行處理顯示「-」）。"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception:
        return ""

    # 子項目在不同筆記裡混用 "-" 或 "*" 作為 bullet 符號，兩種都要能匹配。
    m = re.search(r'\*\*核心論點\*\*[：:]\s*\n((?:\s*[-*]\s.+\n?)+)', content)
    if not m:
        return ""
    first_bullet = m.group(1).strip().split('\n')[0]
    # 只去掉開頭那一個 bullet 符號("- "或"* ")，不能用 lstrip('-* ') ——它會連著
    # 後面粗體標記的 "**" 一起吃掉，導致只有開頭 ** 被移除、結尾 ** 殘留。
    text = re.sub(r'^[-*]\s+', '', first_bullet).strip()
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # 粗體
    text = re.sub(r'`?\[\[([^\]|]+)(?:\|([^\]]+))?\]\]`?', lambda m: m.group(2) or m.group(1), text)  # WikiLink
    text = re.sub(r'`([^`]+)`', r'\1', text)  # 行內程式碼
    text = _truncate_at_boundary(text, max_len)
    return text


def compute_stock_signal(ticker, filepath, target_year, concept_table, valuation_mode="明年"):
    """整合單一個股的買進/賣出訊號 (估值期望值 + 技術面觸發)，回傳 dict；
    股價資料不足(<6天)時回傳 None。目標價/期望值採 FPE 上緣（樂觀情境）而非中緣計算；
    估值 EPS 依 valuation_mode 取明年或明年後年平均（見 load_valuation_mode）。"""
    tech = compute_technical_signals(ticker)
    if tech is None:
        return None

    current_price = tech["current_price"]
    target_eps = parse_valuation_eps(filepath, target_year, valuation_mode)
    fpe_range = get_fpe_range_for_ticker(ticker, concept_table)

    target_price = None
    expected_value_pct = None
    if target_eps is not None and target_eps > 0 and fpe_range is not None:
        target_price = target_eps * fpe_range["high"]
        expected_value_pct = (target_price - current_price) / current_price * 100

    # valuation_rating 固定傳 "HOLD"：這裡只是借用 compute_tactical_score() 算 MA/Bias 分數，
    # 不需要它內建給 update_prices.py 用的「估值SELL且跌破5MA→強制0分」門檻。
    tactical = compute_tactical_score(tech["ma_metrics"], "HOLD")

    signal = "待補充"
    reasons = []
    highlight_first_day = False

    if expected_value_pct is not None:
        buy_5ma = expected_value_pct > BUY_EV_THRESHOLD_5MA_STRATEGY and tech["five_day_strategy_trigger"]
        buy_20ma = expected_value_pct > BUY_EV_THRESHOLD_20MA_SUPPORT and tech["ma20_support"]
        buy_60ma = expected_value_pct > BUY_EV_THRESHOLD_60MA_SUPPORT and tech["ma60_support"]

        if buy_5ma or buy_20ma or buy_60ma:
            signal = "BUY"
            if buy_5ma:
                for text, highlight in format_5ma_strategy_reasons(tech):
                    reasons.append(text)
                    highlight_first_day = highlight_first_day or highlight
            if buy_20ma:
                reasons.extend(text for text, _ in format_20ma_support_reason(tech))
            if buy_60ma:
                reasons.extend(text for text, _ in format_60ma_support_reason(tech))
        else:
            sell_trim = expected_value_pct < SELL_EV_THRESHOLD_TRIM
            sell_break = expected_value_pct < SELL_EV_THRESHOLD_BREAK_5MA and not tech["above_5ma"]
            if sell_trim or sell_break:
                signal = "SELL"
                if sell_trim:
                    reasons.append(f"期望值{expected_value_pct:+.1f}% < {SELL_EV_THRESHOLD_TRIM:.0f}%，逢高減碼")
                if sell_break:
                    reasons.append(f"期望值{expected_value_pct:+.1f}% < {SELL_EV_THRESHOLD_BREAK_5MA:.0f}%，且已跌破5日線")
            else:
                signal = "HOLD"

    return {
        "ticker": ticker,
        "current_price": current_price,
        "target_eps": target_eps,
        "fpe_range": fpe_range,
        "target_price": target_price,
        "expected_value_pct": expected_value_pct,
        "ma_score": tactical["ma_score"],
        "ma_rating": tactical["ma_rating"],
        "bias_score": tactical["bias_score"],
        "bias_rating": tactical["bias_rating"],
        "signal": signal,
        "reasons": reasons,
        "highlight_first_day": highlight_first_day,
        # 轉強型態：首日站上5日線或扣抵值偏低（供報告端搭配動能分數做「轉強高動能」置頂）
        "breakout": bool(tech["just_crossed_above"] or tech["deduction_low"]),
        # 現價是否站上20日均線(月線)，供「一、大盤情況」統計資料庫個股月線以上家數
        "above_ma20": bool(tech["ma_metrics"][20]["val"] and current_price > tech["ma_metrics"][20]["val"]),
    }
