"""
催化劑日曆 (catalyst calendar) 產生器。

輸出至 `30_Projects/Invest_Timeline/`，取代舊版同名資料夾（原本是人工/AI 一次性彙整、
之後不再更新的靜態文件）。本腳本每次執行都即時重新掃描 `10_Stocks/*.md` 既有的時間軸
區塊，依日期精細度分桶（年度/半年度/季度/明確時間），並依 `97_Settings/催化劑日曆設定.md`
的顯示範圍與分桶顯示開關過濾。

用法：
    python generate_invest_timeline.py
"""
import io
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.catalyst_calendar import (
    scan_catalyst_calendar, bucket_entries, load_display_window,
    load_bucket_toggles, format_period_label,
)
from lib.report_pdf import render_markdown_to_pdf

OUTPUT_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Invest_Timeline"

BUCKET_LABELS = [
    ("year", "🗓️ 年度事件"),
    ("half", "🌗 半年度事件"),
    ("quarter", "📆 季度事件"),
    ("date", "📌 明確時間事件"),
]

# 表格欄寬與個股頁面 PDF 排版一致附加在共用樣式之後：日期欄加寬到能放下
# "2026-10~11月" 這種較長的字串不換行，事件欄相應收窄。
CATALYST_CALENDAR_EXTRA_CSS = """
        table { table-layout: fixed; font-size: 8pt; }
        th:nth-child(1), td:nth-child(1) { width: 13%; white-space: nowrap; } /* 日期 */
        th:nth-child(2), td:nth-child(2) { width: 8%; text-align: center; } /* 個股 */
        th:nth-child(3), td:nth-child(3) { width: 15%; } /* 分類 */
        th:nth-child(4), td:nth-child(4) { width: 64%; } /* 事件 */
        th { padding: 5px 6px; }
        td { padding: 5px 6px; }
"""


def _year_group(period):
    y = period.start.year
    return y, str(y)


def _half_group(period):
    s = period.start
    h = 1 if s.month <= 6 else 2
    return (s.year, h), f"{s.year}-H{h}"


def _quarter_group(period):
    s = period.start
    q = (s.month - 1) // 3 + 1
    return (s.year, q), f"{s.year}-Q{q}"


def _month_group(period):
    s = period.start
    return (s.year, s.month), f"{s.year}-{s.month}月"


# 每個分桶各自的分組鍵：年度桶每隔一年、半年度桶每隔半年、季度桶每季、明確時間桶
# 每個月份，插入一列橫幅列（見 build_table 的 grouper 用法）。
BUCKET_GROUPERS = {
    "year": _year_group,
    "half": _half_group,
    "quarter": _quarter_group,
    "date": _month_group,
}


def build_table(rows, dated=True, grouper=None):
    """grouper(period) -> (group_key, group_label)。當某列的 group_key 與上一列不同時，
    先插入一列只有第一欄有內容的橫幅列（**group_label**，其餘欄位留空），模擬「全橫幅」
    的分組標示——markdown 表格不支援真正的 colspan，這是最相容 Obsidian 與 PDF 兩邊
    渲染的近似做法。"""
    lines = ["| 日期 | 個股 | 分類 | 事件 |", "| :--- | :--- | :--- | :--- |"]
    last_key = object()  # sentinel，保證第一列一定觸發插入橫幅
    for e in rows:
        if grouper and dated:
            key, label = grouper(e["period"])
            if key != last_key:
                lines.append(f"| **{label}** |  |  |  |")
                last_key = key
        date_display = format_period_label(e["period"]) if dated else e["date_token"]
        desc = e["desc"].replace("|", "\\|")
        lines.append(f"| {date_display} | {e['source_link']} | {e['type']} | {desc} |")
    return lines


