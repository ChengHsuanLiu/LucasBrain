"""
催化劑日曆 (catalyst calendar) 掃描模組。

不維護獨立資料源，直接掃描既有的 `10_Stocks/*.md` 的
「## 📅 重大事件與時間軸 (Schedule) > ### 📌 預估時間軸 (Expected Timeline)」區塊。
（20_Garden/ 的產業層級時間軸目前不掃，見 scan_catalyst_calendar 的 include_garden 參數。）

每次執行即時重新解析全庫，不存在「一次性快照過期」的問題（舊版 `30_Projects/Invest_Timeline/`
就是手動/AI 一次性彙整、之後不再更新的靜態文件，這是本模組要解決的問題）。

日期格式在既有筆記裡並不統一（YYYY-MM-DD / YYYY-MM / 2026Q3 / 4Q26 / 2026H2 / 2H26 /
2026年底 / 2026下半年 / 純年份 / 範圍如「2027 - 2029」...），parse_period() 盡量涵蓋常見
寫法，並依精細度標記 granularity（year/half/quarter/date），供報告依此分桶與統一顯示格式。
範圍過大（超過一年）的 token 視為無法乾淨歸類，直接回傳 None 捨棄不顯示。
"""
import calendar
import os
import re
from datetime import date

STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"
GARDEN_DIR = r"C:\Users\User\Desktop\LucasBrain\20_Garden"
SETTINGS_PATH = r"C:\Users\User\Desktop\LucasBrain\97_Settings\催化劑日曆設定.md"

_BULLET_RE = re.compile(
    r'^[\*\-]\s*\*\*\[?([^\]\*]+?)\]?\*\*\s*(?:`\[?([^`]+?)\]?`)?\s*[:：]?\s*(.+)$'
)

# 分類規則：依序比對，命中第一個符合的類別即回傳。順序本身就是優先權——
# 藥證/籌碼/價格/認證/訂單/供應鏈重組 這幾類關鍵字較specific，排在前面；
# 「產能」「出貨」「技術」這類常見詞彙較容易與其他類別重疊，排在後面當作
# 較不精確的分類；「財報與營收」是最後的數字型 catch-all。
_CATEGORY_RULES = [
    ("🧪 藥證與臨床", ["藥證", "FDA", "PDUFA", "臨床", "解盲", "NDA", "DSMB", "適應症"]),
    ("💵 籌碼與融資", ["可轉債", "現增", "增資", "掛牌", "上櫃", "上市", "法說會", "法人說明會",
                    "股東會", "庫藏股", "回購", "緘默期"]),
    ("💰 價格變動", ["漲價", "調漲", "降價", "跌價", "售價", "報價", "轉嫁", "漲幅", "價格"]),
    ("✅ 認證", ["認證", "驗證", "AVL", "送樣", "查廠", "驗收", "sample out", "通過"]),
    ("🔀 供應鏈重組", ["轉單", "取代", "讓出", "釋出", "反超", "洗牌"]),
    ("📝 訂單", ["訂單", "拿下", "大單", "標案", "簽約", "承接", "中標", "新客戶"]),
    ("🏭 產能與擴廠", ["產能", "擴產", "擴廠", "新廠", "投產", "產線", "kwpm", "稼動率", "完工",
                    "量產", "安裝", "裝機"]),
    ("📦 出貨", ["出貨", "放量", "交貨", "拉升"]),
    ("⚙️ 技術與規格", ["製程", "世代", "規格", "導入", "技術", "奈米"]),
    ("📊 財報與營收", ["營收", "EPS", "毛利率", "財報", "季報", "資本支出", "目標價", "淨利率", "由虧轉盈"]),
]
_DEFAULT_CATEGORY = "🗂️ 其他"


def classify_category(desc):
    """依關鍵字比對把事件描述歸入固定分類（見 _CATEGORY_RULES）。純字面規則，
    非語意理解，遇到邊界案例可能誤判，僅供快速歸類用，不是精確判斷。"""
    for label, keywords in _CATEGORY_RULES:
        for kw in keywords:
            if kw.lower() in desc.lower():
                return label
    return _DEFAULT_CATEGORY


