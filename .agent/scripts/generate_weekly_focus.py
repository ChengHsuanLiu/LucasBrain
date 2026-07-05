import os
import re
import sys
from datetime import datetime

def parse_target_eps(filepath, target_year):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
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

def extract_core_points(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        return ""
        
    points = []
    # Find section "## 🎯 投資建議與核心結論 (Summary)"
    summary_idx = content.find("## 🎯 投資建議與核心結論 (Summary)")
    if summary_idx == -1:
        summary_idx = content.find("## 🎯 投資建議與核心結論")
        
    if summary_idx != -1:
        # Find next header
        next_header = content.find("##", summary_idx + 20)
        block = content[summary_idx:next_header] if next_header != -1 else content[summary_idx:]
        
        # Look for bullet points under "核心論點"
        core_論點_idx = block.find("核心論點")
        if core_論點_idx != -1:
            sub_block = block[core_論點_idx:]
            # Find lines starting with "-" or "*" inside sub_block but avoid lines containing "評價裁決" or "操作裁決"
            for line in sub_block.split('\n'):
                line = line.strip()
                if (line.startswith('-') or line.startswith('*')) and "核心論點" not in line and "評價裁決" not in line and "操作裁決" not in line:
                    clean_line = re.sub(r'[\*\#\`]', '', line)
                    clean_line = clean_line.lstrip('-* ').strip()
                    if clean_line:
                        points.append(clean_line)
                        if len(points) >= 2: # Keep top 2 points
                            break
                            
    return "; ".join(points) if points else "基本面追蹤中。"

def extract_detailed_reasons(content, is_sell):
    if is_sell:
        return "估值偏高且收盤價跌破 5MA", "估值偏高且收盤價跌破 5MA"
        
    ma_reasons = []
    bias_reasons = []
    
    # 1. Parse MA reasons
    m_ma = re.search(r'^\s*[\-\*]\s+\*\*均線評分\*\*.*?\n(.*?(?=\n(?:[\-\*]\s+\*\*|\Z|##|###)))', content, re.MULTILINE | re.DOTALL)
    if m_ma:
        block_ma = m_ma.group(1)
        for line in block_ma.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                clean = re.sub(r'[\*\#\`]', '', line).lstrip('-* ').strip()
                if clean:
                    ma_reasons.append(clean)
                    
    # 2. Parse Bias reasons
    m_bias = re.search(r'^\s*[\-\*]\s+\*\*乖離率評分\*\*.*?\n(.*?(?=\n(?:[\-\*]\s+\*\*|\Z|##|###)))', content, re.MULTILINE | re.DOTALL)
    if m_bias:
        block_bias = m_bias.group(1)
        for line in block_bias.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                clean = re.sub(r'[\*\#\`]', '', line).lstrip('-* ').strip()
                if clean:
                    bias_reasons.append(clean)
                    
    ma_reasons_str = "；".join(ma_reasons) if ma_reasons else "均線狀態正常"
    bias_reasons_str = "；".join(bias_reasons) if bias_reasons else "無乖離扣分項"
    
    return ma_reasons_str, bias_reasons_str

def generate_weekly_report(target_date=None):
    if target_date is None:
        target_date = datetime.now().strftime("%Y%m%d")
        
    # Format dates
    date_obj = datetime.strptime(target_date, "%Y%m%d")
    date_hyphen = date_obj.strftime("%Y-%m-%d")
    
    stock_dir = r"c:\Users\User\Desktop\LucasBrain\10_Stocks"
    dest_dir = r"c:\Users\User\Desktop\LucasBrain\30_Projects\Weekly_Focus"
    os.makedirs(dest_dir, exist_ok=True)
    
    dest_filepath = os.path.join(dest_dir, f"{target_date}_Weekly_Focus.md")
    
    target_year = date_obj.year + 1 # Next year PE
    
    add_stocks = []
    sell_stocks = []
    
    files = [os.path.join(stock_dir, f) for f in os.listdir(stock_dir) if f.endswith('.md')]
    for fp in files:
        filename = os.path.basename(fp)
        m = re.match(r'^([0-9]+(?:\.[a-zA-Z0-9]+)?)(.*?)\.md$', filename)
        if not m:
            continue
        ticker = m.group(1).strip()
        name = m.group(2).strip()
        
        # Read frontmatter
        try:
            with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except:
            continue
            
        m_yaml = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not m_yaml:
            continue
            
        yaml_text = m_yaml.group(1)
        
        # Parse fields
        rating = "HOLD"
        price = 0.0
        pe = "待補充"
        tactical = "Wait for Setup"
        score_raw = "MA: 0 / Bias: 100"
        
        for line in yaml_text.split('\n'):
            line = line.strip()
            if line.startswith("valuation_rating:"):
                rating = line.split(":", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("current_price:"):
                try:
                    price = float(line.split(":", 1)[1].strip())
                except:
                    price = 0.0
            elif line.startswith("forward_pe:"):
                pe_raw = line.split(":", 1)[1].strip().strip('"').strip("'")
                try:
                    pe = f"{float(pe_raw):.2f}x"
                except:
                    pe = pe_raw
            elif line.startswith("tactical_action:"):
                tactical = line.split(":", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("tactical_score:"):
                score_raw = line.split(":", 1)[1].strip().strip('"').strip("'")
                
        # Parse scores
        ma_score = 0
        bias_score = 100
        m_score = re.match(r'MA:\s*(-?\d+)\s*/\s*Bias:\s*(-?\d+)', score_raw)
        if m_score:
            ma_score = int(m_score.group(1))
            bias_score = int(m_score.group(2))
            
        # Parse ratings from tactical_action
        ma_rating = "均線評分普通"
        bias_rating = "乖離率評分佳"
        is_sell = False
        if tactical == "SELL":
            ma_rating = "SELL"
            bias_rating = "SELL"
            is_sell = True
        else:
            parts = tactical.split('|')
            if len(parts) >= 2:
                ma_rating = parts[0].strip()
                bias_rating = parts[1].strip()
            elif len(parts) == 1:
                ma_rating = parts[0].strip()
                
        # Parse EPS
        eps = parse_target_eps(fp, target_year)
        eps_str = f"{eps:.2f}" if eps is not None else "待補充"
        
        # Extract 2 core points
        summary_points = extract_core_points(fp)
        
        # Extract detailed reasons
        ma_reasons, bias_reasons = extract_detailed_reasons(content, is_sell)
        
        stock_info = {
            "ticker": ticker,
            "name": name,
            "price": price,
            "eps": eps_str,
            "pe": pe,
            "ma_rating": ma_rating,
            "ma_score": ma_score,
            "ma_reasons": ma_reasons,
            "bias_rating": bias_rating,
            "bias_score": bias_score,
            "bias_reasons": bias_reasons,
            "summary": summary_points,
            "filepath": fp
        }
        
        if rating == "ADD":
            add_stocks.append(stock_info)
        elif rating == "SELL":
            sell_stocks.append(stock_info)
            
    # Sort by ticker
    add_stocks.sort(key=lambda x: x["ticker"])
    sell_stocks.sort(key=lambda x: x["ticker"])
    
    # Generate content matching weekly focus template
    report = []
    report.append("---")
    report.append("type: weekly_report")
    report.append(f"date: {date_hyphen}")
    report.append("author: LucasBrain AI")
    report.append("tags: [investment/weekly-focus, portfolio/rebalancing]")
    report.append(f"aliases: [週度投資建議, 週報-{date_hyphen}]")
    report.append("---")
    report.append("")
    report.append(f"# 🧭 LucasBrain 週度投資決策與持股追蹤 ({date_hyphen})")
    report.append("")
    report.append("> [!NOTE]")
    report.append(f"> * **出具日期**：{date_hyphen}")
    report.append("> * **當前市場位階**：[如：高檔震盪/回檔修正/起漲突破]")
    report.append("> * **本週策略主軸**：[如：防守型配置/伺機加碼高階電子/避開估值過高個股]")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 📊 一、 本週大盤宏觀簡評 & 產業風向 (Market Outlook)")
    report.append("* **大盤看法**：[簡述本週加權指數/美股主要指數趨勢]")
    report.append("* **產業最關鍵變動 (So What?)**：")
    report.append("  - **[產業A，如：CCL銅箔基板]**：[例如：上游玻纖布漲價順利轉嫁，帶動高階 CCL 廠重估。]")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 🟢 二、 建議加碼 / 逢低佈局區 (Add Focus)")
    report.append("> [!TIP]")
    report.append("> 此區域列出估值偏低、具安全邊際，且長期基本面與催化劑（Catalysts）確立的加碼標的 (Valuation Rating 為 **ADD**)。")
    report.append("")
    
    # Category 1: 動能趨勢股 (均線評分佳)
    report.append("### 📈 1. 動能趨勢股")
    report.append("> [!NOTE]")
    report.append("> **篩選條件**：Valuation 為 **ADD** 且 **均線評分佳**，乖離率不限。")
    report.append("")
    report.append(f"| 股票代號 / 名稱 | 評價裁決 | 均線評級 / 分數 (MA) | 乖離評級 / 分數 (Bias) | 當前股價 (元) | {target_year}年 預估 EPS | Forward P/E | 投資簡述與核心利多 (So What?) |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    trend_stocks = [s for s in add_stocks if s["ma_rating"] == "均線評分佳"]
    if trend_stocks:
        for s in trend_stocks:
            report.append(f"| `[[{s['ticker']}{s['name']}]]` | `ADD` | `{s['ma_rating']} ({s['ma_score']}分) <br> 原因：{s['ma_reasons']}` | `{s['bias_rating']} ({s['bias_score']}分) <br> 原因：{s['bias_reasons']}` | {s['price']} | {s['eps']} | {s['pe']}x | {s['summary']} |")
    else:
        report.append("| [無符合個股] | | | | | | | |")
        
    report.append("")
    
    # Category 2: 均線整理股 (均線評分普通)
    report.append("### ⏳ 2. 均線整理股")
    report.append("> [!NOTE]")
    report.append("> **篩選條件**：Valuation 為 **ADD** 且 **均線評分普通**，乖離率不限。")
    report.append("")
    report.append(f"| 股票代號 / 名稱 | 評價裁決 | 均線評級 / 分數 (MA) | 乖離評級 / 分數 (Bias) | 當前股價 (元) | {target_year}年 預估 EPS | Forward P/E | 投資簡述與核心利多 (So What?) |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    consolidation_stocks = [s for s in add_stocks if s["ma_rating"] == "均線評分普通"]
    if consolidation_stocks:
        for s in consolidation_stocks:
            report.append(f"| `[[{s['ticker']}{s['name']}]]` | `ADD` | `{s['ma_rating']} ({s['ma_score']}分) <br> 原因：{s['ma_reasons']}` | `{s['bias_rating']} ({s['bias_score']}分) <br> 原因：{s['bias_reasons']}` | {s['price']} | {s['eps']} | {s['pe']}x | {s['summary']} |")
    else:
        report.append("| [無符合個股] | | | | | | | |")
        
    report.append("")
    
    # Category 3: 左側機會股 (均線評分差)
    report.append("### 🔍 3. 左側機會股")
    report.append("> [!NOTE]")
    report.append("> **篩選條件**：Valuation 為 **ADD** 且 **均線評分差**，乖離率不限。")
    report.append("")
    report.append(f"| 股票代號 / 名稱 | 評價裁決 | 均線評級 / 分數 (MA) | 乖離評級 / 分數 (Bias) | 當前股價 (元) | {target_year}年 預估 EPS | Forward P/E | 投資簡述與核心利多 (So What?) |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    opportunity_stocks = [s for s in add_stocks if s["ma_rating"] == "均線評分差"]
    if opportunity_stocks:
        for s in opportunity_stocks:
            report.append(f"| `[[{s['ticker']}{s['name']}]]` | `ADD` | `{s['ma_rating']} ({s['ma_score']}分) <br> 原因：{s['ma_reasons']}` | `{s['bias_rating']} ({s['bias_score']}分) <br> 原因：{s['bias_reasons']}` | {s['price']} | {s['eps']} | {s['pe']}x | {s['summary']} |")
    else:
        report.append("| [無符合個股] | | | | | | | |")
        
    report.append("")
    report.append("### 🔍 加碼個股重點剖析")
    if add_stocks:
        for s in add_stocks[:5]: #剖析前5檔
            report.append(f"* **`[[{s['ticker']}{s['name']}]]`**：")
            report.append(f"  - **核心驅動因子**：{s['summary']}")
            report.append("  - **操作防守建議**：[均線與乖離率評估，建議於均線支撐附近分批布局。]")
    else:
        report.append("* [無個股剖析資料]")
        
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 🔴 三、 建議減碼 / 避開防守區 (Sell / Avoid Focus)")
    report.append("> [!CAUTION]")
    report.append("> 此區域列出估值偏高、短期乖離率過大，或基本面/供應鏈地位出現警訊的個股 (Valuation Rating 為 **SELL**)。")
    report.append("")
    report.append("### 📌 減碼/避開個股清單表")
    report.append(f"| 股票代號 / 名稱 | 評價裁決 | 均線評級 / 分數 (MA) | 乖離評級 / 分數 (Bias) | 當前股價 (元) | {target_year}年 預估 EPS | Forward P/E | 潛在利空與防守退場點 (So What?) |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    if sell_stocks:
        for s in sell_stocks:
            report.append(f"| `[[{s['ticker']}{s['name']}]]` | `SELL` | `{s['ma_rating']} ({s['ma_score']}分) <br> 原因：{s['ma_reasons']}` | `{s['bias_rating']} ({s['bias_score']}分) <br> 原因：{s['bias_reasons']}` | {s['price']} | {s['eps']} | {s['pe']}x | {s['summary']} |")
    else:
        report.append("| [無符合個股] | | | | | | | |")
        
    report.append("")
    report.append("### 🔍 避開/減碼個股重點剖析")
    if sell_stocks:
        for s in sell_stocks:
            report.append(f"* **`[[{s['ticker']}{s['name']}]]`**：")
            report.append(f"  - **核心風險因子**：{s['summary']}")
            report.append("  - **操作防守建議**：[估值偏高，若股價破線跌破關鍵均線建議果斷避開。]")
    else:
        report.append("* [無個股剖析資料]")
        
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 🤝 四、 關聯產業鏈動態與動能觀察 (Sector Momentum)")
    report.append("* **動能轉強產業**：[填寫轉強產業，如：CCL銅箔基板]")
    report.append("* **動能轉弱產業**：[填寫轉弱產業]")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 📅 五、 下週關鍵催化劑與重大時間軸 (Upcoming Catalysts)")
    report.append("* **下週重要時間點**：[填寫重大事件，如法說會、解盲時間等]")
    report.append("")
    
    md_text = "\n".join(report)
    with open(dest_filepath, 'w', encoding='utf-8') as f:
        f.write(md_text)
        
    print(f"Generated Weekly Focus report at: {dest_filepath}")
    
    # Generate PDF
    dest_filepath_pdf = os.path.join(dest_dir, f"{target_date}_Weekly_Focus.pdf")
    try:
        import markdown
        import subprocess
        
        # Pre-process markdown to handle github alerts elegantly in PDF
        processed_md = md_text
        processed_md = re.sub(r'\[!NOTE\]', r'🔔 **備註**', processed_md)
        processed_md = re.sub(r'\[!TIP\]', r'💡 **提示**', processed_md)
        processed_md = re.sub(r'\[!IMPORTANT\]', r'⚠️ **重要**', processed_md)
        processed_md = re.sub(r'\[!WARNING\]', r'⚡ **警告**', processed_md)
        processed_md = re.sub(r'\[!CAUTION\]', r'🛑 **注意**', processed_md)
        
        html_body = markdown.markdown(processed_md, extensions=['tables', 'fenced_code'])
        
        # Complete HTML with styling
        html_content = f"""
        <html>
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <style>
            @page {{
                size: a4;
                margin: 2cm;
            }}
            body {{
                font-family: "Microsoft JhengHei", "Segoe UI", system-ui, sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #1e293b;
                background-color: #ffffff;
            }}
            h1 {{
                font-size: 22pt;
                color: #0f172a;
                text-align: center;
                margin-bottom: 25px;
                padding-bottom: 12px;
                border-bottom: 3px solid #3b82f6;
                font-weight: 700;
            }}
            h2 {{
                font-size: 15pt;
                color: #1e3a8a;
                margin-top: 30px;
                margin-bottom: 15px;
                padding-bottom: 6px;
                border-bottom: 1px solid #cbd5e1;
                font-weight: 600;
            }}
            h3 {{
                font-size: 12pt;
                color: #0f766e;
                margin-top: 20px;
                margin-bottom: 10px;
                font-weight: 600;
            }}
            p, ul, ol {{
                margin-bottom: 12px;
            }}
            li {{
                margin-bottom: 6px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                margin-bottom: 20px;
                font-size: 9pt;
                border-radius: 6px;
                overflow: hidden;
                border: 1px solid #e2e8f0;
            }}
            th {{
                background-color: #1e293b;
                color: #ffffff;
                font-weight: 600;
                text-align: left;
                padding: 10px 12px;
                border: 1px solid #475569;
            }}
            td {{
                padding: 10px 12px;
                border: 1px solid #cbd5e1;
            }}
            tr:nth-child(even) {{
                background-color: #f8fafc;
            }}
            blockquote {{
                background-color: #f8fafc;
                border-left: 4px solid #3b82f6;
                padding: 10px 15px;
                margin: 15px 0;
                color: #475569;
                border-radius: 0 4px 4px 0;
            }}
            code {{
                font-family: "Consolas", "Microsoft JhengHei", monospace;
                background-color: #f1f5f9;
                color: #0f172a;
                padding: 2px 5px;
                border-radius: 4px;
                font-size: 9.5pt;
                border: 1px solid #e2e8f0;
            }}
        </style>
        </head>
        <body>
        {html_body}
        </body>
        </html>
        """
        
        # Save HTML temporarily
        temp_html_path = os.path.join(dest_dir, f"{target_date}_Weekly_Focus_temp.html")
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        
        def run_edge_print(output_pdf):
            cmd = [
                edge_path,
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={output_pdf}",
                temp_html_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        try:
            run_edge_print(dest_filepath_pdf)
            print(f"Generated Weekly Focus PDF at: {dest_filepath_pdf}")
        except PermissionError:
            import time
            timestamp = int(time.time())
            fallback_pdf = os.path.join(dest_dir, f"{target_date}_Weekly_Focus_{timestamp}.pdf")
            print(f"Warning: {dest_filepath_pdf} is locked by another program (e.g., PDF Reader).")
            print(f"Attempting to write to fallback path: {fallback_pdf}")
            run_edge_print(fallback_pdf)
            print(f"Generated Weekly Focus PDF at: {fallback_pdf}")
            
        # Clean up temp HTML
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
            
    except Exception as e:
        print(f"Failed to generate PDF: {e}")
        
    return dest_filepath

if __name__ == "__main__":
    t_date = sys.argv[1] if len(sys.argv) > 1 else None
    generate_weekly_report(t_date)