def build_note_block(window_start, window_end):
    lines = ["> [!NOTE]"]
    lines.append(f"> 本報告由 `generate_invest_timeline.py` 自動掃描 `10_Stocks/*.md` 的「📅 重大事件與時間軸"
                 f" > 預估時間軸」區塊即時產生，不是一次性手動彙整的靜態文件。顯示範圍與分桶開關依"
                 f" `[[催化劑日曆設定]]` 目前設定為 **{window_start} ~ {window_end or '不設上限'}**，"
                 f"要調整範圍或關閉某個分桶直接改那份設定表即可。"
                 f"**目前只掃個股層級，不掃 `20_Garden/` 的產業層級時間軸**（部分 Garden 頁面的 Timeline 區塊"
                 f"寫成主題式技術分析而非逐項有日期的里程碑，雜訊比訊號多；之後如需重新納入產業層級事件，"
                 f"`scan_catalyst_calendar(include_garden=True)` 即可開啟）。"
                 f"事件依日期精細度分成四桶（年度/半年度/季度/明確時間），同桶內依開始日期由舊到新排序；"
                 f"時間範圍寫得過大（超過一年，例如「2027-2028」）視為無法乾淨歸類，直接不顯示。"
                 f"日期格式完全無法辨識的條目（例如沒有標註時間）歸入最下方「時間未定」，不受顯示範圍篩選。"
                 f"「分類」欄位是依關鍵字比對自動歸類（見 `lib/catalyst_calendar.py` 的 `classify_category()`），"
                 f"屬字面規則非語意判斷，邊界案例可能誤判：🧪藥證與臨床／💵籌碼與融資／💰價格變動／✅認證／"
                 f"🔀供應鏈重組／📝訂單／🏭產能與擴廠／📦出貨／⚙️技術與規格／📊財報與營收／🗂️其他"
                 f"（依此優先順序比對，命中第一個符合的類別即回傳）。")
    return lines


def build_title_block(today, total_dated, undated_count):
    lines = ["# 宇宙資本 投資事件行事曆", "", f"**{today.strftime('%Y-%m-%d')}**", ""]
    lines.append(f"（共 {total_dated} 筆事件，另有 {undated_count} 筆日期格式無法辨識）")
    return lines


def build_body(buckets, toggles):
    lines = []
    for key, label in BUCKET_LABELS:
        if not toggles.get(key, True):
            continue
        rows = buckets[key]
        lines.append(f"## {label}（{len(rows)} 筆）")
        lines.append("")
        if rows:
            lines += build_table(rows, dated=True, grouper=BUCKET_GROUPERS.get(key))
        else:
            lines.append("（無）")
        lines.append("")

    if toggles.get("undated", True):
        lines.append("## ⚪ 時間未定")
        lines.append("")
        if buckets["undated"]:
            lines += build_table(buckets["undated"], dated=False)
        else:
            lines.append("（無）")
        lines.append("")

    return lines


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    today = datetime.now()

    window_start, window_end = load_display_window()
    toggles = load_bucket_toggles()
    print(f"顯示範圍：{window_start} ~ {window_end or '不設上限'}")
    print(f"分桶開關：{toggles}")

    print("掃描 10_Stocks/ 的時間軸區塊...")
    entries = scan_catalyst_calendar()
    print(f"共擷取 {len(entries)} 筆時間軸條目。")

    buckets = bucket_entries(entries, window_start, window_end)
    total_dated = sum(len(buckets[k]) for k, _ in BUCKET_LABELS)
    undated_count = len(buckets['undated'])
    print(f"顯示範圍內且日期可解析：{total_dated} 筆；日期無法辨識：{undated_count} 筆。")

    title_block = build_title_block(today, total_dated, undated_count)
    note_block = build_note_block(window_start, window_end)
    body = build_body(buckets, toggles)

    # .md 檔保留 NOTE 說明區塊給自己看；PDF 版拿掉，避免每次印出來都先看到一大段
    # 技術性說明文字。
    md_lines = []
    md_lines.append("---")
    md_lines.append("type: catalyst_calendar")
    md_lines.append(f"date: {today.strftime('%Y-%m-%d')}")
    md_lines.append("author: LucasBrain AI")
    md_lines.append("tags: [report/catalyst-calendar]")
    md_lines.append("---")
    md_lines.append("")
    md_lines += title_block
    md_lines.append("")
    md_lines += note_block
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines += body

    pdf_lines = list(title_block)
    pdf_lines.append("")
    pdf_lines.append("---")
    pdf_lines.append("")
    pdf_lines += body

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stem = f"{today.strftime('%Y%m%d')}_宇宙資本_投資事件行事曆"
    out_path = os.path.join(OUTPUT_DIR, f"{stem}.md")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Generated catalyst calendar at: {out_path}")

    try:
        render_markdown_to_pdf(pdf_lines, OUTPUT_DIR, stem, extra_css=CATALYST_CALENDAR_EXTRA_CSS)
        print(f"Generated PDF at: {os.path.join(OUTPUT_DIR, stem + '.pdf')}")
    except Exception as e:
        print(f"Warning: Failed to generate PDF: {e}")


if __name__ == "__main__":
    main()
