import os
import re
import shutil
import datetime

inbox_dir = r"c:\Users\User\Desktop\LucasBrain\00_Inbox"
stocks_dir = r"c:\Users\User\Desktop\LucasBrain\10_Stocks"
garden_dir = r"c:\Users\User\Desktop\LucasBrain\20_Garden"
archives_dir = r"c:\Users\User\Desktop\LucasBrain\98_Archives"
index_path = r"c:\Users\User\Desktop\LucasBrain\index.md"
log_path = r"c:\Users\User\Desktop\LucasBrain\log.md"

# 1. Build WikiLink Linker
def build_wiki_linker(stocks_dir):
    stock_map = {}
    for f in os.listdir(stocks_dir):
        if f.endswith('.md'):
            base = os.path.splitext(f)[0] # e.g. "2303聯電"
            match = re.match(r'^(\d+)(.+)$', base)
            if match:
                ticker = match.group(1)
                name = match.group(2)
                stock_map[base] = base
                stock_map[name] = base
                
    # Sort keys by length descending to match longest first
    sorted_keys = sorted(stock_map.keys(), key=len, reverse=True)
    
    # Escape keys for regex
    escaped_keys = [re.escape(k) for k in sorted_keys if len(k) >= 2]
    
    # Combined regex pattern: match existing wiki links, markdown links, code blocks, or stock names
    pattern = re.compile(r'(\[\[[^\]]+\]\]|`[^`]+`|\[[^\]]+\]\([^\)]+\))|(' + '|'.join(escaped_keys) + ')')
    
    def replacer(match):
        if match.group(1):
            return match.group(1) # Return existing link unchanged
        name = match.group(2)
        target = stock_map[name]
        return f"[[{target}]]"
        
    def link_text(text):
        return pattern.sub(replacer, text)
        
    return link_text

