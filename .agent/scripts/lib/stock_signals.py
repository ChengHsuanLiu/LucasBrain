"""
個股技術面訊號與買進/賣出訊號計算模組。

`compute_technical_signals()` 是純技術面訊號 (不含估值期望值)，供「三、主力大戶
共識標的」的買賣提醒與「四、資料庫個股買進/賣出訊號」共用：
- 五日線戰法：已站上5日線 (首日站上特別標註) 或 5日線扣抵值偏低現價一定幅度以內
- 急跌至長線支撐：現價貼近上升中的60日均線
- 賣出提醒：跌破5日線 / 5日線下彎 / 20日線(月線)下彎

`compute_stock_signal()` 疊加估值面 (隔年EPS x 概念股FPE上緣算出目標價與期望值%)，
兩種買進訊號都需要期望值門檻 + 對應技術面觸發同時成立；兩種賣出訊號則只看期望值。
"""
import os
import re

from .stock_metrics import (
    get_historical_prices_fallback,
    compute_ma_metrics,
    compute_tactical_score,
    parse_target_eps,
)

STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"
FPE_TABLE_PATH = r"C:\Users\User\Desktop\LucasBrain\20_Garden\概念股FPE合理區間.md"

# 買進訊號門檻
BUY_EV_THRESHOLD_5MA_STRATEGY = 60.0   # 五日線戰法所需期望值下限
BUY_EV_THRESHOLD_60MA_SUPPORT = 80.0   # 急跌至長線支撐所需期望值下限（門檻較高，因屬逆勢承接）
DEDUCTION_LOW_MAX_GAP_PCT = 6.0        # 5日線扣抵值需低於現價、但差距在此百分比以內才算「偏低」
MA60_SUPPORT_TOLERANCE_PCT = 3.0       # 現價與60日均線乖離在正負此百分比內，視為「貼近測試支撐」

# 賣出訊號門檻
SELL_EV_THRESHOLD_TRIM = 25.0          # 期望值低於此值 -> 逢高減碼
SELL_EV_THRESHOLD_BREAK_5MA = 50.0     # 期望值低於此值且跌破5日線 -> 提醒賣出

FOREIGN_LISTING_SUFFIXES = (".SH", ".HK", ".SS")


def is_foreign_listing(ticker):
    return any(suffix in ticker for suffix in FOREIGN_LISTING_SUFFIXES)


def load_concept_fpe_table(filepath=FPE_TABLE_PATH):
    """解析 概念股FPE合理區間.md 的主表格，回傳 [{concept, low, mid, high, members:[ticker,...]}]。
    只讀取「## 概念股分類與現有成員」小節底下、且下/中/上緣皆已填數字的列（跳過使用者尚未填寫的列）。"""
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
        if len(cols) < 5 or cols[0].startswith(':') or cols[0].startswith('概念股分類'):
            continue

        m_concept = re.search(r'\[\[([^\]|]+)', cols[0])
        concept_key = m_concept.group(1) if m_concept else cols[0]

        def _to_float(s):
            try:
                return float(s)
            except ValueError:
                return None

        low, mid, high = _to_float(cols[1]), _to_float(cols[2]), _to_float(cols[3])
        if low is None or mid is None or high is None:
            continue

        member_tickers = []
        for member in cols[4].split('、'):
            m_ticker = re.match(r'^([0-9]+(?:\.[a-zA-Z]+)?)', member.strip())
            if m_ticker:
                member_tickers.append(m_ticker.group(1))

        concepts.append({"concept": concept_key, "low": low, "mid": mid, "high": high, "members": member_tickers})
    return concepts


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


def is_ma60_rising_support(ma_metrics, tolerance_pct=MA60_SUPPORT_TOLERANCE_PCT):
    """判斷是否「急跌至上升中的60日均線」：60MA斜率為上彎，且現價與60MA乖離幅度在
    正負 tolerance_pct% 容忍範圍內（含小幅跌破或貼近測試），視為長線支撐測試訊號。"""
    m60 = ma_metrics.get(60)
    if not m60 or m60["val"] is None:
        return False
    if m60["slope"] != "上彎":
        return False
    return -tolerance_pct <= m60["bias"] <= tolerance_pct


def compute_technical_signals(ticker):
    """純技術面訊號 (不含估值期望值)，供「三、大戶共識標的」買賣提醒與「四、個股買賣
    訊號」共用。股價資料不足(<6天)時回傳 None。"""
    prices = get_historical_prices_fallback(ticker)
    if not prices or len(prices) < 6:
        return None

    ma_metrics = compute_ma_metrics(prices)
    cross_status = compute_5ma_cross_status(prices)
    deduction = compute_five_day_deduction(prices)
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


def format_60ma_support_reason(tech):
    if tech["ma60_support"]:
        return [("急跌至上升中的60日均線支撐", False)]
    return []


def format_sell_reasons(tech):
    reasons = []
    if not tech["above_5ma"]:
        reasons.append("跌破5日線")
    if tech["ma5_down"]:
        reasons.append("5日線下彎")
    if tech["ma20_down"]:
        reasons.append("20日線(月線)下彎")
    return reasons


def extract_investment_blurb(filepath, max_len=80):
    """從個股筆記的「核心論點」抓取第一條重點，簡化為 max_len 字以內的買進理由摘要。
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
    if len(text) > max_len:
        text = text[:max_len - 1].rstrip() + "…"
    return text


def compute_stock_signal(ticker, filepath, target_year, concept_table):
    """整合單一個股的買進/賣出訊號 (估值期望值 + 技術面觸發)，回傳 dict；
    股價資料不足(<6天)時回傳 None。目標價/期望值採 FPE 上緣（樂觀情境）而非中緣計算。"""
    tech = compute_technical_signals(ticker)
    if tech is None:
        return None

    current_price = tech["current_price"]
    target_eps = parse_target_eps(filepath, target_year)
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
        buy_60ma = expected_value_pct > BUY_EV_THRESHOLD_60MA_SUPPORT and tech["ma60_support"]

        if buy_5ma or buy_60ma:
            signal = "BUY"
            if buy_5ma:
                for text, highlight in format_5ma_strategy_reasons(tech):
                    reasons.append(text)
                    highlight_first_day = highlight_first_day or highlight
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
                    reasons.append(f"期望值{expected_value_pct:+.1f}% < {SELL_EV_THRESHOLD_BREAK_5MA:.0f}%且已跌破5日線")
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
    }
