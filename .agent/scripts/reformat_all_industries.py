import os
import re
import sys

# Global map to store EPS data parsed from stock notes
# key: ticker or name -> {"2026": eps26, "2027": eps27}
stock_eps_map = {}

def get_section_by_keyword(sections, keyword):
    for key in sections:
        if keyword in key:
            return key, sections[key]
    return None, None

def parse_stock_file_for_eps(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f"Failed to read stock file {filepath}: {e}")
        return {"2026": "待補充", "2027": "待補充"}
        
    eps_dict = {"2026": [], "2027": []}
    
    # 1. Parse from Markdown table first
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('|'):
            cols = [c.strip() for c in line.split('|')]
            if len(cols) >= 5:
                year = cols[2].strip()
                eps_val = cols[3].strip()
                cond = cols[4].strip()
                date_str = cols[1].strip()
                if year in eps_dict:
                    eps_dict[year].append((date_str, eps_val, cond))
                    
    # 2. Backup: If no table rows found, search for bullet points e.g. - **2026 EPS 預估**：
    if not eps_dict["2026"] and not eps_dict["2027"]:
        bullets = re.findall(r'(\d{4})\s*(?:實際|預估)?\s*EPS\s*(?:預估)?\*\*：?\s*`?([\d\.\-\+~<>/\s]+)\s*元`?', content)
        for year, eps_val in bullets:
            if year in eps_dict:
                eps_dict[year].append(("", eps_val.strip(), "預估"))
                
    result = {}
    for year in ["2026", "2027"]:
        rows = eps_dict[year]
        if not rows:
            result[year] = "待補充"
            continue
            
        # Sort rows by date newest first
        rows.sort(key=lambda x: x[0] if re.match(r'^\d{4}-\d{2}-\d{2}$', x[0]) else "0000-00-00", reverse=True)
        latest_date = rows[0][0]
        
        # Get all estimates from this latest date
        latest_rows = [r for r in rows if r[0] == latest_date]
        
        # If multiple on latest date, filter by Base keywords first
        base_rows = [r for r in latest_rows if any(x in r[2] for x in ["Base", "基準", "中性", "實際"])]
        if base_rows:
            result[year] = base_rows[0][1]
        else:
            seen = []
            for r in latest_rows:
                v = r[1]
                if v not in seen:
                    seen.append(v)
            result[year] = " / ".join(seen)
            
    return result

def build_stock_eps_database():
    stock_dir = r"c:\Users\User\Desktop\LucasBrain\10_Stocks"
    if not os.path.exists(stock_dir):
        print(f"Error: Stocks directory not found at {stock_dir}")
        return
        
    print("Building stock EPS database...")
    for f in os.listdir(stock_dir):
        if f.endswith('.md'):
            # Extract ticker and name from filename
            # e.g., 3189景碩.md -> ticker 3189, name 景碩
            # 1711.TW永光.md -> ticker 1711.TW, name 永光
            m = re.match(r'^([a-zA-Z0-9\.]+)(.*?)\.md$', f)
            if m:
                ticker = m.group(1).strip()
                name = m.group(2).strip()
                filepath = os.path.join(stock_dir, f)
                eps = parse_stock_file_for_eps(filepath)
                
                # Store in database
                stock_eps_map[ticker] = eps
                stock_eps_map[name] = eps
                
    print(f"Database built successfully with {len(stock_eps_map)//2} stock profiles.")

def lookup_eps(link_text):
    link_text = link_text.strip()
    if link_text in stock_eps_map:
        return stock_eps_map[link_text]
        
    m = re.match(r'^([a-zA-Z0-9\.]+)?(.*)$', link_text)
    if m:
        ticker = m.group(1)
        name = m.group(2)
        if ticker and ticker in stock_eps_map:
            return stock_eps_map[ticker]
        if name and name.strip() in stock_eps_map:
            return stock_eps_map[name.strip()]
            
    return {"2026": "待補充", "2027": "待補充"}