# ==========================================
# 日期解析：每個 token 解析成 Period(start, end, granularity, precision)
# granularity ∈ {'date', 'quarter', 'half', 'year'}；precision 只在 granularity=='date'
# 時有意義：'day'=有明確日、'month'=只有年月、'month_range'=同年跨兩個月（如「8-9月」）。
# ==========================================
class Period:
    __slots__ = ("start", "end", "granularity", "precision")

    def __init__(self, start, end, granularity, precision='day'):
        self.start = start
        self.end = end
        self.granularity = granularity
        self.precision = precision


def _month_last_day(y, m):
    return calendar.monthrange(y, m)[1]


def _quarter_range(year, q):
    start_month = (q - 1) * 3 + 1
    end_month = start_month + 2
    return date(year, start_month, 1), date(year, end_month, _month_last_day(year, end_month))


def _half_range(year, h):
    if h == 1:
        return date(year, 1, 1), date(year, 6, 30)
    return date(year, 7, 1), date(year, 12, 31)


def _expand_year(yy_str):
    yy = int(yy_str)
    return 2000 + yy if yy < 100 else yy


def _parse_single_period(token):
    """解析單一時間片語（不含範圍符號），回傳 Period 或 None。"""
    t = token.strip().strip('[]').strip()
    if not t:
        return None

    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', t)
    if m:
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return Period(d, d, 'date', precision='day')
        except ValueError:
            return None

    m = re.match(r'^(\d{4})-(\d{1,2})$', t)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return Period(date(y, mo, 1), date(y, mo, _month_last_day(y, mo)), 'date', precision='month')
        return None

    # 其他年月寫法："2026M9"、"2026/9"、"2026年9月"、"2026年7月中旬"（上/中/下旬
    # 併入月精細度，不特別區分——沒有比「月」更細的桶，中旬/下旬只靠原文件行序決勝）
    m = re.match(r'^(\d{4})\s*[Mm/／]\s*(\d{1,2})$', t)
    if not m:
        m = re.match(r'^(\d{4})\s*年\s*(\d{1,2})\s*月\s*(?:上旬|中旬|下旬)?$', t)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return Period(date(y, mo, 1), date(y, mo, _month_last_day(y, mo)), 'date', precision='month')
        return None

    # 同年月份範圍："2026年8-9月"、"2026 年 8-9 月"（顯示為 8~9月，排序上自然落在
    # 8月與9月之間：start 與純8月同為8月1日，但 end 較晚，靠 (start, end) 排序決勝）
    m = re.match(r'^(\d{4})\s*年?\s*(\d{1,2})\s*[-~]\s*(\d{1,2})\s*月$', t)
    if m:
        y, mo1, mo2 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo1 <= 12 and 1 <= mo2 <= 12 and mo1 <= mo2:
            return Period(date(y, mo1, 1), date(y, mo2, _month_last_day(y, mo2)), 'date', precision='month_range')
        return None

    # "YYYY-MM/MM"：月份斜線範圍（如 "2026-06/07"、"2026-10/11"），取較早的月份
    m = re.match(r'^(\d{4})-(\d{1,2})/(\d{1,2})$', t)
    if m:
        y, mo1, mo2 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        earliest = min(mo1, mo2)
        if 1 <= earliest <= 12:
            return Period(date(y, earliest, 1), date(y, earliest, _month_last_day(y, earliest)), 'date', precision='month')
        return None

    m = re.match(r'^(\d{4})\s*年?\s*[Qq]\s*([1-4])$', t)
    if not m:
        m = re.match(r'^(\d{4})-([1-4])\s*[Qq]$', t)  # "2026-4Q"（年-季度Q，Q在數字後）
    if m:
        s, e = _quarter_range(int(m.group(1)), int(m.group(2)))
        return Period(s, e, 'quarter')

    m = re.match(r'^([1-4])\s*[Qq]\s*(\d{2,4})$', t)
    if m:
        s, e = _quarter_range(_expand_year(m.group(2)), int(m.group(1)))
        return Period(s, e, 'quarter')

    m = re.match(r'^(\d{4})\s*年?\s*[Hh]\s*([12])$', t)
    if m:
        s, e = _half_range(int(m.group(1)), int(m.group(2)))
        return Period(s, e, 'half')

    m = re.match(r'^([12])\s*[Hh]\s*(\d{2,4})$', t)
    if m:
        s, e = _half_range(_expand_year(m.group(2)), int(m.group(1)))
        return Period(s, e, 'half')

    m = re.match(r'^(\d{4})\s*年底$', t)
    if m:
        y = int(m.group(1))
        return Period(date(y, 10, 1), date(y, 12, 31), 'quarter')  # 年底＝Q4

    m = re.match(r'^(\d{4})\s*年初$', t)
    if m:
        y = int(m.group(1))
        return Period(date(y, 1, 1), date(y, 3, 31), 'quarter')  # 年初＝Q1

    m = re.match(r'^(\d{4})\s*年中$', t)
    if m:
        y = int(m.group(1))
        return Period(date(y, 4, 1), date(y, 8, 31), 'half')

    m = re.match(r'^(\d{4})\s*上半年$', t)
    if m:
        s, e = _half_range(int(m.group(1)), 1)
        return Period(s, e, 'half')

    m = re.match(r'^(\d{4})\s*下半年$', t)
    if m:
        s, e = _half_range(int(m.group(1)), 2)
        return Period(s, e, 'half')

    m = re.match(r'^(\d{4})\s*全年$', t)
    if m:
        y = int(m.group(1))
        return Period(date(y, 1, 1), date(y, 12, 31), 'year')

    m = re.match(r'^(\d{4})\s*年?$', t)
    if m:
        y = int(m.group(1))
        return Period(date(y, 1, 1), date(y, 12, 31), 'year')

    return None


