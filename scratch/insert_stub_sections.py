import io
import os
import re

STUB_FILES = [
    "1_需求端_AI實驗室_模型.md", "1_需求端_軟體_平台.md", "1_需求端_雲端巨頭_新雲.md",
    "2_晶片層_EDA_矽智財.md", "2_晶片層_介面_利基IC.md", "2_晶片層_功率元件.md",
    "2_晶片層_感測_MCU.md", "2_晶片層_晶圓代工.md", "2_晶片層_記憶體HBM.md",
    "2_晶片層_電源管理_類比IC.md", "3_上游_先進封裝後段設備.md", "3_上游_前段製程設備.md",
    "3_上游_廠務設備工程.md", "3_上游_測試檢測設備.md", "4_系統層_互連晶片_Retimer.md",
    "4_系統層_光纖_線纜.md", "4_系統層_散熱機構.md", "4_系統層_網通_交換器.md",
    "4_系統層_連接器_機殼.md", "4_系統層_電源電力設備.md", "5_應用層_傳動_關節零組件.md",
    "5_應用層_機器人_自動化.md", "生技醫療.md", "高速傳輸.md",
]

GARDEN_DIR = r"C:\Users\User\Desktop\LucasBrain\20_Garden"

INSERT_BLOCK = """
## 📊 市場規模與循環定位 (Market Size & Cycle Positioning)
* **市場規模與成長率**：[待補充，尚無研究素材可供分析]
* **結構性成長 vs 循環性成長**：[待補充]
* **目前循環位置**：[待補充]

---

## 🏆 競爭格局與市占率 (Competitive Landscape & Market Share)
* [待補充，尚無研究素材可供分析]

---

## ⚠️ 風險與總體敏感度 (Risks & Macro Sensitivity)
* **政策/地緣政治風險**：[待補充，尚無研究素材可供分析]
* **替代技術/顛覆風險**：[待補充]
* **總經敏感度**：[待補充]
"""

updated = []
for filename in STUB_FILES:
    path = os.path.join(GARDEN_DIR, filename)
    with io.open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if "市場規模與循環定位" in content:
        continue  # already has it, skip

    # Insert right before "## 🔗 相關個股連結" (or "## 🔗 相關概念與個股連結")
    marker_pattern = re.compile(r'\n## 🔗 相關')
    m = marker_pattern.search(content)
    if not m:
        print(f"WARNING: no insertion marker found in {filename}, skipped")
        continue

    insert_pos = m.start()
    new_content = content[:insert_pos] + "\n---\n" + INSERT_BLOCK + "\n---\n" + content[insert_pos + 1:]
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    updated.append(filename)

print(f"Updated {len(updated)} files:")
for f in updated:
    print(f"  {f}")
