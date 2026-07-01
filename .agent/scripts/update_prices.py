import os
import re
import json
import urllib.request
from datetime import datetime

def fetch_price_from_yahoo(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            chart_res = data.get('chart', {}).get('result')
            if chart_res and len(chart_res) > 0:
                meta = chart_res[0].get('meta', {})
                price = meta.get('regularMarketPrice')
                return float(price) if price is not None else None
    except Exception as e:
        pass
    return None

def get_stock_price(ticker):
    ticker = ticker.strip()
    if ticker.isdigit():
        price = fetch_price_from_yahoo(f"{ticker}.TW")
        if price is not None:
            return price
        price = fetch_price_from_yahoo(f"{ticker}.TWO")
        if price is not None:
            return price
    else:
        price = fetch_price_from_yahoo(ticker)
        if price is not None:
            return price
        if ".TW" in ticker:
            fallback = ticker.replace(".TW", ".TWO")
            price = fetch_price_from_yahoo(fallback)
            if price is not None:
                return price
        elif ".TWO" in ticker:
            fallback = ticker.replace(".TWO", ".TW")
            price = fetch_price_from_yahoo(fallback)
            if price is not None:
                return price
        elif ".SH" in ticker:
            sh_ticker = ticker.replace(".SH", ".SS")
            price = fetch_price_from_yahoo(sh_ticker)
            if price is not None:
                return price
    return None

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

def update_stock_file(filepath, current_price, forward_pe, rating, target_year):
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
    
    yaml_lines = yaml_text.split('\n')
    new_yaml_lines = []
    keys_updated = {"current_price": False, "forward_pe": False, "valuation_rating": False}
    
    for line in yaml_lines:
        line_stripped = line.strip()
        if not line_stripped:
            new_yaml_lines.append(line)
            continue
            
        m_key = re.match(r'^([a-zA-Z0-9\-_]+)\s*:(.*)$', line_stripped)
        if m_key:
            key = m_key.group(1).strip()
            if key == "current_price":
                new_yaml_lines.append(f"current_price: {current_price}")
                keys_updated["current_price"] = True
            elif key == "forward_pe":
                new_yaml_lines.append(f"forward_pe: {forward_pe:.2f}" if isinstance(forward_pe, float) else f"forward_pe: \"{forward_pe}\"")
                keys_updated["forward_pe"] = True
            elif key == "valuation_rating":
                new_yaml_lines.append(f"valuation_rating: \"{rating}\"")
                keys_updated["valuation_rating"] = True
            else:
                new_yaml_lines.append(line)
        else:
            new_yaml_lines.append(line)
            
    if not keys_updated["current_price"]:
        new_yaml_lines.append(f"current_price: {current_price}")
    if not keys_updated["forward_pe"]:
        new_yaml_lines.append(f"forward_pe: {forward_pe:.2f}" if isinstance(forward_pe, float) else f"forward_pe: \"{forward_pe}\"")
    if not keys_updated["valuation_rating"]:
        new_yaml_lines.append(f"valuation_rating: \"{rating}\"")
        
    new_yaml = "\n".join(new_yaml_lines)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    pe_str = f"{forward_pe:.2f}x" if isinstance(forward_pe, float) else "待補充"
    
    replacement_rating_line = f"* **評價裁決**：`{rating}` (更新日期：{date_str}，收盤股價：{current_price} 元，{target_year} 預估 P/E：{pe_str}，原因：基於 {target_year} 預估 EPS 與 P/E 門檻自動判定)"
    
    body_text, count = re.subn(
        r'^\s*[\-\*]\s+\*\*評價裁決.*?\*\*：.*$',
        replacement_rating_line,
        body_text,
        flags=re.MULTILINE
    )
    
    if count == 0:
        m_core = re.search(r'^\s*[\-\*]\s+\*\*核心論點\*\*：', body_text, re.MULTILINE)
        if m_core:
            pos = m_core.start()
            body_text = body_text[:pos] + replacement_rating_line + "\n" + body_text[pos:]
            
    new_content = "---\n" + new_yaml + "\n---\n" + body_text
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    return True

if __name__ == "__main__":
    stock_dir = r"c:\Users\User\Desktop\LucasBrain\10_Stocks"
    files = [os.path.join(stock_dir, f) for f in os.listdir(stock_dir) if f.endswith('.md')]
    
    current_year = datetime.now().year
    target_year = current_year + 1
    print(f"Current Year: {current_year}, Target Year for Forward P/E: {target_year}")
    
    success_cnt = 0
    fail_cnt = 0
    
    print(f"Scanning {len(files)} stock notes in 10_Stocks/...")
    for fp in files:
        filename = os.path.basename(fp)
        # Extract ticker from filename e.g. 8358.TW金居.md -> 8358.TW; 3673TPK宸鴻.md -> 3673
        m = re.match(r'^([0-9]+(?:\.[a-zA-Z0-9]+)?)(.*?)\.md$', filename)
        if not m:
            continue
        ticker = m.group(1).strip()
        
        # 1. Fetch closing price
        price = get_stock_price(ticker)
        if price is None:
            print(f"Skipping {filename}: Unable to fetch market price.")
            continue
            
        # 2. Parse target EPS (e.g. 2027)
        avg_target_eps = parse_target_eps(fp, target_year)
        
        # 3. Compute Forward P/E & Rating
        if avg_target_eps is not None and avg_target_eps > 0:
            forward_pe = price / avg_target_eps
            if forward_pe < 25:
                rating = "ADD"
            elif 25 <= forward_pe <= 35:
                rating = "HOLD"
            else:
                rating = "SELL"
        else:
            forward_pe = "待補充"
            rating = "HOLD"  # Default rating if EPS is not available
            
        # 4. Update the note file
        ok = update_stock_file(fp, price, forward_pe, rating, target_year)
        if ok:
            success_cnt += 1
            print(f"Updated {filename}: Price={price}, {target_year}E EPS={avg_target_eps}, PE={forward_pe}, Rating={rating}")
        else:
            fail_cnt += 1
            
    print(f"\nCompleted: {success_cnt} files updated successfully, {fail_cnt} failed.")
