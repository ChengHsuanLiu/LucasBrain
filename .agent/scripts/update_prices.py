import os
import re
import json
import urllib.request
import io
import csv
from datetime import datetime

# ==========================================
# 1. TDCC Weekly Data Downloader & Parser
# ==========================================
def download_and_parse_tdcc():
    url = "https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Downloading weekly TDCC shareholding data once...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    tdcc_cache = {}
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            content = response.read().decode('big5', errors='ignore')
            f = io.StringIO(content)
            reader = csv.reader(f)
            headers = next(reader)
            
            # Group rows by ticker
            ticker_groups = {}
            for row in reader:
                if len(row) >= 6:
                    ticker = row[1].strip()
                    if ticker not in ticker_groups:
                        ticker_groups[ticker] = []
                    ticker_groups[ticker].append(row)
            
            # Parse each ticker group
            for ticker, rows in ticker_groups.items():
                if not rows:
                    continue
                date_str = rows[0][0].strip() # e.g. "20260703"
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
            print(f"Successfully cached TDCC data for {len(tdcc_cache)} tickers.")
    except Exception as e:
        print(f"Failed to download/parse TDCC data: {e}")
        print("Continuing without updating weekly shareholding tables.")
        
    return tdcc_cache

# ==========================================
# 2. Yahoo Finance Historical Data Fetcher
# ==========================================
def fetch_historical_prices(symbol):
    # Fetch 2 years of daily data to ensure we have enough points for 240MA and its yesterday slope
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
                
                # Zip and filter out null values
                clean_data = []
                for ts, pr in zip(timestamps, close_prices):
                    if pr is not None:
                        clean_data.append(pr)
                return clean_data
    except Exception as e:
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
# 3. Moving Average & Double Scoring Core
# ==========================================
def calculate_ma(prices, period, index=-1):
    if len(prices) < period:
        return None
    if index == -1:
        slice_prices = prices[-period:]
    else:
        slice_prices = prices[index - period + 1 : index + 1] if index + 1 != 0 else prices[index - period + 1:]
    return sum(slice_prices) / period

