import os
import re
import shutil

archives_dir = r"c:\Users\User\Desktop\LucasBrain\98_Archives"

categories = {
    "Expert_Meetings": os.path.join(archives_dir, "Expert_Meetings"),
    "Research_Report": os.path.join(archives_dir, "Research_Report"),
    "Stock_Memo": os.path.join(archives_dir, "Stock_Memo"),
    "Fund_Company_Memo": os.path.join(archives_dir, "Fund_Company_Memo"),
    "Others": os.path.join(archives_dir, "Others")
}

# Create folders
for path in categories.values():
    os.makedirs(path, exist_ok=True)

# Compile metadata from 10_Stocks and 20_Garden
metadata_map = {}
ref_occurrences = {}
stocks_dir = r"c:\Users\User\Desktop\LucasBrain\10_Stocks"
garden_dir = r"c:\Users\User\Desktop\LucasBrain\20_Garden"

def scan_notes(folder):
    if not os.path.exists(folder):
        return
    for filename in os.listdir(folder):
        if not filename.endswith('.md'):
            continue
        path = os.path.join(folder, filename)
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            matches = re.findall(r'[\-\*]\s*`?\[\[([^\]]+)\]\]`?\s*[\-：\s]+([^\n]+)', content)
            for file_ref, desc in matches:
                file_ref = file_ref.strip()
                desc = desc.strip()
                metadata_map[file_ref] = desc
                base_ref = os.path.splitext(file_ref)[0]
                metadata_map[base_ref] = desc
                
                # Track note occurrences
                note_name = os.path.basename(path)
                if file_ref not in ref_occurrences:
                    ref_occurrences[file_ref] = set()
                ref_occurrences[file_ref].add(note_name)
                
                if base_ref not in ref_occurrences:
                    ref_occurrences[base_ref] = set()
                ref_occurrences[base_ref].add(note_name)
        except Exception as e:
            print(f"Error scanning {filename}: {e}")

scan_notes(stocks_dir)
scan_notes(garden_dir)

print(f"Compiled metadata map for {len(metadata_map)} references.")

def extract_pdf_text(filepath):
    try:
        import pypdf
        reader = pypdf.PdfReader(filepath)
        text = ""
        for page in reader.pages[:2]:
            t = page.extract_text()
            if t:
                text += t
            if len(text) >= 2000:
                break
        return text[:2000]
    except Exception as e:
        return ""

def extract_docx_text(filepath):
    try:
        import docx
        doc = docx.Document(filepath)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
            if len("".join(text)) >= 2000:
                break
        return "\n".join(text)[:2000]
    except Exception as e:
        return ""

# Scan all files under archives recursively
all_files = []
for root, dirs, files_in_dir in os.walk(archives_dir):
    for filename in files_in_dir:
        filepath = os.path.join(root, filename)
        if os.path.isfile(filepath):
            all_files.append((filepath, filename))

moved_count = {cat: 0 for cat in categories}