def _classify_by_span(start, end):
    """僅供「範圍」token（結合左右兩側後）使用，依總天數粗略歸類精細度；
    超過一年（366天）視為範圍過大，回傳 'oversized'——這跟「完全無法解析」不同，
    呼叫端要能區分兩者：無法解析的條目仍要顯示在「時間未定」供人工檢查，範圍過大的
    條目則是解析成功但明確決定不顯示（見 bucket_entries 對 granularity=='oversized' 的處理）。"""
    span = (end - start).days
    if span > 366:
        return 'oversized'
    if span <= 31:
        return 'date'
    if span <= 100:
        return 'quarter'
    if span <= 200:
        return 'half'
    return 'year'


def _combine_strict(left, right):
    """僅在左右兩側都成功解析時才回傳合併區間，避免把「日期+一段敘述」誤判成日期範圍
    （例如 "2026-07-03 更新，來源：XX報告" 若用寬鬆合併，會把左側 "2026" 誤當成年份、
    右側敘述丟棄，變成錯誤的全年區間）。回傳 Period 或 None。"""
    if not (left and right):
        return None
    start, end = left.start, right.end
    granularity = _classify_by_span(start, end)
    return Period(start, end, granularity, precision=('month' if granularity == 'date' else 'day'))


def parse_period(raw_token):
    """解析時間軸日期欄位（單一時間片語或用 -／~／至／到 分隔的範圍）。
    回傳 Period；無法辨識或範圍過大（超過一年）回傳 None。"""
    if not raw_token:
        return None
    t = raw_token.strip().strip('[]').strip()
    if not t:
        return None

    single = _parse_single_period(t)
    if single:
        return single

    # 同年季度簡寫範圍，如 "2026Q3/Q4" 或 "2026Q3-Q4"
    m = re.match(r'^(\d{4})\s*[Qq]\s*([1-4])\s*[/\-~]\s*[Qq]?\s*([1-4])$', t)
    if m:
        y = int(m.group(1))
        s, _ = _quarter_range(y, int(m.group(2)))
        _, e = _quarter_range(y, int(m.group(3)))
        return Period(s, e, _classify_by_span(s, e))

    # 範圍寫法僅在整個 token 本身就是「短片語-短片語」時才嘗試，且左右兩側都要能
    # 各自獨立解析成功，避免把夾帶長敘述文字的日期欄位誤判為範圍。
    if len(t) <= 40:
        for sep in ['~', '至', '到', '-']:
            if sep in t:
                left, right = t.split(sep, 1)
                combined = _combine_strict(_parse_single_period(left), _parse_single_period(right))
                if combined:
                    return combined

    # 最後手段：token 開頭是一段完整日期/年月，後面接著一串敘述文字而非另一個可解析的
    # 日期（例如 "2026-06-07 供應鏈更新"）。整段當「範圍」解析會失敗（右側不是日期），
    # 但開頭那段本身就是一筆明確日期，值得取出來單獨使用，而不是整條丟進時間未定。
    m = re.match(r'^(\d{4}-\d{1,2}(?:-\d{1,2})?)\b', t)
    if m:
        leading = _parse_single_period(m.group(1))
        if leading:
            return leading

    return None


