"""
共用股價/均線/籌碼計算模組。

被 update_prices.py、generate_stock_report.py、generate_weekly_focus.py 共用，
避免同一套均線/乖離率計算邏輯或筆記解析邏輯各自維護一份、規則逐漸不同步的問題。

分層原則：
- fetch_* / download_*  : 純資料抓取 (Yahoo Finance 股價、TDCC 籌碼)
- calculate_ma / compute_ma_metrics : 純計算 (均線值、斜率、乖離率%、52週高低)，不含評等門檻
- compute_tactical_score : 唯一一套評分/評等規則 (MA Score / Bias Score -> tactical_action)，
  消費 compute_ma_metrics() 的輸出，不重新計算均線
- parse_target_eps : 唯一一套從個股筆記「財務數據與 EPS 預估比對」表格解析目標年度 EPS 的邏輯
"""
import json
import os
import re
import urllib.request
import io
import csv

MA_PERIODS = [5, 10, 20, 60, 120, 240]
CREDENTIALS_PATH = r"C:\Users\User\Desktop\LucasBrain\.agent\credentials.json"


def _load_finmind_token(credentials_path=CREDENTIALS_PATH):
    """唯一一處讀取 FinMind token 的邏輯，供所有 FinMind API 呼叫共用。"""
    try:
        if os.path.exists(credentials_path):
            with open(credentials_path, 'r', encoding='utf-8') as cf:
                return json.load(cf).get("finmind_token")
    except Exception as e:
        print(f"Warning: Failed to load FinMind token: {e}")
    return None


def _finmind_request(dataset, data_id, start_date, credentials_path=CREDENTIALS_PATH, timeout=15):
    """呼叫 FinMind v4 API 並回傳 data list，統一 token/header 組裝與錯誤處理。"""
    token = _load_finmind_token(credentials_path)
    url = f"https://api.finmindtrade.com/api/v4/data?dataset={dataset}&data_id={data_id}&start_date={start_date}"
    if token:
        url += f"&token={token}"

    headers = {'User-Agent': 'Mozilla/5.0'}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        res_data = json.loads(response.read().decode('utf-8'))
        return res_data.get('data', [])


# ==========================================
# 1. Yahoo Finance Historical Price Fetcher
# ==========================================
def fetch_historical_prices(symbol):
    # Fetch 2 years of daily data to ensure enough points for 240MA and its yesterday slope
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            chart_res = data.get('chart', {}).get('result')
            if chart_res and len(chart_res) > 0:
                result = chart_res[0]
                timestamps = result.get('timestamp', [])
                quote = result.get('indicators', {}).get('quote', [{}])[0]
                close_prices = quote.get('close', [])

                clean_data = []
                for ts, pr in zip(timestamps, close_prices):
                    if pr is not None:
                        clean_data.append(pr)
                return clean_data
    except Exception:
        pass
    return []


def get_historical_prices_fallback(ticker):
    ticker = ticker.strip()
    if ticker.isdigit():
        prices = fetch_historical_prices(f"{ticker}.TW")
        if prices:
            return prices
        prices = fetch_historical_prices(f"{ticker}.TWO")
        if prices:
            return prices
    else:
        prices = fetch_historical_prices(ticker)
        if prices:
            return prices
        if ".TW" in ticker:
            fallback = ticker.replace(".TW", ".TWO")
            prices = fetch_historical_prices(fallback)
            if prices:
                return prices
        elif ".TWO" in ticker:
            fallback = ticker.replace(".TWO", ".TW")
            prices = fetch_historical_prices(fallback)
            if prices:
                return prices
        elif ".SH" in ticker:
            sh_ticker = ticker.replace(".SH", ".SS")
            prices = fetch_historical_prices(sh_ticker)
            if prices:
                return prices
    return []