for src_filepath, filename in all_files:
    if ".git" in src_filepath:
        continue
        
    base_name = os.path.splitext(filename)[0]
    desc = metadata_map.get(filename, metadata_map.get(base_name, ""))
    
    # Read text from file
    content = ""
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.md', '.txt']:
        try:
            with open(src_filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(2000)
        except:
            pass
    elif ext == '.pdf':
        content = extract_pdf_text(src_filepath)
    elif ext in ['.docx', '.doc']:
        content = extract_docx_text(src_filepath)
        
    desc_lower = desc.lower()
    filename_lower = filename.lower()
    content_lower = content.lower()
    
    # Check reference counts to detect multi-stock files
    ref_list = ref_occurrences.get(filename, ref_occurrences.get(base_name, set()))
    is_multi_stock = len(ref_list) >= 3
    
    # Helper checking function that ignores "memory" / "memories" when matching "memo"
    def has_memo(text):
        return bool(re.search(r'memo(?!ry)', text))
        
    category = "Others" # Default fallback
    
    # Match keywords (lowercase for case insensitivity)
    # 1. Expert Meetings
    if any(kw in desc_lower for kw in ["專家會議", "專家訪談", "專家"]) or \
       any(kw in filename_lower for kw in ["專家會議", "專家訪談", "專家"]) or \
       any(kw in content_lower for kw in ["專家會議", "專家訪談", "專家"]):
        category = "Expert_Meetings"
        
    # 2. Fund Company Memo: Title has "會議紀錄" / "會議記錄" / "討論紀錄" and has multi-stock links or multi-speaker keywords
    elif (re.search(r'會議記[錄|紀|綠]', desc_lower + filename_lower + content_lower) or \
          any(kw in desc_lower + filename_lower + content_lower for kw in ["晨報", "晨會"])) and \
         (is_multi_stock or any(kw in desc_lower + filename_lower + content_lower for kw in ["講者", "投資公司", "討論內容", "討論"])):
        category = "Fund_Company_Memo"
        
    # 3. Stock Memo: Single stock memo (meetings, Q&As, dialogs, calls, memos, shareholder meetings, tech forums, interviews)
    elif any(kw in desc_lower for kw in ["股東會", "法說會", "法說", "私訪", "股東常會", "對話紀錄", "對話", "備忘錄", "會議紀要", "會議記錄", "會議紀錄", "議事手冊", "財務報告", "訪談", "會議", "論壇", "q&a", "問答"]) or \
         any(kw in filename_lower for kw in ["股東會", "法說會", "法說", "私訪", "股東常會", "對話紀錄", "對話", "備忘錄", "訪談", "會議", "論壇", "q&a", "問答"]) or \
         any(kw in content_lower for kw in ["股東會", "法說會", "法說", "私訪", "股東常會", "會後q&a", "訪談紀錄", "會議", "論壇"]) or \
         has_memo(desc_lower) or has_memo(filename_lower) or has_memo(content_lower):
        category = "Stock_Memo"
        
    # 4. Research Reports: Formal analyst reports from brokers
    elif any(kw in desc_lower for kw in ["研究報告", "投顧", "大摩", "大華", "凱基", "元大", "統一", "國泰", "研報", "評等", "目標價", "報告", "ubs", "morgan stanley", "hsbc", "daikwa", "daiwa", "大和", "大和證券", "券商", "美林", "野村", "瑞銀", "麥格理", "高盛", "花旗", "滙豐", "micron", "晶圓", "ccl", "top pick", "overweight", "underweight", "outperform", "target", "estimates", "forecast", "equity", "research"]) or \
         any(kw in filename_lower for kw in ["研究報告", "投顧", "大摩", "大華", "凱基", "元大", "統一", "國泰", "報告", "ubs", "morgan stanley", "hsbc", "daikwa", "daiwa", "大和", "大和證券", "券商", "美林", "野村", "瑞銀", "麥格理", "高盛", "花旗", "滙豐", "micron", "ccl", "top pick", "research"]) or \
         any(kw in content_lower for kw in ["研究報告", "投顧", "目標價", "評等", "買進", "kgi", "morgan stanley", "大摩", "目標價", "ubs", "hsbc", "券商", "global research", "equity research", "top pick", "overweight", "target price", "estimates", "forecast"]):
        category = "Research_Report"
        
    dest_dir = categories[category]
    dest_filepath = os.path.join(dest_dir, filename)
    
    if os.path.abspath(src_filepath) != os.path.abspath(dest_filepath):
        try:
            if os.path.exists(dest_filepath):
                os.remove(dest_filepath)
            shutil.move(src_filepath, dest_filepath)
            moved_count[category] += 1
        except Exception as e:
            print(f"Failed to move {filename} from {src_filepath} to {dest_filepath}: {e}")
    else:
        moved_count[category] += 1

print("\nClassification results:")
for cat, count in moved_count.items():
    print(f"  - {cat}: {count} files")
