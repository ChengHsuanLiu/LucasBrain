"""
資料庫個股買進/賣出訊號計算模組 (DailyReport 第四階段：四、資料庫個股買進/賣出訊號)。

消費 stock_metrics.py 的均線/乖離率計算與個股筆記的隔年EPS估算，疊加：
- 概念股 FPE 目標價 (隔年EPS x 所屬概念股FPE中緣，同屬多個概念取平均)
- 期望值% = (目標價/現價 - 1)，>60% 才視為買進訊號、<30% 提醒逢高減碼
- 5日線站上狀態 (首日站上/準備跌落) 與5日線扣抵值 (5MA是否有望轉為上彎)
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

BUY_EXPECTED_VALUE_THRESHOLD = 60.0
SELL_EXPECTED_VALUE_THRESHOLD = 30.0
BIAS_SCORE_OVERHEAT_THRESHOLD = 70


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


def compute_five_day_deduction(prices):
    """5日線扣抵值：明日即將被移出5日窗口的舊收盤價。若目前價格 > 扣抵值，代表明日窗口
    滾動時换掉的是較低的舊值，5MA 有望維持/轉為上彎；反之則上彎動能減弱。"""
    if len(prices) < 5:
        return None
    deduction_value = prices[-5]
    current_price = prices[-1]
    return {"deduction_value": deduction_value, "turning_up_likely": current_price > deduction_value}


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


def compute_stock_signal(ticker, filepath, target_year, concept_table):
    """整合單一個股的買進/賣出訊號，回傳 dict；歷史股價不足(<6天)時回傳 None。"""
    prices = get_historical_prices_fallback(ticker)
    if not prices or len(prices) < 6:
        return None

    current_price = prices[-1]
    target_eps = parse_target_eps(filepath, target_year)
    fpe_range = get_fpe_range_for_ticker(ticker, concept_table)

    target_price = None
    expected_value_pct = None
    if target_eps is not None and target_eps > 0 and fpe_range is not None:
        target_price = target_eps * fpe_range["mid"]
        expected_value_pct = (target_price - current_price) / current_price * 100

    ma_metrics = compute_ma_metrics(prices)
    # valuation_rating 固定傳 "HOLD"：這裡只是借用 compute_tactical_score() 算 MA/Bias 分數，
    # 不需要它內建給 update_prices.py 用的「估值SELL且跌破5MA→強制0分」門檻。
    tactical = compute_tactical_score(ma_metrics, "HOLD")
    cross_status = compute_5ma_cross_status(prices)
    deduction = compute_five_day_deduction(prices)

    alerts = []
    if cross_status:
        if cross_status["just_crossed_above"]:
            alerts.append("今日剛站上5日線（首日站上）")
        if not cross_status["above_5ma"]:
            alerts.append("已跌破5日線")
        elif cross_status["about_to_fall"]:
            alerts.append(f"貼近5日線（乖離僅{cross_status['bias_pct']:.2f}%），留意隨時可能跌破")
    if deduction:
        if deduction["turning_up_likely"]:
            alerts.append(f"5日線扣抵值偏低（{deduction['deduction_value']:.2f}），有望維持/轉為上彎")
        else:
            alerts.append(f"5日線扣抵值偏高（{deduction['deduction_value']:.2f}），上彎動能減弱")

    if expected_value_pct is None:
        signal = "待補充"
    elif expected_value_pct > BUY_EXPECTED_VALUE_THRESHOLD:
        signal = "BUY"
    elif expected_value_pct < SELL_EXPECTED_VALUE_THRESHOLD:
        signal = "SELL_逢高減碼"
    elif cross_status and not cross_status["above_5ma"]:
        signal = "SELL_跌破5MA"
    elif tactical["bias_score"] < BIAS_SCORE_OVERHEAT_THRESHOLD:
        signal = "SELL_乖離過熱"
    else:
        signal = "HOLD"

    if signal == "BUY" and tactical["bias_score"] < BIAS_SCORE_OVERHEAT_THRESHOLD:
        alerts.append(f"乖離率評分僅{tactical['bias_score']}分，短線偏熱，可考慮等拉回再進場")

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
        "cross_status": cross_status,
        "deduction": deduction,
        "signal": signal,
        "alerts": alerts,
    }