# ==========================================
# 2. TDCC Shareholding Data
# ==========================================
def download_and_parse_tdcc():
    """一次性抓取集保所 OpenData 全市場週資料 (免費，無需 token)，回傳 {ticker: {date, ratio_400, ratio_1000}}。"""
    url = "https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

    tdcc_cache = {}
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            content = response.read().decode('big5', errors='ignore')
            f = io.StringIO(content)
            reader = csv.reader(f)
            next(reader)  # headers

            ticker_groups = {}
            for row in reader:
                if len(row) >= 6:
                    ticker = row[1].strip()
                    ticker_groups.setdefault(ticker, []).append(row)

            for ticker, rows in ticker_groups.items():
                if not rows:
                    continue
                date_str = rows[0][0].strip()  # e.g. "20260703"
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

                ratio_1000 = 0.0
                ratio_400 = 0.0
                for row in rows:
                    try:
                        tier = int(row[2].strip())
                        percent = float(row[5].strip())
                        if tier == 15:
                            ratio_1000 = percent
                            ratio_400 += percent
                        elif tier in [12, 13, 14]:
                            ratio_400 += percent
                    except ValueError:
                        continue

                tdcc_cache[ticker] = {
                    "date": formatted_date,
                    "ratio_400": ratio_400,
                    "ratio_1000": ratio_1000
                }
    except Exception as e:
        print(f"Failed to download/parse TDCC OpenData: {e}")

    return tdcc_cache


def fetch_tdcc_history_finmind(ticker, start_date, credentials_path=CREDENTIALS_PATH):
    """透過 FinMind API 逐檔查詢籌碼歷史 (付費 Backer 方案，用於個股研報等需要保證
    最近 N 週資料完整性的場景；每日全市場批次更新請用 download_and_parse_tdcc)。"""
    try:
        data_list = _finmind_request("TaiwanStockHoldingSharesPer", ticker, start_date, credentials_path)
        if not data_list:
            return []

        records_by_date = {}
        for item in data_list:
            d = item.get('date')
            if not d:
                continue
            records_by_date.setdefault(d, []).append(item)

        history = []
        for date in sorted(records_by_date.keys(), reverse=True):
            rows = records_by_date[date]
            ratio_400 = 0.0
            ratio_1000 = 0.0
            people_400 = 0

            for row in rows:
                # FinMind's HoldingSharesLevel is a share-count range label (e.g. "400,001-600,000",
                # "more than 1,000,001"), NOT the numeric tier code (12-15) used by TDCC's free
                # OpenData CSV in download_and_parse_tdcc(). 400張=400,000股, 1000張=1,000,000股.
                level_label = str(row.get('HoldingSharesLevel', '')).strip()
                percent = float(row.get('percent', 0.0))
                people = int(row.get('people', 0))

                if level_label == 'more than 1,000,001':
                    ratio_1000 = percent
                    ratio_400 += percent
                    people_400 += people
                elif level_label in ('400,001-600,000', '600,001-800,000', '800,001-1,000,000'):
                    ratio_400 += percent
                    people_400 += people

            history.append({
                "date": date,
                "ratio_400": ratio_400,
                "ratio_1000": ratio_1000,
                "people_400": people_400
            })
        return history
    except Exception as e:
        print(f"Warning: Failed to fetch TDCC history from FinMind: {e}")
        return []


def parse_tdcc_from_stock_note(stock_content):
    """從既有個股筆記的籌碼表格讀回歷史資料，做為 FinMind 查詢失敗時的備援。"""
    lines = stock_content.split('\n')
    started = False
    table_lines = []
    for line in lines:
        if line.startswith('###') and "籌碼面" in line:
            started = True
            continue
        if started:
            if line.startswith('##') or (line.startswith('###') and "籌碼面" not in line):
                break
            if '|' in line:
                table_lines.append(line)

    history = []
    import re
    for line in table_lines:
        cols = [c.strip() for c in line.split('|')]
        if len(cols) >= 4:
            date_str = cols[1].strip()
            if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                p400_str = cols[2].replace('%', '').strip()
                p1000_str = cols[3].replace('%', '').strip()
                try:
                    history.append({
                        "date": date_str,
                        "ratio_400": float(p400_str),
                        "ratio_1000": float(p1000_str),
                        "people_400": "-"
                    })
                except ValueError:
                    continue
    return history


