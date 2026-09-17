import os
import re
import sys
from datetime import datetime, timedelta

VAULT_ROOT = r"c:\Users\User\Desktop\LucasBrain"
STOCK_DIR = os.path.join(VAULT_ROOT, "10_Stocks")
GARDEN_DIR = os.path.join(VAULT_ROOT, "20_Garden")
LOG_PATH = os.path.join(VAULT_ROOT, "log.md")
INGEST_RECORDS_DIR = os.path.join(VAULT_ROOT, "33_Ingest_Records")
DEST_DIR = os.path.join(VAULT_ROOT, "30_Projects", "Weekly_Report")

BULLET_RE = re.compile(r'^-\s+(.*)$')
LINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]*)?\]\]')
LOG_HEADER_RE = re.compile(r'^## \[(\d{4}-\d{2}-\d{2})\](.*)$', re.MULTILINE)
INGEST_SECTION_RE = re.compile(r'^## 更新內容\s*\n(.*?)(?=\n## |\Z)', re.MULTILINE | re.DOTALL)
INGEST_SUBHEADING_RE = re.compile(r'^### (.*)$', re.MULTILINE)


def get_week_range(target_date=None):
    if target_date:
        end = datetime.strptime(target_date, "%Y%m%d").date()
    else:
        end = datetime.now().date()
    monday = end - timedelta(days=end.weekday())
    return monday, end


def parse_log_entries(monday, end):
    with open(LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    matches = list(LOG_HEADER_RE.finditer(content))
    blocks = []
    for i, m in enumerate(matches):
        date_str = m.group(1)
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if not (monday <= entry_date <= end):
            continue
        start = m.end()
        stop = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:stop]
        header_text = m.group(2)
        blocks.append((entry_date, header_text, body))
    return blocks


def find_ingest_record(entry_date):
    """找出與 log.md 某條 ingest 條目同一天的 33_Ingest_Records 原始檔（檔名慣例 YYYYMMDD_HHMMSS_ingest.md）。"""
    if not os.path.isdir(INGEST_RECORDS_DIR):
        return None
    prefix = entry_date.strftime('%Y%m%d')
    candidates = sorted(
        f for f in os.listdir(INGEST_RECORDS_DIR)
        if f.startswith(prefix) and f.endswith('_ingest.md')
    )
    if not candidates:
        return None
    return os.path.join(INGEST_RECORDS_DIR, candidates[-1])


