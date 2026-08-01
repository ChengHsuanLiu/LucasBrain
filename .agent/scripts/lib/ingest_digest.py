"""
從 33_Ingest_Records/ 的 ingest 紀錄中，抽取適合放進 DailyReport 最後一區塊的
「消息面更新」摘要。

篩選規則（人工訂定，寫在這裡供未來調整時參考）：
1. 只保留「## 更新內容」段落下、標題含至少一個 [[股票]] wikilink 的區塊——
   代表這是已展開個股頁面的更新，非資料庫追蹤標的的區塊（標題沒有 wikilink）整段捨棄。
2. 每個區塊最多保留 3 條 bullet；內容以「豐富但不失控」為原則——句子在 280 字以內
   全文保留，超過才在最近的句界（。／；）截斷，而非只取第一句，讓 EPS/理由等細節留得住。
3. 若 bullet 包含「分歧」「矛盾」「相反」等分歧訊號關鍵字，視為高含金量分析線索，
   放寬到 400 字才截斷，且整塊卡片會標記為「分歧」樣式。
4. 「## 大戶籌碼追蹤」段落預設整段捨棄（DailyReport 自身的籌碼/動能區塊已涵蓋這塊），
   只有 bullet 命中「暴增/倍增/翻倍/急增/驟減/歸零/清倉/全數平倉/史上新高/史上最高」
   等異常變動關鍵字時才保留該句，且整塊卡片標記為「籌碼異常」樣式。
5. 每條 bullet 依內容關鍵字附一個小標籤（評等/目標價、EPS、分歧訊號、籌碼異常），
   供排版時決定顏色，方便一眼掃過類別。
"""
import glob
import os
import re

INGEST_RECORDS_DIR = r"C:\Users\User\Desktop\LucasBrain\33_Ingest_Records"

DIVERGENCE_KEYWORDS = ["分歧", "矛盾", "背離"]
WHALE_EXTREME_KEYWORDS = [
    "暴增", "倍增", "翻倍", "急增", "驟減", "歸零",
    "清倉", "全數平倉", "史上新高", "史上最高",
]
RATING_KEYWORDS = ["評等", "TP", "目標價", "重申", "OW", "OP", "買進", "持股"]
EPS_KEYWORDS = ["EPS", "獲利", "毛利率", "營收"]

MAX_BULLETS_PER_BLOCK = 3
NORMAL_MAX_LEN = 280
DIVERGENCE_MAX_LEN = 400
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def find_ingest_records_for_date(date_str):
    """date_str 格式 YYYY-MM-DD，回傳當天所有 ingest record 檔案路徑（依檔名時間排序）。"""
    prefix = date_str.replace("-", "")
    pattern = os.path.join(INGEST_RECORDS_DIR, f"{prefix}*_ingest.md")
    return sorted(glob.glob(pattern))


def _bullet_tag(text):
    """依內容關鍵字判斷這條 bullet 該貼哪個小標籤，優先序：分歧 > 評等/TP > EPS > 一般。"""
    if any(kw in text for kw in DIVERGENCE_KEYWORDS):
        return ("分歧訊號", "badge-red")
    if any(kw in text for kw in RATING_KEYWORDS):
        return ("評等/目標價", "badge-green")
    if any(kw in text for kw in EPS_KEYWORDS):
        return ("EPS/財務", "badge-amber")
    return (None, None)


def _truncate_bullet(text):
    is_divergence = any(kw in text for kw in DIVERGENCE_KEYWORDS)
    limit = DIVERGENCE_MAX_LEN if is_divergence else NORMAL_MAX_LEN

    if len(text) <= limit:
        return text.rstrip()

    window = text[:limit]
    m = None
    for mm in re.finditer(r"[。；]", window):
        m = mm
    cut = m.end() if m else limit
    result = text[:cut].rstrip("，、")
    if cut < len(text):
        result += "…"
    return result