# ==========================================
# 3. Moving Average & Bias Metrics (計算層，不含評分門檻)
# ==========================================
def calculate_ma(prices, period, index=-1):
    if len(prices) < period:
        return None
    if index == -1:
        slice_prices = prices[-period:]
    else:
        slice_prices = prices[index - period + 1: index + 1] if index + 1 != 0 else prices[index - period + 1:]
    return sum(slice_prices) / period


def compute_ma_metrics(prices):
    """回傳全部 MA_PERIODS (以 period 為 key) 的 {val, slope, bias(帶正負號的%), dist}，
    並列 current_price / high_52w / low_52w / sufficient_for_score 於同一層。
    這是均線/乖離率的唯一計算來源；評分門檻邏輯請見 compute_tactical_score()。
    """
    if not prices:
        metrics = {p: {"val": 0.0, "slope": "無數據", "bias": 0.0, "dist": 0.0} for p in MA_PERIODS}
        metrics.update({
            "current_price": 0.0,
            "high_52w": 0.0,
            "low_52w": 0.0,
            "sufficient_for_score": False,
        })
        return metrics

    current_price = prices[-1]
    recent_250 = prices[-250:] if len(prices) >= 250 else prices
    high_52w = max(recent_250)
    low_52w = min(recent_250)

    metrics = {}
    for p in MA_PERIODS:
        ma_val = calculate_ma(prices, p, -1)
        if ma_val is None:
            metrics[p] = {"val": 0.0, "slope": "無數據", "bias": 0.0, "dist": 0.0}
            continue
        ma_prev = calculate_ma(prices, p, -2)
        if ma_prev is None:
            ma_prev = ma_val
        slope = "上彎" if ma_val > ma_prev else "下彎"
        bias = (current_price - ma_val) / ma_val * 100 if ma_val else 0.0
        dist = current_price - ma_val
        metrics[p] = {"val": ma_val, "slope": slope, "bias": bias, "dist": dist}

    metrics["current_price"] = current_price
    metrics["high_52w"] = high_52w
    metrics["low_52w"] = low_52w
    metrics["sufficient_for_score"] = len(prices) >= 242
    return metrics


