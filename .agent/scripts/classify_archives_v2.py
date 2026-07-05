import os
import re
import shutil

# First, restore files moved in v1 so we can start clean
archives_dir = r"c:\Users\User\Desktop\LucasBrain\99_Templates" # Wait, archives is in 98_Archives
archives_dir = r"c:\Users\User\Desktop\LucasBrain\98_Archives"

categories = {
    "Expert_Meetings": os.path.join(archives_dir, "Expert_Meetings"),
    "Research_Report": os.path.join(archives_dir, "Research_Report"),
    "Stock_Meeting_Memo": os.path.join(archives_dir, "Stock_Meeting_Memo"),
    "Fund_Company_Memo": os.path.join(archives_dir, "Fund_Company_Memo")
}

# Restore files from subfolders to root for a fresh classification
for cat, path in categories.items():
    if os.path.exists(path):
        for f in os.listdir(path):
            src = os.path.join(path, f)
            dest = os.path.join(archives_dir, f)
            if os.path.isfile(src):
                try:
                    shutil.move(src, dest)
                except Exception as e:
                    pass

# Now compile metadata from 10_Stocks and 20_Garden
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
            # Match patterns like: * `[[20260625_190433_text.md]]` - description
            # or * [[20260625_190433_text.md]] - description
            # or * `[[20260625_190433_text.md]]` ： description
            matches = re.findall(r'[\-\*]\s*`?\[\[([^\]]+)\]\]`?\s*[\-：\s]+([^\n]+)', content)
            for file_ref, desc in matches:
                file_ref = file_ref.strip()
                desc = desc.strip()
                metadata_map[file_ref] = desc
                # Also maps base filename without extension
                base_ref = os.path.splitext(file_ref)[0]
                metadata_map[base_ref] = desc
        except Exception as e:
            print(f"Error scanning {filename}: {e}")

scan_notes(stocks_dir)
scan_notes(garden_dir)

print(f"Compiled metadata map for {len(metadata_map)} document references.")

# Now scan all files currently in 98_Archives root
files = [f for f in os.listdir(archives_dir) if os.path.isfile(os.path.join(archives_dir, f))]

moved_count = {cat: 0 for cat in categories}
unclassified = []

for filename in files:
    filepath = os.path.join(archives_dir, filename)
    base_name = os.path.splitext(filename)[0]
    
    # Check if we have descriptive metadata for this file or its base name
    desc = metadata_map.get(filename, metadata_map.get(base_name, ""))
    
    # Read first 1000 characters if it's text, to supplement classification
    content = ""
    is_text = filename.endswith('.md') or filename.endswith('.txt')
    if is_text:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(2000)
        except:
            pass
            
    category = None
    
    # Classification rules based on description & content
    # 1. Expert Meetings
    if "專家會議" in desc or "專家" in desc or "專家會議" in filename or "專家會議" in content or "專家訪談" in content:
        category = "Expert_Meetings"
    # 2. Stock Meeting Memo
    elif any(kw in desc for kw in ["股東會", "法說會", "私訪", "股東常會", "對話紀錄", "Call Memo", "備忘錄", "會議紀要", "議事手冊", "合併財務報告", "財務報告"]) or \
         any(kw in filename for kw in ["股東會", "法說會", "私訪", "股東常會", "對話紀錄", "Call Memo", "備忘錄"]) or \
         any(kw in content for kw in ["股東會", "法說會", "私訪", "股東常會", "會後Q&A", "訪談紀錄", "Call Memo"]):
        category = "Stock_Meeting_Memo"
    # 3. Research Reports
    elif any(kw in desc for kw in ["研究報告", "投顧", "大摩", "大華", "凱基", "元大", "統一", "國泰", "研報", "評等", "目標價", "報告"]) or \
         any(kw in filename for kw in ["研究報告", "投顧", "大摩", "大華", "凱基", "元大", "統一", "國泰", "報告"]) or \
         any(kw in content for kw in ["研究報告", "投顧", "目標價", "評等", "買進", "KGI", "Morgan Stanley", "大摩", "目標價"]):
        category = "Research_Report"
    # 4. Fund Company Memo
    elif "投資公司" in desc or "講者" in desc or "投資公司" in content or "晨會" in content or "晨報" in content:
        category = "Fund_Company_Memo"
    # 5. Generic filename fallback
    else:
        lower_name = filename.lower()
        if "report" in lower_name or "update" in lower_name or "ccl" in lower_name:
            category = "Research_Report"
        elif "memo" in lower_name or "qa" in lower_name:
            category = "Stock_Meeting_Memo"
            
    if category:
        dest_path = os.path.join(categories[category], filename)
        try:
            shutil.move(filepath, dest_path)
            moved_count[category] += 1
        except Exception as e:
            print(f"Failed to move {filename}: {e}")
            unclassified.append(filename)
    else:
        unclassified.append(filename)

print("\nClassification results:")
for cat, count in moved_count.items():
    print(f"  - {cat}: {count} files moved")
print(f"  - Unclassified: {len(unclassified)} files remaining in root")
if unclassified:
    print(f"Unclassified files (top 20): {unclassified[:20]}")
