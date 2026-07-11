"""
為 97_Settings/概念股FPE合理區間.md 中「有成員資格但尚無 10_Stocks/ 頁面」的股票，
批次建立精簡版佔位頁面（詳盡研究內容待未來透過 00_Inbox ingest 疊加）。

用法：
    python create_placeholder_stocks.py
"""
import io
import os
import re
import sys
from datetime import datetime, timedelta

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
                ticker = m_ticker.group(1)
                name = member[len(ticker):].strip().rstrip('*').strip()
                members.append((ticker, name))
        if members:
            concepts.append({"concept": concept_key, "members": members})
    return concepts


def readable_industry_label(concept_key):
    """把 Garden 頁面檔名轉成適合放進 industry frontmatter 的可讀字串，
    去除 N_Tier名稱_ 前綴，其餘底線轉成 /。"""
    stripped = re.sub(r'^\d_[^_]+_', '', concept_key)
    return stripped.replace('_', '/')


def build_placeholder_content(ticker, name, concept_key, today):
    industry_label = readable_industry_label(concept_key)
    review_by = (datetime.strptime(today, "%Y-%m-%d") + timedelta(days=90)).strftime("%Y-%m-%d")
    return f"""---
type: stock
ticker: "{ticker}"
name: "{name}"
industry: "{industry_label}"
created: {today}
updated: {today}
review_by: {review_by}
tags: [investment/watchlist]
aliases: [{name}]
current_price: 0.0
forward_pe: "待補充"
valuation_rating: "HOLD"
tactical_score: "MA: 0 / Bias: 0"
tactical_action: "尚無數據"
---
# {name} ({ticker})

> [!NOTE]
> 佔位頁面：尚未透過 00_Inbox 收集此股票的研究素材，目前僅依 `[[{concept_key}]]` 的產業分類納入追蹤（每日價格/技術面、動能分數、財務指標篩選）。投資論點、EPS 預估、供應鏈細節待補充；未來若收到相關研究素材，將以 ingest 流程疊加進本頁面。

## 🎯 投資建議與核心結論 (Summary)
* **核心論點**：[待補充]

---

## 🔗 相關概念與產業連結 (Related Concepts)
* **關聯產業 (Garden)**：`[[{concept_key}]]`

---

## 📄 原始文件與連結 (Original Documents)
* (尚無)
"""


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    concepts = parse_concepts_with_names()
    tracked = get_tracked_tickers()
    today = datetime.now().strftime("%Y-%m-%d")

    ticker_to_concept_name = {}
    for c in concepts:
        for ticker, name in c["members"]:
            if ticker not in tracked and ticker not in ticker_to_concept_name:
                ticker_to_concept_name[ticker] = (c["concept"], name)

    created = []
    for ticker, (concept_key, name) in sorted(ticker_to_concept_name.items()):
        filename = f"{ticker}{name}.md"
        filepath = os.path.join(STOCK_DIR, filename)
        if os.path.exists(filepath):
            continue
        content = build_placeholder_content(ticker, name, concept_key, today)
        with io.open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        created.append(filename)

    print(f"已建立 {len(created)} 個佔位頁面：")
    for f in created:
        print(f"  {f}")


if __name__ == "__main__":
    main()
