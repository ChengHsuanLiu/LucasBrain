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
        except Exception as e:
            print(f"Error scanning {filename}: {e}")

scan_notes(stocks_dir)
scan_notes(garden_dir)

# Read all files from root of archives (in case any exist) + all files in subfolders to re-evaluate
# Let's perform a complete clean re-classification of all files in all folders
all_files = []
for root, dirs, files_in_dir in os.walk(archives_dir):
    for filename in files_in_dir:
        filepath = os.path.join(root, filename)
        # Avoid directories themselves
        if os.path.isfile(filepath):
            all_files.append((filepath, filename))

moved_count = {cat: 0 for cat in categories}

for src_filepath, filename in all_files:
    # If the file is inside the .git directory or similar, skip it
    if ".git" in src_filepath:
        continue
        
    base_name = os.path.splitext(filename)[0]
    
    # Check if we have descriptive metadata for this file or its base name
    desc = metadata_map.get(filename, metadata_map.get(base_name, ""))
    
    # Read first 2000 characters if it's text, to supplement classification
    content = ""
    is_text = filename.endswith('.md') or filename.endswith('.txt')
    if is_text:
        try:
            with open(src_filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(2000)
        except:
            pass
            
    category = "Others" # Default fallback
    
    # 1. Expert Meetings
    if "專家會議" in desc or "專家" in desc or "專家會議" in filename or "專家會議" in content or "專家訪談" in content:
        category = "Expert_Meetings"
    # 2. Stock Memo
    elif any(kw in desc for kw in ["股東會", "法說會", "私訪", "股東常會", "對話紀錄", "Call Memo", "備忘錄", "會議紀要", "議事手冊", "合併財務報告", "財務報告", "memo"]) or \
         any(kw in filename for kw in ["股東會", "法說會", "私訪", "股東常會", "對話紀錄", "Call Memo", "備忘錄", "memo"]) or \
         any(kw in content for kw in ["股東會", "法說會", "私訪", "股東常會", "會後Q&A", "訪談紀錄", "Call Memo", "memo"]):
        category = "Stock_Memo"
    # 3. Research Reports
    elif any(kw in desc for kw in ["研究報告", "投顧", "大摩", "大華", "凱基", "元大", "統一", "國泰", "研報", "評等", "目標價", "報告"]) or \
         any(kw in filename for kw in ["研究報告", "投顧", "大摩", "大華", "凱基", "元大", "統一", "國泰", "報告"]) or \
         any(kw in content for kw in ["研究報告", "投顧", "目標價", "評等", "買進", "KGI", "Morgan Stanley", "大摩", "目標價"]):
        category = "Research_Report"
    # 4. Fund Company Memo: Contains "會議紀錄" and has multiple speakers / discussions
    elif "會議紀錄" in desc or "會議紀錄" in filename or "會議紀錄" in content:
        # Check if it has hallmarks of multiple speakers/stocks (晨會/討論內容)
        if any(kw in content for kw in ["講者", "投資公司", "晨會", "晨報"]):
            category = "Fund_Company_Memo"
            
    # Move if not already in the correct folder
    dest_dir = categories[category]
    dest_filepath = os.path.join(dest_dir, filename)
    
    if os.path.abspath(src_filepath) != os.path.abspath(dest_filepath):
        try:
            # Check if destination file already exists, if so remove it first to avoid collision
            if os.path.exists(dest_filepath):
                os.remove(dest_filepath)
            shutil.move(src_filepath, dest_filepath)
            moved_count[category] += 1
        except Exception as e:
            print(f"Failed to move {filename} from {src_filepath} to {dest_filepath}: {e}")
    else:
        moved_count[category] += 1

print("\nRe-classification completed:")
for cat, count in moved_count.items():
    print(f"  - {cat}: {count} files")