# 2. Append helper
def append_history_note(ticker, note_text, link_func):
    # Find matching stock file
    stock_file = None
    for f in os.listdir(stocks_dir):
        if f.startswith(ticker) and f.endswith(".md"):
            stock_file = os.path.join(stocks_dir, f)
            break
            
    if not stock_file:
        print(f"Stock file for ticker {ticker} not found.")
        return False
        
    try:
        with open(stock_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # Standardize the history header if present
        match_header = re.search(r'## 📝 歷史筆記與會議紀要[^\n]*', content)
        if match_header:
            content = content.replace(match_header.group(0), "## 📝 歷史筆記與會議紀要 (Notes & Memos)")
            
        header = "## 📝 歷史筆記與會議紀要 (Notes & Memos)"
        
        # Apply WikiLinks to the note text before appending
        note_linked = link_func(note_text)
        
        if header in content:
            parts = content.split(header)
            body = parts[1].lstrip()
            # Clean up any leftover dangling header texts on the first lines of body
            body_lines = body.split('\n')
            clean_body_lines = []
            for line in body_lines:
                stripped = line.strip()
                if stripped in ["(Notes & Memos)", "(History Notes)", "(Notes & Memos) (History Notes)", "(History Notes) (Notes & Memos)"]:
                    continue
                clean_body_lines.append(line)
            clean_body = '\n'.join(clean_body_lines)
            
            new_content = parts[0] + header + "\n" + note_linked + "\n" + clean_body.lstrip()
        else:
            # Append to the end of the file
            new_content = content.rstrip() + "\n\n" + header + "\n" + note_linked + "\n"
            
        with open(stock_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Successfully appended note to {os.path.basename(stock_file)}")
        return True
    except Exception as e:
        print(f"Failed to append to stock file for {ticker}: {e}")
        return False

# 3. Move functions
def move_file(filename, category):
    src = os.path.join(inbox_dir, filename)
    dest_dir = os.path.join(archives_dir, category)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, filename)
    if os.path.exists(src):
        if os.path.exists(dest):
            os.remove(dest)
        shutil.move(src, dest)
        print(f"Moved {filename} to 98_Archives/{category}/")
    else:
        print(f"Source file {src} not found.")

def main():
    link_func = build_wiki_linker(stocks_dir)
    affected_stocks = set()
    
    # 1. Parse 20260704_232844_text.md
    note_path = os.path.join(inbox_dir, "20260704_232844_text.md")
    if os.path.exists(note_path):
        with open(note_path, 'r', encoding='utf-8', errors='replace') as f:
            full_text = f.read()
            
        # Match sections starting with 🔺
        matches = re.finditer(r'🔺\s*(\d{4})\s*([^:\n：]+)[:：]?(.*?)(?=🔺|___|^\s*[A-I]\s*$|\Z)', full_text, re.DOTALL | re.MULTILINE)
        
        # Accumulate notes by ticker
        ticker_notes = {}
        for m in matches:
            ticker = m.group(1).strip()
            name = m.group(2).strip().replace("*", "")
            raw_body = m.group(3).strip()
            
            # Format the body lines with correct indentation
            body_lines = []
            for line in raw_body.split('\n'):
                line_stripped = line.strip()
                if line_stripped:
                    # Indent
                    body_lines.append(f"    - {line_stripped}")
            
            body_formatted = "\n".join(body_lines)
            
            if ticker not in ticker_notes:
                ticker_notes[ticker] = []
            
            ticker_notes[ticker].append(body_formatted)
            
        # Append to individual stock pages
        for ticker, note_bodies in ticker_notes.items():
            combined_bodies = "\n".join(note_bodies)
            note_formatted = f"* [2026-07-04] 投資討論晨會紀錄 (來源: [[20260704_232844_text.md]]):\n{combined_bodies}"
            if append_history_note(ticker, note_formatted, link_func):
                # Find matching stock file name
                for f in os.listdir(stocks_dir):
                    if f.startswith(ticker) and f.endswith(".md"):
                        affected_stocks.add(os.path.splitext(f)[0])
                        break
            
    # 2. Append reference for 20260705_182425_text.md to 6696仁新醫藥
    ref_note = "* [2026-07-05] 報告摘要：[[20260705_182425_text.md]] - 仁新醫藥：被市場低估的全球新藥商業化轉折股（深入探討 LBS-008 斯特格病藥證商業化、小分子藥物高淨利率優勢、PRV 一次性收益與 LBS-007 血癌平台想像）"
    if append_history_note("6696", ref_note, link_func):
        affected_stocks.add("6696仁新醫藥")
    
    # 3. Add link reference in 2327國巨.md for 20260705_183705_file.pdf
    yageo_note = "* [2026-07-05] 法人報告：[[20260705_183705_file.pdf]] - 高盛證券重申買進（BUY）評等，目標價大升至 1,490 元，預期 MLCC 全面漲價帶動 2027-2028 EPS 創下歷史新高（37.56 / 57.32 元）"
    if append_history_note("2327", yageo_note, link_func):
        affected_stocks.add("2327國巨")

    # 4. Move raw files to 98_Archives
    move_file("20260704_232844_text.md", "Fund_Company_Memo")
    move_file("20260705_182425_text.md", "Stock_Memo")
    move_file("20260705_183705_file.pdf", "Research_Report")
    
    # 5. Update index.md Statistics
    if os.path.exists(index_path):
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_content = f.read()
                
            stock_count = len([f for f in os.listdir(stocks_dir) if f.endswith('.md')])
            garden_count = len([f for f in os.listdir(garden_dir) if f.endswith('.md')])
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            
            # Find and replace statistics
            index_content = re.sub(r'\*\s*\*\*個股筆記數量\*\*\s*：\s*\d+\s*檔', f'* **個股筆記數量**：{stock_count} 檔', index_content)
            index_content = re.sub(r'\*\s*\*\*產業筆記數量\*\*\s*：\s*\d+\s*個', f'* **產業筆記數量**：{garden_count} 個', index_content)
            index_content = re.sub(r'\*\s*\*\*最後更新時間\*\*\s*：\s*\d{4}-\d{2}-\d{2}', f'* **最後更新時間**：{today_str}', index_content)
            
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(index_content)
            print("Successfully updated index.md statistics.")
        except Exception as e:
            print(f"Failed to update index.md: {e}")
            
    # 6. Append history log to log.md
    if os.path.exists(log_path):
        try:
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            log_files = "20260704_232844_text.md, 20260705_182425_text.md, 20260705_183705_file.pdf"
            affected_links = "、".join([f"[[{s}]]" for s in sorted(affected_stocks)])
            
            log_entry = f"\n## [{today_str}] ingest | {log_files} | 影響 {affected_links}\n"
            log_entry += f"- 整理 00_Inbox 中的 3 個文件：導入晨會紀錄的個股討論要點，並新增仁新醫藥報告摘要與國巨高盛報告之連結參考。完成原始檔案歸檔與 WikiLinks 補齊。\n"
            
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            print("Successfully appended history log to log.md.")
        except Exception as e:
            print(f"Failed to update log.md: {e}")

if __name__ == "__main__":
    main()