def analyze_technical(prices, valuation_rating):
    if len(prices) < 242:
        return {
            "close": prices[-1] if prices else 0.0,
            "mas": {p: 0.0 for p in [5, 10, 20, 60, 120, 240]},
            "slopes": {p: "下彎" for p in [5, 10, 20, 60, 120, 240]},
            "ma_score": 0,
            "ma_rating": "均線評分差",
            "ma_reasons": ["歷史 K 線數據不足 242 天，無法評估均線"],
            "bias_score": 0,
            "bias_rating": "乖離率評分差",
            "bias_reasons": ["歷史 K 線數據不足 242 天，無法評估乖離"],
            "score_str": "MA: 0 / Bias: 0",
            "rating": "均線評分差 | 乖離率評分差"
        }
        
    close = prices[-1]
    
    periods = [5, 10, 20, 60, 120, 240]
    mas = {}
    slopes = {}
    
    for p in periods:
        ma_today = calculate_ma(prices, p, -1)
        ma_prev = calculate_ma(prices, p, -2)
        mas[p] = ma_today
        slopes[p] = "上彎" if ma_today > ma_prev else "下彎"
        
    if valuation_rating == "SELL":
        # Valuation is SELL &跌破 5ma ➡️ 直接警示並評斷為 SELL
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
    for p in periods:
        if close < mas[p]:
            ma_score -= 10
            below_cnt += 1
    if below_cnt > 0:
        ma_reasons.append(f"股價低於 {below_cnt} 條均線 (-{below_cnt * 10})")
        
    # D. 每條均線若上彎各加 10 分，每下彎一條扣 10 分
    up_cnt = 0
    down_cnt = 0
    for p in periods:
        if slopes[p] == "上彎":
            ma_score += 10
            up_cnt += 1
        else:
            ma_score -= 10
            down_cnt += 1
    ma_reasons.append(f"均線 {up_cnt} 條上彎 (+{up_cnt * 10}), {down_cnt} 條下彎 (-{down_cnt * 10})")
    
    # MA Rating mapping
    if ma_score >= 80:
        ma_rating = "均線評分佳"
    elif 50 < ma_score < 80:
        ma_rating = "均線評分普通"
    else:
        ma_rating = "均線評分差"
        
    # 2. Bias Score (base = 100)
    bias_score = 100
    bias_reasons = []
    
    bias_5 = abs(close - mas[5]) / mas[5]
    bias_20 = abs(close - mas[20]) / mas[20]
    bias_60 = abs(close - mas[60]) / mas[60]
    
    # B. 股價乖離 5ma 超過 5%，扣 10 分
    if bias_5 > 0.05:
        bias_score -= 10
        bias_reasons.append(f"股價偏離 5MA ({bias_5*100:.1f}%) 超過 5% (-10)")
        
    # C. 股價乖離 20ma 超過 25%，扣 15 分
    if bias_20 > 0.25:
        bias_score -= 15
        bias_reasons.append(f"股價偏離 20MA ({bias_20*100:.1f}%) 超過 25% (-15)")
        
    # D. 股價乖離 60ma 超過 40%，扣 15 分
    if bias_60 > 0.40:
        bias_score -= 15
        bias_reasons.append(f"股價偏離 60MA ({bias_60*100:.1f}%) 超過 40% (-15)")
        
    # E. 股價乖離 5ma 超過 10%，再扣 15 分
    if bias_5 > 0.10:
        bias_score -= 15
        bias_reasons.append(f"股價偏離 5MA ({bias_5*100:.1f}%) 超過 10% (追加扣分 -15)")
        
    # F. 股價乖離 5ma 超過 15%，再扣 20 分
    if bias_5 > 0.15:
        bias_score -= 20
        bias_reasons.append(f"股價偏離 5MA ({bias_5*100:.1f}%) 超過 15% (追加扣分 -20)")
        
    # Bias Rating mapping
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
# 4. Target EPS Parser from Note Tables
# ==========================================
def parse_target_eps(filepath, target_year):
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
# 5. Lossless Markdown Note Rewriter
# ==========================================
def update_stock_file(filepath, current_price, forward_pe, rating, target_year, ma_info, tdcc_info):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f"Failed to read {filepath}: {e}")
        return False
        
    m_yaml = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
    if not m_yaml:
        print(f"Error: YAML frontmatter not found in {os.path.basename(filepath)}")
        return False
        
    yaml_text = m_yaml.group(1)
    body_text = m_yaml.group(2)
    
    # A. Update YAML frontmatter
    yaml_lines = yaml_text.split('\n')
    new_yaml_lines = []
    
    keys_to_update = {
        "current_price": str(current_price),
        "forward_pe": f"{forward_pe:.2f}" if isinstance(forward_pe, (float, int)) else f'"{forward_pe}"',
        "valuation_rating": f'"{rating}"',
        "tactical_score": f'"{ma_info["score_str"]}"',
        "tactical_action": f'"{ma_info["rating"]}"'
    }
    keys_found = {k: False for k in keys_to_update}
    
    for line in yaml_lines:
        line_stripped = line.strip()
        if not line_stripped:
            new_yaml_lines.append(line)
            continue
        m_key = re.match(r'^([a-zA-Z0-9\-_]+)\s*:(.*)$', line_stripped)
        if m_key:
            key = m_key.group(1).strip()
            if key in keys_to_update:
                new_yaml_lines.append(f"{key}: {keys_to_update[key]}")
                keys_found[key] = True
            else:
                new_yaml_lines.append(line)
        else:
            new_yaml_lines.append(line)
            
    for key, val in keys_to_update.items():
        if not keys_found[key]:
            new_yaml_lines.append(f"{key}: {val}")
            
    new_yaml = "\n".join(new_yaml_lines)
    
    # B. Update Valuation rating line in body
    date_str = datetime.now().strftime("%Y-%m-%d")
    pe_str = f"{forward_pe:.2f}x" if isinstance(forward_pe, (float, int)) else "待補充"
    valuation_line = f"* **評價裁決 (Valuation)**：`{rating}` (更新日期：{date_str}，收盤股價：{current_price} 元，{target_year} 預估 P/E：{pe_str}，原因：由收盤股價與 {target_year} 年預估平均 EPS 自動推算判定。門檻：<25 為 ADD/BUY，25~35 為 HOLD，>35 為 SELL)"
    
    body_text, count_val = re.subn(
        r'^\s*[\-\*]\s+\*\*評價裁決.*?\*\*：.*$',
        valuation_line,
        body_text,
        flags=re.MULTILINE
    )
    
    # C. Update Tactical action line in body
    if ma_info["rating"] == "SELL":
        tactical_line = f"* **操作裁決 (Tactical)**：`SELL` (當前股價：{current_price} 元，警示原因：估值偏高且收盤價跌破 5MA {ma_info['mas'][5]:.1f})"
    else:
        tactical_line = f"* **操作裁決 (Tactical)**：`{ma_info['rating']}` (當前股價：{current_price} 元，均線評分：{ma_info['ma_score']} 分，乖離率評分：{ma_info['bias_score']} 分)"
        
    body_text, count_tac = re.subn(
        r'^\s*[\-\*]\s+\*\*操作裁決.*?\*\*：.*$',
        tactical_line,
        body_text,
        flags=re.MULTILINE
    )
    if count_tac == 0:
        m_val_pos = re.search(r'^\s*[\-\*]\s+\*\*評價裁決.*?\*\*：.*$', body_text, re.MULTILINE)
        if m_val_pos:
            pos = m_val_pos.end()
            body_text = body_text[:pos] + "\n" + tactical_line + body_text[pos:]
            
    # D. Parse/Update Shareholding Table
    shareholding_title = "### 👥 籌碼面與大戶持股 (Shareholding)"
    shareholding_idx = body_text.find(shareholding_title)
    
    history_rows = []
    if shareholding_idx != -1:
        block_end = body_text.find("###", shareholding_idx + len(shareholding_title))
        if block_end == -1:
            block_end = body_text.find("##", shareholding_idx + len(shareholding_title))
        block_text = body_text[shareholding_idx:block_end] if block_end != -1 else body_text[shareholding_idx:]
        
        for line in block_text.split('\n'):
            line = line.strip()
            if line.startswith('|') and '週別' not in line and '---' not in line:
                cols = [c.strip() for c in line.split('|')]
                if len(cols) >= 5:
                    history_rows.append({
                        "date": cols[1],
                        "ratio_400": cols[2],
                        "ratio_1000": cols[3],
                        "trend": cols[4]
                    })
                    
    if tdcc_info:
        new_date = tdcc_info["date"]
        exists = any(r["date"] == new_date for r in history_rows)
        if not exists:
            history_rows.insert(0, {
                "date": new_date,
                "ratio_400": f"{tdcc_info['ratio_400']:.2f}%",
                "ratio_1000": f"{tdcc_info['ratio_1000']:.2f}%",
                "trend": "計算中"
            })
            
    # Calculate chip rating trend for first 3 rows
    if len(history_rows) >= 3:
        try:
            r1_400 = float(history_rows[0]["ratio_400"].replace('%', ''))
            r2_400 = float(history_rows[1]["ratio_400"].replace('%', ''))
            r3_400 = float(history_rows[2]["ratio_400"].replace('%', ''))
            
            r1_1000 = float(history_rows[0]["ratio_1000"].replace('%', ''))
            r2_1000 = float(history_rows[1]["ratio_1000"].replace('%', ''))
            r3_1000 = float(history_rows[2]["ratio_1000"].replace('%', ''))
            
            if r1_400 > r2_400 > r3_400 and r1_1000 > r2_1000 > r3_1000:
                trend = "連續兩週上升 (籌碼極佳)"
            elif r1_400 > r2_400 > r3_400 or r1_1000 > r2_1000 > r3_1000:
                trend = "持股比例上升 (籌碼偏佳)"
            elif r1_400 < r2_400 < r3_400 and r1_1000 < r2_1000 < r3_1000:
                trend = "連續兩週下降 (籌碼偏弱)"
            else:
                trend = "波動震盪 (籌碼中性)"
        except ValueError:
            trend = "波動震盪 (籌碼中性)"
    elif len(history_rows) >= 2:
        try:
            r1_400 = float(history_rows[0]["ratio_400"].replace('%', ''))
            r2_400 = float(history_rows[1]["ratio_400"].replace('%', ''))
            if r1_400 > r2_400:
                trend = "持股比例上升 (籌碼偏佳)"
            elif r1_400 < r2_400:
                trend = "持股比例下降 (籌碼偏弱)"
            else:
                trend = "無變動 (籌碼中性)"
        except ValueError:
            trend = "無變動 (籌碼中性)"
    else:
        trend = "無足夠歷史數據 (籌碼中性)"
        
    if history_rows:
        history_rows[0]["trend"] = trend
        
    shareholding_text = f"{shareholding_title}\n"
    shareholding_text += "| 週別 | 400張大戶比例 | 1000張大戶比例 | 大戶持股變動 / 評分 |\n"
    shareholding_text += "| :--- | :--- | :--- | :--- |\n"
    for r in history_rows:
        shareholding_text += f"| {r['date']} | {r['ratio_400']} | {r['ratio_1000']} | {r['trend']} |\n"
        
    # E. Build Technical Analysis Section
    ma_reasons_bullets = "\n".join([f"  - {reason}" for reason in ma_info["ma_reasons"]])
    bias_reasons_bullets = "\n".join([f"  - {reason}" for reason in ma_info["bias_reasons"]])
    
    tech_title = "### 📈 技術面與均線分析 (Technical Analysis)"
    tech_text = f"{tech_title}\n"
    tech_text += f"* **當前收盤價**：{current_price} 元\n"
    tech_text += f"* **均線價格與斜率**：\n"
    for p in [5, 10, 20, 60, 120, 240]:
        tech_text += f"  - {p}MA: {ma_info['mas'][p]:.2f} ({ma_info['slopes'][p]})\n"
        
    if ma_info["rating"] == "SELL":
        tech_text += f"* **技術評分警示** (評為 **SELL**)：\n{ma_reasons_bullets}\n"
    else:
        tech_text += f"* **均線評分** (總分：{ma_info['ma_score']} 分，評為 **{ma_info['ma_rating']}**)：\n{ma_reasons_bullets}\n"
        tech_text += f"* **乖離率評分** (總分：{ma_info['bias_score']} 分，評為 **{ma_info['bias_rating']}**)：\n{bias_reasons_bullets}\n"
    
    # F. Replace/Insert sections cleanly
    p_match = re.search(r'^\s*---\s*\n*##\s*📦\s*主要產品', body_text, re.MULTILINE)
    if not p_match:
        p_match = re.search(r'^##\s*📦\s*主要產品', body_text, re.MULTILINE)
        
    if p_match:
        pos = p_match.start()
        fin_match = re.search(r'###\s*📊\s*財務數據與\s*EPS\s*預估比對', body_text)
        if fin_match:
            body_before = body_text[:pos].rstrip()
            body_before = re.sub(r'###\s*👥\s*籌碼面與大戶持股.*?(?=\n(?:##|###|---)|\Z)', '', body_before, flags=re.DOTALL)
            body_before = re.sub(r'###\s*📈\s*技術面與均線分析.*?(?=\n(?:##|###|---)|\Z)', '', body_before, flags=re.DOTALL)
            body_before = body_before.rstrip()
            
            new_body = body_before + "\n\n" + shareholding_text + "\n" + tech_text + "\n" + body_text[pos:]
        else:
            new_body = body_text
    else:
        new_body = body_text
        
    final_content = "---\n" + new_yaml + "\n---\n" + new_body
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_content)
        
    return True