def parse_ingest_record_updates(filepath):
    """解析 ingest record 的「## 更新內容」段落，回傳 {頁面名稱: [bullet文字...]}，供 log.md 漏寫時的補漏 fallback 用。"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception:
        return {}

    section_match = INGEST_SECTION_RE.search(content)
    if not section_match:
        return {}
    section = section_match.group(1)

    result = {}
    sub_matches = list(INGEST_SUBHEADING_RE.finditer(section))
    for i, sm in enumerate(sub_matches):
        heading = sm.group(1)
        body_start = sm.end()
        body_stop = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(section)
        body = section[body_start:body_stop]
        names = [n.strip() for n in LINK_RE.findall(heading)]
        if not names:
            continue
        bullet_lines = []
        for raw_line in body.split('\n'):
            line = raw_line.strip()
            bm = BULLET_RE.match(line)
            if bm:
                bullet_lines.append(bm.group(1))
        if not bullet_lines:
            continue
        for name in names:
            result.setdefault(name, []).extend(bullet_lines)
    return result


def existing_page_names():
    stock_names = set()
    if os.path.isdir(STOCK_DIR):
        for f in os.listdir(STOCK_DIR):
            if f.endswith('.md'):
                stock_names.add(f[:-3])
    garden_names = set()
    if os.path.isdir(GARDEN_DIR):
        for f in os.listdir(GARDEN_DIR):
            if f.endswith('.md'):
                garden_names.add(f[:-3])
    return stock_names, garden_names


def collect_weekly_bullets(blocks, stock_names, garden_names):
    stock_updates = {}
    garden_updates = {}
    for entry_date, header_text, body in blocks:
        covered_names = set()
        for raw_line in body.split('\n'):
            line = raw_line.strip()
            m = BULLET_RE.match(line)
            if not m:
                continue
            text = m.group(1)
            links = LINK_RE.findall(text)
            if not links:
                continue
            for name in links:
                name = name.strip()
                covered_names.add(name)
                if name in stock_names:
                    stock_updates.setdefault(name, []).append((entry_date, text))
                elif name in garden_names:
                    garden_updates.setdefault(name, []).append((entry_date, text))

        # 完整性檢查：header的「影響」清單裡有、但log.md本文沒寫bullet的頁面，回頭讀當天的
        # ingest record原始檔補一條fallback bullet，避免log.md漏寫導致週報整頁消失。
        header_names = {n.strip() for n in LINK_RE.findall(header_text)}
        missing_names = {
            n for n in header_names - covered_names
            if n in stock_names or n in garden_names
        }
        if not missing_names:
            continue
        record_path = find_ingest_record(entry_date)
        if not record_path:
            continue
        fallback_map = parse_ingest_record_updates(record_path)
        for name in missing_names:
            lines = fallback_map.get(name)
            if not lines:
                continue
            fallback_text = "⚠️（補自ingest record，log.md未收錄）" + "；".join(lines)
            if name in stock_names:
                stock_updates.setdefault(name, []).append((entry_date, fallback_text))
            else:
                garden_updates.setdefault(name, []).append((entry_date, fallback_text))
    return stock_updates, garden_updates


def parse_frontmatter_fields(filepath):
    fields = {"valuation_rating": "HOLD", "current_price": None, "forward_pe": None}
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception:
        return fields
    m_yaml = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not m_yaml:
        return fields
    for line in m_yaml.group(1).split('\n'):
        line = line.strip()
        for key in ("valuation_rating", "current_price", "forward_pe"):
            prefix = key + ":"
            if line.startswith(prefix):
                raw = line[len(prefix):]
                raw = raw.split('#', 1)[0].strip()
                fields[key] = raw.strip('"').strip("'")
    return fields


def rating_icon(rating):
    return "🔺" if (rating or "").strip().upper() == "ADD" else "🔷"


def ticker_sort_key(name):
    m = re.match(r'^(\d+)', name)
    return int(m.group(1)) if m else 999999


def group_pages_by_signature(updates):
    """把「同一週更新內容完全相同」的頁面合併成一組，避免同一段敘述被逐頁重複貼上。"""
    groups = {}
    order = []
    for name, bullets in updates.items():
        sig = tuple(bullets)
        if sig not in groups:
            groups[sig] = []
            order.append(sig)
        groups[sig].append(name)
    return [(groups[sig], list(sig)) for sig in order]


def build_stock_block(names, bullets):
    if len(names) == 1:
        name = names[0]
        fields = parse_frontmatter_fields(os.path.join(STOCK_DIR, name + ".md"))
        icon = rating_icon(fields["valuation_rating"])
        header = f"{icon} {name}:"
        status_parts = [f"目前評等：{fields['valuation_rating']}"]

        try:
            price_val = float(fields["current_price"]) if fields["current_price"] else None
        except ValueError:
            price_val = None
        if price_val:
            status_parts.append(f"現價：{price_val:g}元")

        try:
            pe_val = float(fields["forward_pe"]) if fields["forward_pe"] else None
        except ValueError:
            pe_val = None
        if pe_val:
            status_parts.append(f"Forward PE：{pe_val:.1f}x")

        status_line = "｜".join(status_parts)
    else:
        ratings = [parse_frontmatter_fields(os.path.join(STOCK_DIR, n + ".md"))["valuation_rating"] for n in names]
        icon = "🔺" if any((r or "").strip().upper() == "ADD" for r in ratings) else "🔷"
        header = f"{icon} {'、'.join(names)}（同批更新，內容重疊已合併）:"
        status_line = None

    lines = [header, ""]
    if status_line:
        lines.append(f"> {status_line}")
        lines.append("")
    lines.append("[本周更新]")
    if bullets:
        for d, text in bullets:
            lines.append(f"- ({d.strftime('%m-%d')}) {text}")
    else:
        lines.append("無")
    lines.append("")
    lines.append("[操作想法]")
    lines.append("（請Lucas填寫本週操作想法）")
    return "\n".join(lines)


def build_garden_block(names, bullets):
    suffix = "（產業）" if len(names) == 1 else "（產業，同批更新，內容重疊已合併）"
    header = f"🔷 {'、'.join(names)}{suffix}:"
    lines = [header, "", "[本周更新]"]
    for d, text in bullets:
        lines.append(f"- ({d.strftime('%m-%d')}) {text}")
    return "\n".join(lines)


def generate_weekly_report(target_date=None):
    monday, end = get_week_range(target_date)
    os.makedirs(DEST_DIR, exist_ok=True)
    dest_filepath = os.path.join(DEST_DIR, f"{end.strftime('%Y%m%d')}_Weekly_Report.md")

    blocks = parse_log_entries(monday, end)
    stock_names, garden_names = existing_page_names()
    stock_updates, garden_updates = collect_weekly_bullets(blocks, stock_names, garden_names)

    stock_groups = group_pages_by_signature(stock_updates)
    stock_groups.sort(key=lambda item: min(ticker_sort_key(n) for n in item[0]))

    garden_groups = group_pages_by_signature(garden_updates)
    garden_groups.sort(key=lambda item: min(item[0]))

    ingest_dates = sorted(set(d.strftime('%m-%d') for d, _, _ in blocks))

    report = []
    report.append("---")
    report.append("type: weekly_report")
    report.append(f"date: {end.strftime('%Y-%m-%d')}")
    report.append(f"range: {monday.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}")
    report.append("author: LucasBrain AI")
    report.append("tags: [investment/weekly-report]")
    report.append(f"aliases: [週報, 週報-{end.strftime('%Y-%m-%d')}]")
    report.append("---")
    report.append("")
    report.append(f"# {end.strftime('%Y%m%d')} 週報（{monday.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}）")
    report.append("")
    if ingest_dates:
        report.append(f"> 本週（{monday.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}）共有 {len(blocks)} 次 ingest 更新：{'、'.join(ingest_dates)}。以下【個股資訊 & 產業資訊】段落由本週 ingest 內容（`log.md`）自動彙整，其餘段落請手動填寫。")
    else:
        report.append(f"> 本週（{monday.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}）尚無 ingest 更新，以下個股/產業段落為空，請視情況手動補充。")
    report.append("")
    report.append("## 【大盤】")
    report.append("> （請Lucas手動填寫本週大盤重點：大盤指數、類股表現、籌碼動能、總經數據等）")
    report.append("")
    report.append("## 【近期關注事件】")
    report.append("> （請Lucas手動填寫近期關注事件：法說會、選舉、央行會議、地緣政治等時間點）")
    report.append("")
    report.append("## 【個股資訊 & 產業資訊】")
    report.append("")
    report.append("### 個股")
    report.append("")
    if stock_groups:
        first = True
        for names, bullets in stock_groups:
            if not first:
                report.append("")
                report.append("---")
                report.append("")
            first = False
            report.append(build_stock_block(names, bullets))
    else:
        report.append("（本週無個股更新）")
    report.append("")
    report.append("### 產業")
    report.append("")
    if garden_groups:
        first = True
        for names, bullets in garden_groups:
            if not first:
                report.append("")
                report.append("---")
                report.append("")
            first = False
            report.append(build_garden_block(names, bullets))
    else:
        report.append("（本週無產業更新）")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 【結論與交易想法】")
    report.append("> 市場氣氛：（請填寫）")
    report.append("> 個人想法：（請填寫）")
    report.append(">")
    report.append("> （請Lucas手動填寫本週結論與交易想法）")
    report.append("")

    md_text = "\n".join(report)
    with open(dest_filepath, 'w', encoding='utf-8') as f:
        f.write(md_text)

    print(f"Generated Weekly Report at: {dest_filepath}")
    print(f"Range: {monday.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}, {len(blocks)} ingest run(s), {len(stock_updates)} stock page(s), {len(garden_updates)} garden page(s) updated.")
    return dest_filepath


if __name__ == "__main__":
    t_date = sys.argv[1] if len(sys.argv) > 1 else None
    generate_weekly_report(t_date)