def parse_supply_chain(sc_body):
    if not sc_body:
        return "", ""
        
    lines = sc_body.split('\n')
    current_pos = "待分類"
    rows = []
    details = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('|'):
            continue
            
        # Check if it's a bold header category line
        # Category line must NOT have a colon with a description and ends with line end
        m_cat = re.match(r'^[\-\*]\s+\*\*(.*?)\*\*(?:[:：])?\s*$', stripped)
        if m_cat:
            current_pos = m_cat.group(1).strip()
            details.append(line)
            continue
            
        # Check if it's a company bullet item
        m_comp = re.match(r'^\s*[\-\*]\s+(.*?)[\:：](.+)', stripped)
        if m_comp:
            comp_name = m_comp.group(1).strip()
            comp_detail = m_comp.group(2).strip()
            
            clean_name = comp_name.replace('**', '').replace('*', '').strip()
            
            # Skip if clean_name looks like a remark/detail sub-bullet
            if any(kw in clean_name for kw in ["預估 EPS", "備註", "展望", "毛利率", "實際 EPS"]):
                details.append(line)
                continue
                
            # Lookup EPS using link or name
            link_match = re.search(r'\[\[(.*?)\]\]', clean_name)
            eps_data = {"2026": "待補充", "2027": "待補充"}
            
            if link_match:
                link_text = link_match.group(1).strip()
                eps_data = lookup_eps(link_text)
            else:
                for k in stock_eps_map:
                    if k in clean_name:
                        eps_data = stock_eps_map[k]
                        break
                        
            short_desc = comp_detail
            if len(short_desc) > 35:
                short_desc = short_desc[:32] + "..."
                
            rows.append((current_pos, clean_name, short_desc, eps_data["2026"], eps_data["2027"]))
            details.append(line)
        else:
            details.append(line)
            
    table = ""
    if rows:
        table = "| 產業位置 | 推薦個股/廠商 | 主要角色與供應材料 (簡述) | 2026E EPS | 2027E EPS | 關鍵合作 / 競爭格局 |\n"
        table += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for pos, name, desc, eps26, eps27 in rows:
            eps26_str = f"{eps26} 元" if eps26 != "待補充" else "待補充"
            eps27_str = f"{eps27} 元" if eps27 != "待補充" else "待補充"
            table += f"| **{pos}** | {name} | {desc} | {eps26_str} | {eps27_str} | 詳見下方細節 |\n"
        table += "\n"
        
    details_str = "\n".join(details).strip()
    return table, details_str

def clean_section_body(body):
    if not body:
        return ""
    body = body.strip()
    if body.endswith('---'):
        body = body[:-3].strip()
    return body