def format_period_label(period):
    """統一顯示格式：年度事件顯示 "YYYY"；半年度顯示 "YYYY-HN"；季度顯示 "YYYY-QN"；
    有明確日期顯示 "YYYY-MM-DD"；只有年月顯示 "YYYY-M月"（無前導零）；同年跨月範圍
    顯示 "YYYY-M~M月"。"""
    s = period.start
    if period.granularity == 'year':
        return f"{s.year}"
    if period.granularity == 'half':
        h = 1 if s.month <= 6 else 2
        return f"{s.year}-H{h}"
    if period.granularity == 'quarter':
        q = (s.month - 1) // 3 + 1
        return f"{s.year}-Q{q}"
    if period.precision == 'month_range':
        return f"{s.year}-{s.month}~{period.end.month}月"
    if period.precision == 'month':
        return f"{s.year}-{s.month}月"
    return f"{s.year}-{s.month:02d}-{s.day:02d}"


def _derive_stock_display(filename):
    m = re.match(r'^([0-9]+(?:\.[a-zA-Z0-9]+)?)(.*?)\.md$', filename)
    if m:
        ticker, name = m.group(1), m.group(2)
        page = f"{ticker}{name}"
        return page, f"[[{page}|{ticker}<br>{name}]]"  # 代號/名稱分兩行顯示，仍連到完整頁面
    page = filename[:-3]
    return page, f"[[{page}]]"


def _derive_garden_display(filename):
    return filename[:-3] if filename.endswith('.md') else filename


def _extract_section(content, header, next_header_prefixes):
    idx = content.find(header)
    if idx == -1:
        return None
    start = idx + len(header)
    end = len(content)
    for prefix in next_header_prefixes:
        pos = content.find(f'\n{prefix}', start)
        if pos != -1:
            end = min(end, pos)
    return content[start:end]


_VAGUE_TIME_MARKERS = ('近期', '稍後', '日後', '陸續')


def _looks_like_time_reference(token):
    """粗略過濾：Garden 頁面的 Timeline 區塊有時混入非時間性的主題小標（例如
    「鋁質電容迎來大轉機」「技術代差」），這些被 bullet 正則誤判為「日期」欄位。
    只有 token 含數字，或包含常見的模糊時間詞，才視為真正的時間標記；否則整條
    捨棄（不歸入時間未定，因為它根本不是一筆有時間性的事件）。"""
    if any(ch.isdigit() for ch in token):
        return True
    return any(marker in token for marker in _VAGUE_TIME_MARKERS)


def _extract_entries(filepath, header, display_name, source_link, next_header_prefixes):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception:
        return []

    block = _extract_section(content, header, next_header_prefixes)
    if not block:
        return []

    entries = []
    for line in block.split('\n'):
        line = line.strip()
        bm = _BULLET_RE.match(line)
        if not bm:
            continue
        date_token, category, desc = bm.group(1), bm.group(2), bm.group(3)
        date_token = date_token.strip()
        desc = desc.strip()
        if not desc or desc in ('待補充', '[請填寫近期趨勢與重要時間軸里程碑，按時間排序]'):
            continue
        if not _looks_like_time_reference(date_token):
            continue
        entries.append({
            "date_token": date_token,
            "period": parse_period(date_token),
            "category": (category or "").strip('[]').strip(),
            "type": classify_category(desc),
            "desc": desc,
            "source": display_name,
            "source_link": source_link,
        })
    return entries


def scan_catalyst_calendar(stock_dir=STOCK_DIR, garden_dir=GARDEN_DIR, include_garden=False):
    """掃描時間軸區塊，回傳所有解析出來的條目（含日期解析失敗者，period=None）。

    include_garden=False（目前預設）時只掃 10_Stocks/ 的個股層級時間軸，不掃
    20_Garden/ 的產業層級時間軸——後者有幾頁（4_系統層_被動元件、4_系統層_光通訊光模組、
    伺服器無電纜化架構、3_上游_材料矽晶圓光罩）的 Timeline 區塊寫成主題式技術分析而非
    真正逐項有日期的里程碑，混進來的雜訊比訊號多；其餘 Garden 頁面雖然格式良好，但目前
    先以個股為主，之後如果要重新納入產業層級事件，把 include_garden 設為 True 即可，
    不需要改動掃描邏輯本身。"""
    entries = []

    if os.path.isdir(stock_dir):
        for filename in os.listdir(stock_dir):
            if not filename.endswith('.md'):
                continue
            fp = os.path.join(stock_dir, filename)
            display_name, source_link = _derive_stock_display(filename)
            entries += _extract_entries(
                fp, "### 📌 預估時間軸 (Expected Timeline)",
                display_name, source_link, ('##', '###', '---'),
            )

    if include_garden and os.path.isdir(garden_dir):
        for filename in os.listdir(garden_dir):
            if not filename.endswith('.md'):
                continue
            fp = os.path.join(garden_dir, filename)
            display_name = _derive_garden_display(filename)
            entries += _extract_entries(
                fp, "## 📅 產業趨勢與產品迭代時間軸 (Timeline)",
                display_name, f"[[{display_name}]]", ('##', '---'),
            )

    return entries


