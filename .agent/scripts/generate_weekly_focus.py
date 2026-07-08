import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.stock_metrics import parse_target_eps

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
    
    # Helper to check if line represents a deduction
    def is_deduction(text):
        # Match negative numbers other than -0 (e.g. -10, -15, -20)
        return bool(re.search(r'-\s*[1-9]\d*', text))
        
    def clean_and_format_reason(text):
        # Remove (追加扣分 -15) or similar
        text = re.sub(r'\(\s*追加扣分\s*-\s*\d+\s*\)', '(追加扣分)', text)
        # Remove (-10) or similar
        text = re.sub(r'\(\s*-\s*\d+\s*\)', '', text)
        # Remove (+50) or similar
        text = re.sub(r'\(\s*\+\s*\d+\s*\)', '', text)
        # Clean up spaces around commas and double spaces
        text = re.sub(r'\s+,\s*', ', ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if "股價偏離" in text:
            # Match (10.1%) or similar
            pct_match = re.search(r'\(\s*(\d+(?:\.\d+)?%)\s*\)', text)
            if pct_match:
                pct_str = pct_match.group(0)
                text = text.replace(pct_str, "")
                text = re.sub(r'\s+,\s*', ', ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                if "追加扣分" in text:
                    text = text.replace("(追加扣分)", f"{pct_str} (追加扣分)")
                else:
                    text = f"{text} {pct_str}"
                text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    # 1. Parse MA reasons
    m_ma = re.search(r'^\s*[\-\*]\s+\*\*均線評分\*\*.*?\n(.*?(?=\n(?:[\-\*]\s+\*\*|\Z|##|###)))', content, re.MULTILINE | re.DOTALL)
    if m_ma:
        block_ma = m_ma.group(1)
        for line in block_ma.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                clean = re.sub(r'[\*\#\`]', '', line).lstrip('-* ').strip()
                if clean and is_deduction(clean):
                    ma_reasons.append(clean_and_format_reason(clean))
                    
    # 2. Parse Bias reasons
    m_bias = re.search(r'^\s*[\-\*]\s+\*\*乖離率評分\*\*.*?\n(.*?(?=\n(?:[\-\*]\s+\*\*|\Z|##|###)))', content, re.MULTILINE | re.DOTALL)
    if m_bias:
        block_bias = m_bias.group(1)
        for line in block_bias.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                clean = re.sub(r'[\*\#\`]', '', line).lstrip('-* ').strip()
                if clean and is_deduction(clean):
                    bias_reasons.append(clean_and_format_reason(clean))
                    
    ma_reasons_str = "；".join(ma_reasons) if ma_reasons else "無扣分項"
    bias_reasons_str = "；".join(bias_reasons) if bias_reasons else "無扣分項"
    
    return ma_reasons_str, bias_reasons_str

def generate_weekly_report(target_date=None):
    if target_date is None:
        target_date = datetime.now().strftime("%Y%m%d")
        
    # Format dates
    date_obj = datetime.strptime(target_date, "%Y%m%d")
    date_hyphen = date_obj.strftime("%Y-%m-%d")
    
    current_time_str = datetime.now().strftime("%H%M")
    filename_prefix = f"{target_date}{current_time_str}_Lucas_Weekly_Focus"
    
    stock_dir = r"c:\Users\User\Desktop\LucasBrain\10_Stocks"
    dest_dir = r"c:\Users\User\Desktop\LucasBrain\30_Projects\Weekly_Focus"
    os.makedirs(dest_dir, exist_ok=True)
    
    dest_filepath = os.path.join(dest_dir, f"{filename_prefix}.md")
    
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
        
        # Only process Taiwan stocks (purely numeric ticker)
        if not ticker.isdigit():
            continue
        
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
                    pe = f"{float(pe_raw):.1f}x"
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
        elif rating == "SELL" and tactical == "SELL":
            sell_stocks.append(stock_info)
            
    # Sort by ticker
    add_stocks.sort(key=lambda x: x["ticker"])
    sell_stocks.sort(key=lambda x: x["ticker"])
    
    # Generate content matching weekly focus template
    report = []
    # Format rating cell helper
    def format_rating_cell(rating_label, score, reasons):
        # 沿用台股慣例：紅=佳(漲)、綠=差(跌)，僅由行內 style 改為統一的 badge 樣式
        if "佳" in rating_label:
            badge_class = "badge-red"
        elif "普通" in rating_label:
            badge_class = "badge-amber"
        elif "差" in rating_label:
            badge_class = "badge-green"
        else:
            badge_class = "badge-amber"

        label_html = f'<span class="badge {badge_class}">{rating_label} ({score}分)</span>'

        if reasons and reasons != "無扣分項":
            norm_reasons = reasons.replace(';', '；')
            reasons_list = [r.strip() for r in norm_reasons.split('；') if r.strip()]
            reasons_formatted = "<br>".join(reasons_list)
            reasons_html = f'<div style="font-size: 8pt; color: #4b5563; margin-top: 4px; line-height: 1.3;">原因：<br>{reasons_formatted}</div>'
            return f"{label_html} {reasons_html}"
        else:
            return label_html

    # Format and truncate summary helper (150 chars max, wraps each reason to its own line)
    def format_summary(raw_summary):
        if not raw_summary:
            return "基本面追蹤中。"
        # Standardize punctuation (preserve float decimal points by not replacing '.')
        cleaned = raw_summary.replace('; ', '；').replace(';', '；').replace(':', '：')
        parts = []
        for p in re.split(r'[；。：\n]', cleaned):
            p = p.strip()
            if p:
                parts.append(p)
                
        formatted = ""
        for part in parts:
            if not part:
                continue
            if formatted:
                next_line = formatted + "<br>" + part
            else:
                next_line = part
                
            # Check length of the visible text content (excluding HTML tags)
            visible_len = len(next_line.replace("<br>", ""))
            if visible_len > 150:
                current_visible_len = len(formatted.replace("<br>", ""))
                allowed = 150 - current_visible_len - 3  # 3 for "..."
                if allowed > 0:
                    if formatted:
                        formatted += "<br>" + part[:allowed] + "..."
                    else:
                        formatted = part[:147] + "..."
                else:
                    formatted += "..."
                break
            else:
                formatted = next_line
        return formatted

    # Format detailed points as nested list items
    def format_detailed_points(raw_summary):
        if not raw_summary or raw_summary == "基本面追蹤中。":
            return "  - 基本面追蹤中。"
        cleaned = raw_summary.replace('；', ';').replace('; ', ';')
        parts = [p.strip() for p in cleaned.split(';') if p.strip()]
        bullets = []
        for p in parts:
            p = re.sub(r'[：:]$', '', p).strip()
            if p:
                bullets.append(f"  - {p}")
        return "\n".join(bullets)

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
    report.append(f"# {target_date}-Lucas每周AI選股")
    report.append("")
    report.append("## 一、 建議加碼 / 逢低佈局區 (Add Focus)")
    report.append("> [!TIP]")
    report.append("> 此區域列出估值偏低、具安全邊際，且長期基本面與催化劑（Catalysts）確立的加碼標的 (Valuation Rating 為 **ADD**)。")
    report.append("")
    
    # Category 1: 動能趨勢股 (均線評分佳)
    report.append("### 📈 1. 動能趨勢股")
    report.append("> [!NOTE]")
    report.append("> **篩選條件**：Valuation 為 **ADD** 且 **均線評分佳**，乖離率不限。")
    report.append("")
    report.append(f"| 股票 | 評價 | 均線評級 | 乖離評級 | 當前股價 (元) | {str(target_year)[2:]}EPS(F) | FP/E | 投資簡述 |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    trend_stocks = [s for s in add_stocks if s["ma_rating"] == "均線評分佳"]
    if trend_stocks:
        for s in trend_stocks:
            ma_cell = format_rating_cell(s["ma_rating"], s["ma_score"], s["ma_reasons"])
            bias_cell = format_rating_cell(s["bias_rating"], s["bias_score"], s["bias_reasons"])
            summary_cell = format_summary(s["summary"])
            report.append(f"| [[{s['ticker']}{s['name']}|{s['ticker']}<br>{s['name']}]] | `ADD` | {ma_cell} | {bias_cell} | {s['price']:.1f} | {s['eps']} | {s['pe']} | {summary_cell} |")
    else:
        report.append("| [無符合個股] | | | | | | | |")
        
    report.append("")
    
    # Category 2: 均線整理股 (均線評分普通)
    report.append("### ⏳ 2. 均線整理股")
    report.append("> [!NOTE]")
    report.append("> **篩選條件**：Valuation 為 **ADD** 且 **均線評分普通**，乖離率不限。")
    report.append("")
    report.append(f"| 股票 | 評價 | 均線評級 | 乖離評級 | 當前股價 (元) | {str(target_year)[2:]}EPS(F) | FP/E | 投資簡述 |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    consolidation_stocks = [s for s in add_stocks if s["ma_rating"] == "均線評分普通"]
    if consolidation_stocks:
        for s in consolidation_stocks:
            ma_cell = format_rating_cell(s["ma_rating"], s["ma_score"], s["ma_reasons"])
            bias_cell = format_rating_cell(s["bias_rating"], s["bias_score"], s["bias_reasons"])
            summary_cell = format_summary(s["summary"])
            report.append(f"| [[{s['ticker']}{s['name']}|{s['ticker']}<br>{s['name']}]] | `ADD` | {ma_cell} | {bias_cell} | {s['price']:.1f} | {s['eps']} | {s['pe']} | {summary_cell} |")
    else:
        report.append("| [無符合個股] | | | | | | | |")
        
    report.append("")
    
    # Category 3: 左側機會股 (均線評分差)
    report.append("### 🔍 3. 左側機會股")
    report.append("> [!NOTE]")
    report.append("> **篩選條件**：Valuation 為 **ADD** 且 **均線評分差**，乖離率不限. ")
    report.append("")
    report.append(f"| 股票 | 評價 | 均線評級 | 乖離評級 | 當前股價 (元) | {str(target_year)[2:]}EPS(F) | FP/E | 投資簡述 |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    opportunity_stocks = [s for s in add_stocks if s["ma_rating"] == "均線評分差"]
    if opportunity_stocks:
        for s in opportunity_stocks:
            ma_cell = format_rating_cell(s["ma_rating"], s["ma_score"], s["ma_reasons"])
            bias_cell = format_rating_cell(s["bias_rating"], s["bias_score"], s["bias_reasons"])
            summary_cell = format_summary(s["summary"])
            report.append(f"| [[{s['ticker']}{s['name']}|{s['ticker']}<br>{s['name']}]] | `ADD` | {ma_cell} | {bias_cell} | {s['price']:.1f} | {s['eps']} | {s['pe']} | {summary_cell} |")
    else:
        report.append("| [無符合個股] | | | | | | | |")
        
    report.append("")
    report.append("### 🔍 加碼個股重點剖析")
    if add_stocks:
        first = True
        for s in add_stocks[:5]: #剖析前5檔
            if not first:
                report.append("")
                report.append("---")
                report.append("")
            first = False
            report.append(f"#### 🏢 [[{s['ticker']}{s['name']}]]")
            report.append("* **核心驅動因子**：")
            report.append(format_detailed_points(s['summary']))
            report.append("* **估值與操作空間**：")
            report.append("  - 建議於均線支撐附近分批布局。")
    else:
        report.append("* [無個股剖析資料]")
        
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 二、 建議減碼 / 避開防守區 (Sell / Avoid Focus)")
    report.append("> [!CAUTION]")
    report.append("> 此區域列出估值偏高、短期乖離率過大，或基本面/供應鏈地位出現警訊的個股 (Valuation Rating 為 **SELL**)。")
    report.append("")
    report.append("### 📌 減碼/避開個股清單表")
    report.append(f"| 股票 | 評價 | 均線評級 | 乖離評級 | 當前股價 (元) | {str(target_year)[2:]}EPS(F) | FP/E | 潛在利空 |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    if sell_stocks:
        for s in sell_stocks:
            ma_cell = format_rating_cell(s["ma_rating"], s["ma_score"], s["ma_reasons"])
            bias_cell = format_rating_cell(s["bias_rating"], s["bias_score"], s["bias_reasons"])
            summary_cell = format_summary(s["summary"])
            report.append(f"| [[{s['ticker']}{s['name']}|{s['ticker']}<br>{s['name']}]] | `SELL` | {ma_cell} | {bias_cell} | {s['price']:.1f} | {s['eps']} | {s['pe']} | {summary_cell} |")
    else:
        report.append("| [無符合個股] | | | | | | | |")
        
    report.append("")
    report.append("### 🔍 避開/減碼個股重點剖析")
    if sell_stocks:
        first = True
        for s in sell_stocks:
            if not first:
                report.append("")
                report.append("---")
                report.append("")
            first = False
            report.append(f"#### 🏢 [[{s['ticker']}{s['name']}]]")
            report.append("* **核心風險因子**：")
            report.append(format_detailed_points(s['summary']))
            report.append("* **操作防守建議**：")
            report.append("  - 若股價破線跌破關鍵均線建議果斷避開。")
    else:
        report.append("* [無個股剖析資料]")
        
    report.append("")
    
    md_text = "\n".join(report)
    with open(dest_filepath, 'w', encoding='utf-8') as f:
        f.write(md_text)
        
    print(f"Generated Weekly Focus report at: {dest_filepath}")
    
    # Generate PDF
    dest_filepath_pdf = os.path.join(dest_dir, f"{filename_prefix}.pdf")
    try:
        import markdown
        import subprocess
        import pathlib
        import tempfile
        import time

        # Pre-process markdown to handle github alerts elegantly in PDF
        processed_md = md_text
        processed_md = re.sub(r'\[!NOTE\]', r'**註：**', processed_md)
        processed_md = re.sub(r'\[!TIP\]', r'**提示：**', processed_md)
        processed_md = re.sub(r'\[!IMPORTANT\]', r'**重要：**', processed_md)
        processed_md = re.sub(r'\[!WARNING\]', r'**警示：**', processed_md)
        processed_md = re.sub(r'\[!CAUTION\]', r'**注意：**', processed_md)

        # YAML frontmatter is for machine/AI consumption only — strip it entirely from the PDF.
        processed_md = re.sub(r'^---\n.*?\n---\n', '', processed_md, count=1, flags=re.DOTALL)

        # Strip any remaining emoji for a clean, professional look — this also catches emoji
        # embedded in note content pulled in verbatim from 10_Stocks/.
        emoji_pattern = re.compile(
            "[\U0001F300-\U0001FAFF\U00002300-\U000023FF\U00002B00-\U00002BFF"
            "\U00002600-\U000026FF\U00002700-\U000027BF\U0000FE0F]+",
            flags=re.UNICODE,
        )
        processed_md = emoji_pattern.sub("", processed_md)
        processed_md = re.sub(r'[ \t]+\n', '\n', processed_md)

        # Remove markdown backticks and [[ ]] brackets around stock codes/names for PDF rendering, keeping the alias if present
        def clean_links(match):
            text = match.group(1)
            if '|' in text:
                return text.split('|', 1)[1]
            return text
        processed_md = re.sub(r'`?\[\[([^\]]+)\]\]`?', clean_links, processed_md)
        
        html_body = markdown.markdown(processed_md, extensions=['tables', 'fenced_code'])
        
        # Complete HTML with styling
        html_content = f"""
        <html>
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <style>
            @page {{
                size: a4;
                margin: 1.9cm 1.6cm 1.8cm 1.6cm;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: "Microsoft JhengHei", "Segoe UI", system-ui, sans-serif;
                font-size: 10pt;
                line-height: 1.65;
                color: #1f2937;
                background-color: #ffffff;
            }}
            h1 {{
                font-family: "Noto Serif TC", "PMingLiU", "Microsoft JhengHei", serif;
                font-size: 20pt;
                font-weight: 700;
                color: #111827;
                margin: 2px 0 14px 0;
                padding-bottom: 10px;
                border-bottom: 2px solid #111827;
                letter-spacing: 0.01em;
            }}
            h2 {{
                font-family: "Noto Serif TC", "PMingLiU", "Microsoft JhengHei", serif;
                font-size: 14.5pt;
                font-weight: 700;
                color: #111827;
                margin-top: 4px;
                margin-bottom: 14px;
                padding-bottom: 8px;
                border-bottom: 2px solid #111827;
                page-break-before: always;
                break-before: page;
            }}
            h1 + h2 {{
                page-break-before: auto;
                break-before: auto;
            }}
            h3 {{
                font-size: 11pt;
                font-weight: 700;
                color: #111827;
                margin-top: 20px;
                margin-bottom: 8px;
                padding-top: 10px;
                border-top: 1px solid #d1d5db;
            }}
            h4 {{
                font-size: 10pt;
                color: #1f2937;
                margin-top: 14px;
                margin-bottom: 6px;
                font-weight: 700;
            }}
            p, ul, ol {{
                margin: 0 0 10px 0;
            }}
            li {{
                margin-bottom: 4px;
            }}
            hr {{
                border: none;
                border-top: 1px solid #d1d5db;
                margin: 16px 0;
            }}
            table {{
                width: 100%;
                table-layout: fixed;
                border-collapse: collapse;
                margin: 8px 0 16px 0;
                font-size: 8pt;
            }}
            th:nth-child(1), td:nth-child(1) {{ width: 8%; }} /* 股票 */
            th:nth-child(2), td:nth-child(2) {{ width: 5%; text-align: center; }} /* 評價 */
            th:nth-child(3), td:nth-child(3) {{ width: 18%; }} /* 均線評級 */
            th:nth-child(4), td:nth-child(4) {{ width: 18%; }} /* 乖離評級 */
            th:nth-child(5), td:nth-child(5) {{ width: 8%; text-align: right; }} /* 當前股價 */
            th:nth-child(6), td:nth-child(6) {{ width: 8%; text-align: right; }} /* 27EPS(F) */
            th:nth-child(7), td:nth-child(7) {{ width: 7%; text-align: right; }} /* FP/E */
            th:nth-child(8), td:nth-child(8) {{ width: 28%; }} /* 投資簡述 */

            th {{
                background: #ffffff;
                color: #111827;
                font-weight: 700;
                text-align: left;
                padding: 5px 6px;
                border-top: 1.5px solid #111827;
                border-bottom: 1px solid #111827;
            }}
            th:nth-child(2) {{ text-align: center; }}
            th:nth-child(5), th:nth-child(6), th:nth-child(7) {{ text-align: right; }}

            td {{
                padding: 5px 6px;
                border-bottom: 1px solid #e5e7eb;
                vertical-align: top;
            }}
            tr:last-child td {{
                border-bottom: 1px solid #111827;
            }}
            tr:nth-child(even) td {{
                background-color: #f9fafb;
            }}
            blockquote {{
                border-left: 3px solid #9ca3af;
                padding: 3px 12px;
                margin: 12px 0;
                color: #4b5563;
                font-size: 9.3pt;
            }}
            blockquote p {{ margin: 0; }}
            code {{
                font-family: "Consolas", "Microsoft JhengHei", monospace;
                background-color: #f3f4f6;
                color: #111827;
                padding: 1px 4px;
                border-radius: 2px;
                font-size: 8.7pt;
            }}
            .badge {{
                display: inline-block;
                padding: 1px 8px;
                border-radius: 3px;
                font-size: 8pt;
                font-weight: 700;
                letter-spacing: 0.02em;
            }}
            .badge-green {{ color: #065f46; background: #d1fae5; }}
            .badge-amber {{ color: #92400e; background: #fef3c7; }}
            .badge-red {{ color: #991b1b; background: #fee2e2; }}
        </style>
        </head>
        <body>
        {html_body}
        </body>
        </html>
        """
        
        # Save HTML temporarily
        temp_html_path = os.path.join(dest_dir, f"{filename_prefix}_temp.html")
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        temp_html_uri = pathlib.Path(temp_html_path).resolve().as_uri()

        def run_edge_print(output_pdf):
            if os.path.exists(output_pdf):
                os.remove(output_pdf)
            with tempfile.TemporaryDirectory(prefix="edge_pdf_profile_") as edge_profile_dir:
                cmd = [
                    edge_path,
                    "--headless",
                    "--disable-gpu",
                    f"--user-data-dir={edge_profile_dir}",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={output_pdf}",
                    temp_html_uri
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # msedge.exe's headless print-to-pdf writes the PDF asynchronously and can
                # exit before the file is fully flushed to disk. Wait for it to appear and
                # its size to stabilize before returning, otherwise the caller may delete
                # the source HTML (temp_html_path) while the still-running render is trying
                # to read it, baking an ERR_FILE_NOT_FOUND page into the PDF instead.
                deadline = time.time() + 20
                last_size = -1
                stable_checks = 0
                while time.time() < deadline:
                    if os.path.exists(output_pdf):
                        size = os.path.getsize(output_pdf)
                        if size > 0 and size == last_size:
                            stable_checks += 1
                            if stable_checks >= 2:
                                break
                        else:
                            stable_checks = 0
                        last_size = size
                    time.sleep(0.5)

        # Test if the file is writable
        is_locked = False
        if os.path.exists(dest_filepath_pdf):
            try:
                with open(dest_filepath_pdf, "r+b") as f:
                    pass
            except PermissionError:
                is_locked = True

        if not is_locked:
            try:
                run_edge_print(dest_filepath_pdf)
                print(f"Generated Weekly Focus PDF at: {dest_filepath_pdf}")
            except Exception as e:
                print(f"Failed to generate PDF: {e}")
        else:
            timestamp = int(time.time())
            fallback_pdf = os.path.join(dest_dir, f"{target_date}_Weekly_Focus_{timestamp}.pdf")
            print(f"Warning: {dest_filepath_pdf} is locked by another program (e.g., PDF Reader).")
            print(f"Attempting to write to fallback path: {fallback_pdf}")
            try:
                run_edge_print(fallback_pdf)
                print(f"Generated Weekly Focus PDF at: {fallback_pdf}")
            except Exception as e:
                print(f"Failed to generate fallback PDF: {e}")

        # Clean up temp HTML
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
            
    except Exception as e:
        print(f"Failed to generate PDF: {e}")
        
    return dest_filepath

if __name__ == "__main__":
    t_date = sys.argv[1] if len(sys.argv) > 1 else None
    generate_weekly_report(t_date)