# ==========================================
# 6. Main Orchestrator
# ==========================================
if __name__ == "__main__":
    stock_dir = r"c:\Users\User\Desktop\LucasBrain\10_Stocks"
    files = [os.path.join(stock_dir, f) for f in os.listdir(stock_dir) if f.endswith('.md')]
    
    current_year = datetime.now().year
    target_year = current_year + 1
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Target Year for Forward P/E: {target_year}")
    
    # 1. Download and parse TDCC data once
    tdcc_cache = download_and_parse_tdcc()
    
    success_cnt = 0
    fail_cnt = 0
    
    print(f"Scanning {len(files)} stock notes in 10_Stocks/...")
    for fp in files:
        filename = os.path.basename(fp)
        m = re.match(r'^([0-9]+(?:\.[a-zA-Z0-9]+)?)(.*?)\.md$', filename)
        if not m:
            continue
        ticker = m.group(1).strip()
        
        # 1. Fetch historical closing prices (last 2 years of daily data)
        prices = get_historical_prices_fallback(ticker)
        if not prices:
            print(f"Skipping {filename}: Unable to fetch market price history.")
            continue
        current_price = prices[-1]
            
        # 2. Parse target EPS (e.g. 2027)
        avg_target_eps = parse_target_eps(fp, target_year)
        
        # 3. Compute Forward P/E & Valuation Rating
        if avg_target_eps is not None and avg_target_eps > 0:
            forward_pe = current_price / avg_target_eps
            if forward_pe < 25:
                valuation_rating = "ADD"
            elif 25 <= forward_pe <= 35:
                valuation_rating = "HOLD"
            else:
                valuation_rating = "SELL"
        else:
            forward_pe = "待補充"
            valuation_rating = "HOLD"
            
        # 4. Perform Moving Average and Double Scoring Analysis
        ma_info = analyze_technical(prices, valuation_rating)
        
        # 5. Extract TDCC weekly data for this ticker
        tdcc_info = tdcc_cache.get(ticker)
        
        # 6. Update markdown note file
        ok = update_stock_file(fp, current_price, forward_pe, valuation_rating, target_year, ma_info, tdcc_info)
        if ok:
            success_cnt += 1
            print(f"Updated {filename}: Price={current_price}, {target_year}E EPS={avg_target_eps}, PE={forward_pe}, Valuation={valuation_rating}, Tactical={ma_info['rating']}")
        else:
            fail_cnt += 1
            
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Completed: {success_cnt} files updated successfully, {fail_cnt} failed.")