def _split_heading(heading):
    """把「被動元件 MLCC 漲價循環（[[2327國巨]] [[2492華新科]]）」這類標題
    拆成 (主題文字, [股票名稱, ...])；主題文字去掉 wikilink 與其外圍的括號/斜線分隔裝飾，
    但保留像「7/20早報」這種文字本身就含斜線的部分（斜線旁沒有 wikilink 才留著）。"""
    tickers = WIKILINK_RE.findall(heading)
    theme = heading
    # 先整段拿掉「（[[..]] [[..]] ...）」這種括號包住、內容全是 wikilink 的群組
    theme = re.sub(r"[（(]\s*(?:\[\[[^\]]+\]\]\s*)+[）)]", "", theme)
    # 再拿掉任何殘留的單顆 wikilink，含它左右緊鄰的「/」分隔符號
    theme = re.sub(r"\s*/?\s*\[\[[^\]]+\]\]\s*/?\s*", " ", theme)
    theme = re.sub(r"\s+", " ", theme).strip()
    theme = re.sub(r"^[（(]+|[）)]+$", "", theme).strip()
    return theme, tickers


def _parse_update_section(body):
    """從「## 更新內容」到下一個「## 」之間的內容，切成 (heading, [bullets]) 清單。"""
    m = re.search(r"^## 更新內容\s*$", body, flags=re.M)
    if not m:
        return []
    rest = body[m.end():]
    next_h2 = re.search(r"^## ", rest, flags=re.M)
    section = rest[: next_h2.start()] if next_h2 else rest

    blocks = re.split(r"^### ", section, flags=re.M)
    results = []
    for block in blocks[1:]:
        lines = block.strip("\n").split("\n")
        heading = lines[0].strip()
        bullet_lines = [ln[2:].strip() for ln in lines[1:] if ln.startswith("- ")]
        results.append((heading, bullet_lines))
    return results


def _parse_whale_section(body):
    m = re.search(r"^## 大戶籌碼追蹤\s*$", body, flags=re.M)
    if not m:
        return []
    rest = body[m.end():]
    next_h2 = re.search(r"^## ", rest, flags=re.M)
    section = rest[: next_h2.start()] if next_h2 else rest
    return [ln[2:].strip() for ln in section.split("\n") if ln.startswith("- ")]


def extract_digest_entries(record_path):
    """回傳 card 清單，每張 card 為 dict：
    {theme, tickers, bullets: [(text, tag_label, tag_class), ...], style}
    style 為 "divergence" / "whale-alert" / None，供排版決定卡片配色。"""
    with open(record_path, "r", encoding="utf-8") as f:
        body = f.read()

    cards = []
    for heading, bullets in _parse_update_section(body):
        if "[[" not in heading:
            continue  # 沒有 wikilink，代表是「非資料庫追蹤個股」摘要區塊，整段捨棄
        theme, tickers = _split_heading(heading)
        kept_raw = [b for b in bullets[:MAX_BULLETS_PER_BLOCK] if b]
        if not kept_raw:
            continue
        bullet_entries = []
        card_style = None
        for b in kept_raw:
            tag_label, tag_class = _bullet_tag(b)
            if tag_label == "分歧訊號":
                card_style = "divergence"
            bullet_entries.append((_truncate_bullet(b), tag_label, tag_class))
        cards.append({
            "theme": theme,
            "tickers": tickers,
            "bullets": bullet_entries,
            "style": card_style,
        })

    whale_bullets = _parse_whale_section(body)
    flagged = [b for b in whale_bullets if any(kw in b for kw in WHALE_EXTREME_KEYWORDS)]
    if flagged:
        cards.append({
            "theme": "大戶籌碼異常變動",
            "tickers": [],
            "bullets": [(b, "籌碼異常", "badge-red") for b in flagged],
            "style": "whale-alert",
        })

    return cards


def build_digest_for_date(date_str):
    """回傳當天（可能有多份）ingest record 彙整後的 card 清單。"""
    all_cards = []
    for path in find_ingest_records_for_date(date_str):
        all_cards.extend(extract_digest_entries(path))
    return all_cards
