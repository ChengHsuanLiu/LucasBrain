import os
import re

stocks_dir = r"c:\Users\User\Desktop\LucasBrain\10_Stocks"

# 1. Load all stock names and tickers to build link mapping
stock_files = [f for f in os.listdir(stocks_dir) if f.endswith('.md')]
stock_map = {} # name -> full link name, e.g. "聯電" -> "2303聯電"

for f in stock_files:
    base = os.path.splitext(f)[0] # e.g. "2303聯電"
    match = re.match(r'^(\d+)(.+)$', base)
    if match:
        ticker = match.group(1)
        name = match.group(2)
        stock_map[base] = base
        stock_map[name] = base
        # Also map ticker+name and name combinations if needed
        # We avoid mapping pure numbers like "2303" alone because it could match year/dates,
        # but we can map "2303聯電" or "聯電".

# Sort names by length descending to match longest first
sorted_names = sorted(stock_map.keys(), key=len, reverse=True)

def add_wikilinks(text):
    # We want to replace occurrences of stock names with [[fullName]]
    # But we must avoid double-linking already linked items, e.g. [[2303聯電]] or [[聯電]]
    # Let's tokenize by existing links or just do a regex replace that ignores existing links.
    # A safe way: split by [[...]] and code blocks, only replace in plain text parts.
    
    # We split by wiki links and markdown links first
    parts = re.split(r'(\[\[[^\]]+\]\]|`[^`]+`|\[[^\]]+\]\([^\)]+\))', text)
    for i in range(len(parts)):
        # If it is not a link/code block, we do replacements
        if not parts[i].startswith('[[') and not parts[i].startswith('`') and not (parts[i].startswith('[') and '](' in parts[i]):
            # Replace each stock name with [[link]]
            for name in sorted_names:
                if len(name) < 2: # Skip very short names
                    continue
                # Match name but ensure it's not already part of a word or link
                # Since Chinese doesn't have word boundaries, we match the string directly,
                # but we must make sure we don't match inside another link (handled by splitting).
                target = stock_map[name]
                # Replace name with [[target]]
                # We use a pattern to avoid matching if it's already inside double brackets
                # (though split handles most, let's be careful).
                parts[i] = parts[i].replace(name, f"[[{target}]]")
                
    # Reassemble and clean up nested links like [[[[2303聯電]]]] if any
    result = "".join(parts)
    # Simplify nested brackets if they occurred
    while "[[[[" in result:
        result = result.replace("[[[[", "[[")
    while "]]]]" in result:
        result = result.replace("]]]]", "]]")
    # Clean up double brackets of the same target, e.g. [[[[2303聯電]]]] -> [[2303聯電]]
    # Regex cleanup: [[\[\[([^\]]+)\]\]]] -> [[$1]]
    result = re.sub(r'\[\[\s*\[\[([^\]]+)\]\]\s*\]\]', r'[[\1]]', result)
    return result

# 2. Process all stock files
for filename in stock_files:
    filepath = os.path.join(stocks_dir, filename)
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
        
    original_content = content
    
    # 2a. Fix the dangling (Notes & Memos) or (History Notes)
    # Match the header and remove the dangling lines
    # Pattern: ## 📝 歷史筆記與會議紀要 followed by any text, and then a line containing just (Notes & Memos) or (History Notes)
    # Let's replace the header line itself to have the standard (Notes & Memos)
    
    # If the header doesn't have (Notes & Memos), we standardize it
    if "## 📝 歷史筆記與會議紀要" in content and "## 📝 歷史筆記與會議紀要 (Notes & Memos)" not in content:
        content = content.replace("## 📝 歷史筆記與會議紀要", "## 📝 歷史筆記與會議紀要 (Notes & Memos)")
        
    # Remove dangling (Notes & Memos) or (History Notes) or (Notes & Memos) lines
    lines = content.split('\n')
    new_lines = []
    skip_next_if_blank = False
    for line in lines:
        stripped = line.strip()
        if stripped in ["(Notes & Memos)", "(History Notes)", "(Notes & Memos) (History Notes)", "(History Notes) (Notes & Memos)"]:
            print(f"Removing dangling header leftover in {filename}: '{stripped}'")
            continue
        new_lines.append(line)
        
    content = '\n'.join(new_lines)
    
    # 2b. Add Wikilinks to the ## 📝 歷史筆記與會議紀要 section
    # Let's find the history section and only apply Wikilinks there to avoid modifying other parts unnecessarily
    header = "## 📝 歷史筆記與會議紀要 (Notes & Memos)"
    if header in content:
        parts = content.split(header)
        # The history section is parts[1] up to the next "---" or next header "##"
        # Let's split parts[1] by the next main section
        subparts = re.split(r'(\n---|\n## )', parts[1], maxsplit=1)
        
        # Apply wikilinks to the history section body (subparts[0])
        linked_history = add_wikilinks(subparts[0])
        
        # Reconstruct parts[1]
        parts[1] = linked_history + "".join(subparts[1:])
        content = header.join(parts)
        
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated and cleaned {filename}")

print("Clean and link process completed.")
