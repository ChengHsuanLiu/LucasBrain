"""
找出 97_Settings/概念股FPE合理區間.md 成員清單中，尚未在 10_Stocks/ 建立個股筆記的代號。

用法：
    python find_missing_stock_pages.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.stock_signals import FPE_TABLE_PATH

STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"


def get_tracked_tickers():
    tracked = set()
    for filename in os.listdir(STOCK_DIR):
        if not filename.endswith('.md'):
            continue
        m = re.match(r'^([0-9]+(?:\.[a-zA-Z0-9]+)?)', filename)
        if m:
            tracked.add(m.group(1))
    return tracked


def parse_concepts_with_names(filepath=FPE_TABLE_PATH):
    """比照 load_concept_fpe_table() 的解析邏輯，但保留成員的完整字串 (代號+名稱)
    而非只留代號，方便產生人類可讀的報告。回傳 [{concept, members: [(ticker, full_str), ...]}]。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')

    concepts = []
    in_main_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('## 概念股分類與現有成員'):
            in_main_table = True
            continue
        if in_main_table and stripped.startswith('## '):
            break
        if not in_main_table or not stripped.startswith('|'):
            continue

        cols = [c.strip() for c in stripped.split('|')[1:-1]]
        if len(cols) < 6 or cols[0].startswith(':') or cols[1].startswith('概念股分類'):
            continue

        m_concept = re.search(r'\[\[([^\]|]+)', cols[1])
        concept_key = m_concept.group(1) if m_concept else cols[1]

        members = []
        for member in cols[5].split('、'):
            member = member.strip()
            m_ticker = re.match(r'^([0-9]+(?:\.[a-zA-Z]+)?)', member)
            if m_ticker:
                members.append((m_ticker.group(1), member))
        if members:
            concepts.append({"concept": concept_key, "members": members})
    return concepts


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    concepts = parse_concepts_with_names()
    tracked = get_tracked_tickers()

    missing = {}  # ticker -> {"name_str": full member string, "concepts": set()}
    for c in concepts:
        for ticker, full_str in c["members"]:
            if ticker not in tracked:
                entry = missing.setdefault(ticker, {"name_str": full_str, "concepts": set()})
                entry["concepts"].add(c["concept"])

    if not missing:
        print("所有 FPE 表成員都已有對應的 10_Stocks/ 頁面。")
        return

    print(f"共 {len(missing)} 檔股票在 FPE 表有成員資格，但 10_Stocks/ 尚無對應頁面：\n")
    for ticker in sorted(missing.keys()):
        entry = missing[ticker]
        concept_list = "、".join(sorted(entry["concepts"]))
        print(f"  {entry['name_str']}  ->  {concept_list}")


if __name__ == "__main__":
    main()