def reformat_industry_file(filepath):
    filename = os.path.basename(filepath)
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f"Failed to read {filename}: {e}")
        return False, "read_error"
        
    # We parse the markdown by headers
    parts = re.split(r'^##\s+', content, flags=re.MULTILINE)
    header = parts[0]
    sections = {}
    for part in parts[1:]:
        lines = part.split('\n')
        title_line = lines[0].strip()
        body = '\n'.join(lines[1:])
        sections[title_line] = body
        
    is_new_format = "## 🎯 產業投資點評與核心結論" in content or "## 🧠 產業深層結構與底層物理" in content
    
    if is_new_format:
        # Parse using the new headings/English keywords
        sum_key, sum_body = get_section_by_keyword(sections, "Summary")
        fp_key, fp_body = get_section_by_keyword(sections, "First Principles")
        sc_key, sc_body = get_section_by_keyword(sections, "Supply Chain")
        app_key, app_body = get_section_by_keyword(sections, "Applications")
        t_key, t_body = get_section_by_keyword(sections, "Timeline")
        rel_key, rel_body = get_section_by_keyword(sections, "Related Concepts")
        orig_key, orig_body = get_section_by_keyword(sections, "Original Documents")
        
        sum_body = clean_section_body(sum_body)
        fp_body = clean_section_body(fp_body)
        sc_body = clean_section_body(sc_body)
        app_body = clean_section_body(app_body)
        t_body = clean_section_body(t_body)
        rel_body = clean_section_body(rel_body)
        orig_body = clean_section_body(orig_body)
        
        # Parse supply chain
        sc_table, sc_details = parse_supply_chain(sc_body)
        
        sc_section = "## 🗺️ 產業鏈地圖與廠商財務比對 (Supply Chain & Financials)\n"
        if sc_table:
            sc_section += sc_table
        if sc_details:
            if "### 📌 產業鏈廠商與供應鏈細節" not in sc_details:
                sc_section += "### 📌 產業鏈廠商與供應鏈細節 (Supply Chain Details)\n" + sc_details + "\n"
            else:
                sc_section += sc_details + "\n"
        else:
            sc_section += "* **[請填寫產業上下游廠商清單]**\n"
            
        summary_content = "## " + (sum_key or "🎯 產業投資點評與核心結論 (Summary & Insights)") + "\n" + (sum_body.strip() if sum_body else "") + "\n"
        fp_content = "## " + (fp_key or "🧠 產業深層結構與底層物理 (First Principles)") + "\n" + (fp_body.strip() if fp_body else "") + "\n"
        app_content = "## " + (app_key or "💼 終端應用與核心客戶 (Applications & Customers)") + "\n" + (app_body.strip() if app_body else "") + "\n"
        timeline_content = "## " + (t_key or "📅 產業趨勢與產品迭代時間軸 (Timeline)") + "\n" + (t_body.strip() if t_body else "") + "\n"
        rel_content = "## " + (rel_key or "🔗 相關概念與個股連結 (Related Concepts)") + "\n" + (rel_body.strip() if rel_body else "") + "\n"
        orig_content = "## " + (orig_key or "📄 原始文件與連結 (Original Documents)") + "\n" + (orig_body.strip() if orig_body else "") + "\n"
        
    else:
        # 1. Summary & Insights
        sum_key, sum_body = get_section_by_keyword(sections, "摘要")
        insights_key, insights_body = get_section_by_keyword(sections, "關鍵洞察")
        cf_key, cf_body = get_section_by_keyword(sections, "核心發現")
        
        summary_content = "## 🎯 產業投資點評與核心結論 (Summary & Insights)\n"
        summary_content += "* **產業 So What?（這為什麼重要）**：\n"
        summary_content += "  - [請填寫此產業的核心投資價值與爆發催化劑]\n"
        
        bullets = []
        for b in [sum_body, insights_body, cf_body]:
            if b:
                for line in b.split('\n'):
                    line = line.strip()
                    if line.startswith('- ') or line.startswith('* '):
                        bullets.append(line)
                    elif line:
                        bullets.append(f"- {line}")
                        
        if bullets:
            summary_content += "* **關鍵洞察**：\n"
            for bullet in bullets:
                summary_content += f"  {bullet}\n"
                
        # 2. First Principles
        sc_key, sc_body = get_section_by_keyword(sections, "第二層思考")
        fp_key, fp_body = get_section_by_keyword(sections, "第一性原理")
        
        fp_content = "## 🧠 產業深層結構與底層物理 (First Principles)\n"
        added_fp = False
        if sc_body and sc_body.strip():
            fp_content += "### 📌 第二層思考 (Second-Level Thinking)\n" + sc_body.strip() + "\n\n"
            added_fp = True
        if fp_body and fp_body.strip():
            fp_content += "### 📌 第一性原理分析 (First Principles Analysis)\n" + fp_body.strip() + "\n\n"
            added_fp = True
            
        if not added_fp:
            fp_content += "* **[請填寫物理限制、材料瓶頸或技術壁壘，例如：線寬線距極限、散熱係數瓶頸]**\n"
            
        # 3. Supply Chain Table & Details
        comp_key, comp_body = get_section_by_keyword(sections, "上中下游廠商")
        sc_table, sc_details = parse_supply_chain(comp_body)
        
        sc_section = "## 🗺️ 產業鏈地圖與廠商財務比對 (Supply Chain & Financials)\n"
        if sc_table:
            sc_section += sc_table
        if sc_details:
            sc_section += "### 📌 產業鏈廠商與供應鏈細節 (Supply Chain Details)\n" + sc_details + "\n"
        else:
            sc_section += "* **[請填寫產業上下游廠商清單]**\n"
            
        # 4. Applications & Customers
        app_key, app_body = get_section_by_keyword(sections, "主要用途以及客戶")
        app_content = "## 💼 終端應用與核心客戶 (Applications & Customers)\n"
        if app_body and app_body.strip():
            app_content += app_body.strip() + "\n"
        else:
            app_content += "* **[請填寫主要終端應用與客戶清單]**\n"
            
        # 5. Timeline
        t_key, t_body = get_section_by_keyword(sections, "未來趨勢與重要時間軸")
        timeline_content = "## 📅 產業趨勢與產品迭代時間軸 (Timeline)\n"
        if t_body and t_body.strip():
            timeline_content += t_body.strip() + "\n"
        else:
            timeline_content += "* **[請填寫近期趨勢與重要時間軸里程碑，按時間排序]**\n"
            
        # 6. Related Concepts
        rel_key, rel_body = get_section_by_keyword(sections, "相關概念")
        rel_content = "## 🔗 相關概念與個股連結 (Related Concepts)\n" + (rel_body.strip() if rel_body else "") + "\n"
        
        # 7. Original Documents
        orig_key, orig_body = get_section_by_keyword(sections, "原始文件")
        orig_content = "## 📄 原始文件與連結 (Original Documents)\n" + (orig_body.strip() if orig_body else "") + "\n"
        
    # Assemble
    new_content = header.strip() + "\n\n"
    new_content += summary_content.strip() + "\n\n---\n\n"
    new_content += fp_content.strip() + "\n\n---\n\n"
    new_content += sc_section.strip() + "\n\n---\n\n"
    new_content += app_content.strip() + "\n\n---\n\n"
    new_content += timeline_content.strip() + "\n\n---\n\n"
    new_content += rel_content.strip() + "\n\n---\n\n"
    new_content += orig_content.strip() + "\n"
    
    # Assert size drop check
    if len(new_content) < len(content) * 0.5:
        print(f"Assert Failed: Content size of {filename} dropped significantly from {len(content)} to {len(new_content)}")
        return False, "assert_size_drop"
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print(f"Successfully reformatted and updated EPS in {filename}")
    return True, "success"

if __name__ == "__main__":
    build_stock_eps_database()
    
    target_dir = r"c:\Users\User\Desktop\LucasBrain\20_Garden"
    files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith('.md')]
    
    success_cnt = 0
    skipped_cnt = 0
    fail_cnt = 0
    
    print(f"\nStarting cross-reference migration of {len(files)} files...")
    for fp in files:
        if os.path.basename(fp) == "CCL銅箔基板.md":
            skipped_cnt += 1
            print(f"Skipping CCL銅箔基板.md (already manually customized)")
            continue
            
        try:
            ok, status = reformat_industry_file(fp)
            if ok:
                success_cnt += 1
            else:
                fail_cnt += 1
                print(f"Failed to process {os.path.basename(fp)}: {status}")
        except Exception as e:
            fail_cnt += 1
            print(f"Exception while processing {os.path.basename(fp)}: {e}")
            
    print(f"\nMigration finished: {success_cnt} succeeded, {skipped_cnt} skipped, {fail_cnt} failed.")
    if fail_cnt > 0:
        sys.exit(1)
    sys.exit(0)
