import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.stock_metrics import (
    download_and_parse_tdcc,
    get_historical_prices_fallback,
    compute_ma_metrics,
    compute_tactical_score,
    parse_valuation_eps,
)
from lib.stock_signals import load_valuation_mode

# ==========================================
# 1. Lossless Markdown Note Rewriter
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

            # body_text[pos:] itself starts with whatever blank-line run precedes
            # "---" (the regex's leading \s* swallows it), and that run grows by one
            # line every time this function runs unless it's normalized back down —
            # otherwise the blank lines accumulate forever across repeated refreshes.
            tail = re.sub(r'^\s+', '\n\n', body_text[pos:])
            new_body = body_before + "\n\n" + shareholding_text + "\n" + tech_text + tail
        else:
            new_body = body_text
    else:
        new_body = body_text

    final_content = "---\n" + new_yaml + "\n---\n" + new_body
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_content)

    return True

# ==========================================
# 2. Main Orchestrator
# ==========================================
if __name__ == "__main__":
    stock_dir = r"c:\Users\User\Desktop\LucasBrain\10_Stocks"
    files = [os.path.join(stock_dir, f) for f in os.listdir(stock_dir) if f.endswith('.md')]

    # Optional: pass a ticker to refresh only that one stock (e.g. called by
    # generate_stock_report.py before producing a single-stock report), instead of
    # the full ~80-stock sweep this script normally does.
    target_ticker = sys.argv[1].strip() if len(sys.argv) > 1 else None
    if target_ticker:
        files = [fp for fp in files if os.path.basename(fp).startswith(target_ticker)]
        if not files:
            print(f"No stock note found for ticker {target_ticker} in 10_Stocks/.")
            sys.exit(1)

    current_year = datetime.now().year
    target_year = current_year + 1
    valuation_mode = load_valuation_mode()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Target Year for Forward P/E: {target_year} (估值模式: {valuation_mode})")

    # 1. Download and parse TDCC data once
    tdcc_cache = download_and_parse_tdcc()
    print(f"Successfully cached TDCC data for {len(tdcc_cache)} tickers.")

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

        # 2. Parse valuation EPS (依估值模式取明年或明年後年平均)
        avg_target_eps = parse_valuation_eps(fp, target_year, valuation_mode)

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

        # 4. Compute MA/Bias metrics, then apply the single tactical scoring rule set
        ma_metrics = compute_ma_metrics(prices)
        ma_info = compute_tactical_score(ma_metrics, valuation_rating)

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