# ==========================================
# 4. Tactical Scoring — 唯一一套 MA Score / Bias Score 評分規則
# ==========================================
def compute_tactical_score(ma_metrics, valuation_rating):
    """消費 compute_ma_metrics() 的輸出，產出 MA Score / Bias Score 與 tactical_action 評等。
    這是全庫唯一的評分/門檻系統，其他腳本需要評等時應呼叫本函式，不應另行實作一套門檻。
    """
    close = ma_metrics["current_price"]
    mas_full = ma_metrics

    if not ma_metrics.get("sufficient_for_score", False):
        return {
            "close": close,
            "mas": {p: mas_full.get(p, {}).get("val", 0.0) for p in MA_PERIODS},
            "slopes": {p: mas_full.get(p, {}).get("slope", "下彎") for p in MA_PERIODS},
            "ma_score": 0,
            "ma_rating": "均線評分差",
            "ma_reasons": ["歷史 K 線數據不足 242 天，無法評估均線"],
            "bias_score": 0,
            "bias_rating": "乖離率評分差",
            "bias_reasons": ["歷史 K 線數據不足 242 天，無法評估乖離"],
            "score_str": "MA: 0 / Bias: 0",
            "rating": "均線評分差 | 乖離率評分差"
        }

    mas = {p: mas_full[p]["val"] for p in MA_PERIODS}
    slopes = {p: mas_full[p]["slope"] for p in MA_PERIODS}

    if valuation_rating == "SELL":
        # Valuation is SELL & 跌破 5ma ➡️ 直接警示並評斷為 SELL
        if close < mas[5]:
            return {
                "close": close,
                "mas": mas,
                "slopes": slopes,
                "ma_score": 0,
                "ma_rating": "均線評分差",
                "ma_reasons": [f"估值偏高且收盤價跌破 5MA {mas[5]:.2f}"],
                "bias_score": 0,
                "bias_rating": "乖離率評分差",
                "bias_reasons": [f"估值偏高且收盤價跌破 5MA {mas[5]:.2f}"],
                "score_str": "MA: 0 / Bias: 0",
                "rating": "SELL"
            }

    # 1. MA Score (base = 0)
    ma_score = 0
    ma_reasons = []

    # A. 5ma上彎且股價 > 5ma (+40分)
    if slopes[5] == "上彎" and close > mas[5]:
        ma_score += 40
        ma_reasons.append("5MA 上彎且股價高於 5MA (+40)")

    # B. 短期均線 5ma, 10ma, 20ma, 60ma 均上彎(+20分)
    if slopes[5] == "上彎" and slopes[10] == "上彎" and slopes[20] == "上彎" and slopes[60] == "上彎":
        ma_score += 20
        ma_reasons.append("短期均線 (5/10/20/60MA) 均呈上彎 (+20)")

    # C. 股價是否底於 5ma, 10ma, 20ma, 60ma, 120ma, 240ma，每低於一條均線扣 10 分
    below_cnt = 0
    for p in MA_PERIODS:
        if close < mas[p]:
            ma_score -= 10
            below_cnt += 1
    if below_cnt > 0:
        ma_reasons.append(f"股價低於 {below_cnt} 條均線 (-{below_cnt * 10})")

    # D. 每條均線若上彎各加 10 分，每下彎一條扣 10 分
    up_cnt = 0
    down_cnt = 0
    for p in MA_PERIODS:
        if slopes[p] == "上彎":
            ma_score += 10
            up_cnt += 1
        else:
            ma_score -= 10
            down_cnt += 1
    ma_reasons.append(f"均線 {up_cnt} 條上彎 (+{up_cnt * 10}), {down_cnt} 條下彎 (-{down_cnt * 10})")

    if ma_score >= 80:
        ma_rating = "均線評分佳"
    elif 50 < ma_score < 80:
        ma_rating = "均線評分普通"
    else:
        ma_rating = "均線評分差"

    # 2. Bias Score (base = 100) — 取 compute_ma_metrics() 已算好的帶號乖離%，僅在此取絕對值套門檻
    bias_score = 100
    bias_reasons = []

    bias_5 = abs(mas_full[5]["bias"]) / 100
    bias_20 = abs(mas_full[20]["bias"]) / 100
    bias_60 = abs(mas_full[60]["bias"]) / 100

    if bias_5 > 0.05:
        bias_score -= 10
        bias_reasons.append(f"股價偏離 5MA ({bias_5*100:.1f}%) 超過 5% (-10)")

    if bias_20 > 0.25:
        bias_score -= 15
        bias_reasons.append(f"股價偏離 20MA ({bias_20*100:.1f}%) 超過 25% (-15)")

    if bias_60 > 0.40:
        bias_score -= 15
        bias_reasons.append(f"股價偏離 60MA ({bias_60*100:.1f}%) 超過 40% (-15)")

    if bias_5 > 0.10:
        bias_score -= 15
        bias_reasons.append(f"股價偏離 5MA ({bias_5*100:.1f}%) 超過 10% (追加扣分 -15)")

    if bias_5 > 0.15:
        bias_score -= 20
        bias_reasons.append(f"股價偏離 5MA ({bias_5*100:.1f}%) 超過 15% (追加扣分 -20)")

    if bias_score >= 70:
        bias_rating = "乖離率評分佳"
    elif 50 < bias_score < 70:
        bias_rating = "乖離率評分普通"
    else:
        bias_rating = "乖離率評分差"

    score_str = f"MA: {ma_score} / Bias: {bias_score}"
    rating_str = f"{ma_rating} | {bias_rating}"

    return {
        "close": close,
        "mas": mas,
        "slopes": slopes,
        "ma_score": ma_score,
        "ma_rating": ma_rating,
        "ma_reasons": ma_reasons,
        "bias_score": bias_score,
        "bias_rating": bias_rating,
        "bias_reasons": bias_reasons,
        "score_str": score_str,
        "rating": rating_str
    }