# ==========================================
# 設定表讀取
# ==========================================
def load_display_window(settings_path=SETTINGS_PATH, default_start=None, default_end=None):
    """讀取「顯示範圍」設定表，回傳 (start_date, end_date)。留空或解析失敗時使用
    default_start（預設今天）／default_end（預設 None＝不設上限）。"""
    start = default_start or date.today()
    end = default_end

    try:
        with open(settings_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read().split('\n')
    except Exception:
        return start, end

    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        cols = [c.strip() for c in line.split('|')[1:-1]]
        if len(cols) < 2:
            continue
        label, value = cols[0], cols[1]
        m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', value)
        if label == '開始日期' and m:
            start = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        elif label == '結束日期' and m:
            end = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    return start, end


_BUCKET_TOGGLE_LABELS = {
    '顯示年度事件': 'year',
    '顯示半年度事件': 'half',
    '顯示季度事件': 'quarter',
    '顯示明確時間事件': 'date',
    '顯示時間未定': 'undated',
}


def load_bucket_toggles(settings_path=SETTINGS_PATH):
    """讀取「分桶顯示開關」設定表，回傳 {'year':bool, 'half':bool, 'quarter':bool,
    'date':bool, 'undated':bool}。設定表讀不到或缺列時預設為 True（顯示）。"""
    toggles = {key: True for key in _BUCKET_TOGGLE_LABELS.values()}

    try:
        with open(settings_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read().split('\n')
    except Exception:
        return toggles

    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        cols = [c.strip() for c in line.split('|')[1:-1]]
        if len(cols) < 2:
            continue
        label, value = cols[0], cols[1]
        key = _BUCKET_TOGGLE_LABELS.get(label)
        if key:
            toggles[key] = value.strip().upper() == 'Y'

    return toggles


# ==========================================
# 分桶：依「精細度」而非「距今天數」分類
# ==========================================
def bucket_entries(entries, window_start=None, window_end=None):
    """依 granularity 把條目分成 4 桶：year（年度事件）/half（半年度事件）/
    quarter（季度事件）/date（明確時間事件），各桶內依開始日期由舊到新排序。
    無法解析日期的條目歸入 undated，不受時間窗篩選（因為無從判斷是否在範圍內）。
    granularity=='oversized'（範圍跨超過一年，如「2027-2028」）的條目直接捨棄，
    不進任何桶——這跟「完全無法解析」不同，是解析成功後明確決定不顯示。

    window_start/window_end：只保留與 [window_start, window_end] 有重疊的條目——
    即區間結束日 >= window_start（尚未在窗口開始前就結束），且區間開始日 <= window_end
    （還沒晚到窗口結束之後才開始）。window_end=None 表示不設上限。"""
    buckets = {"year": [], "half": [], "quarter": [], "date": [], "undated": []}

    for e in entries:
        period = e["period"]
        if period is None:
            buckets["undated"].append(e)
            continue
        if period.granularity == 'oversized':
            continue
        if window_start and period.end < window_start:
            continue
        if window_end and period.start > window_end:
            continue
        buckets[period.granularity].append(e)

    for key in ("year", "half", "quarter", "date"):
        # 用 (start, end) 排序而非只用 start：像「2026年8-9月」跟純「2026-8月」的
        # start 都是8月1日會平手，加上 end 當次要鍵，範圍較長的（跨到9月）會排在
        # 純8月之後、純9月之前，符合「放在8月跟9月中間」的直覺。
        buckets[key].sort(key=lambda e: (e["period"].start, e["period"].end))

    return buckets