# ==========================================
# 5. Note Parsing Helpers
# ==========================================
def parse_target_eps(filepath, target_year):
    """從個股筆記的「財務數據與 EPS 預估比對」表格中，取出指定年度所有並列估計值的平均。"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f"Failed to read {filepath}: {e}")
        return None

    eps_values = []
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('|'):
            cols = [c.strip() for c in line.split('|')]
            if len(cols) >= 5:
                year = cols[2].strip()
                eps_val = cols[3].strip()
                if year == str(target_year):
                    nums = re.findall(r'(\d+(?:\.\d+)?)', eps_val)
                    if nums:
                        floats = [float(n) for n in nums]
                        avg_val = sum(floats) / len(floats)
                        eps_values.append(avg_val)

    if eps_values:
        return sum(eps_values) / len(eps_values)
    return None


# ==========================================
# 6. FinMind Financial Statements (季度財報，付費 Backer 方案)
# ==========================================
def _date_to_quarter_label(date_str):
    try:
        year, month = date_str.split('-')[0], date_str.split('-')[1]
        m = int(month)
        q = 1 if m <= 3 else 2 if m <= 6 else 3 if m <= 9 else 4
        return f"{year}Q{q} (實)"
    except Exception:
        return date_str


def fetch_financial_statements(ticker, start_date, credentials_path=CREDENTIALS_PATH):
    """透過 FinMind TaiwanStockFinancialStatements 抓取季度財報原始數據，
    回傳依日期排序 (由舊到新) 的 [{date, quarter_label, revenue, gross_profit, operating_income, eps}] 列表。"""
    try:
        records = _finmind_request("TaiwanStockFinancialStatements", ticker, start_date, credentials_path)
        if not records:
            return []

        by_date = {}
        for r in records:
            d = r.get('date')
            t = r.get('type')
            v = r.get('value')
            by_date.setdefault(d, {})[t] = v

        quarters = []
        for d in sorted(by_date.keys()):
            data = by_date[d]
            revenue = data.get('Revenue', 0.0) or 0.0
            gross_profit = data.get('GrossProfit', 0.0) or 0.0
            operating_income = data.get('OperatingIncome', 0.0) or 0.0
            eps = data.get('EPS', 0.0) or 0.0
            quarters.append({
                "date": d,
                "quarter_label": _date_to_quarter_label(d),
                "revenue": revenue,
                "gross_profit": gross_profit,
                "operating_income": operating_income,
                "eps": eps,
            })
        return quarters
    except Exception as e:
        print(f"Warning: Failed to fetch financial statements from FinMind: {e}")
        return []


def format_financial_table(quarterly_records, quarters=5):
    """把 fetch_financial_statements() 的原始資料格式化為個股研報用的季度財報 Markdown 表格，僅取最近 N 季。"""
    if not quarterly_records:
        return None

    recent = quarterly_records[-quarters:] if len(quarterly_records) >= quarters else quarterly_records

    lines = ["| 季度 | 營收 (億元) | 毛利率 (%) | 營業利益率 (%) | EPS (元) | 備註 / 營運重點說明 |",
             "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for q in recent:
        revenue_hundred_millions = q["revenue"] / 100000000.0
        gp_margin = (q["gross_profit"] / q["revenue"] * 100.0) if q["revenue"] else 0.0
        op_margin = (q["operating_income"] / q["revenue"] * 100.0) if q["revenue"] else 0.0
        lines.append(
            f"| **{q['quarter_label']}** | {revenue_hundred_millions:.2f} | {gp_margin:.2f}% | "
            f"{op_margin:.2f}% | {q['eps']:.2f} | (FinMind 財報自動抓取) |"
        )
    return "\n".join(lines)
