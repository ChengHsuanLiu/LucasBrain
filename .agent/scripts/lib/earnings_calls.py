"""
法說會時程追蹤共用模組。

資料來源（兩個都能用純 HTTP 抓，不需瀏覽器）：
- Yahoo 股市行事曆 (tw.stock.yahoo.com/calendar/earnings-call)：預設列出「未來已公告」的全部場次，
  獨家提供「國內/國外」欄位與上市(.TW)/上櫃(.TWO)後綴；`?date=YYYY-MM-DD` 可取該日起約一週(回補歷史用)。
- 臺灣指數公司 IR 議合平台 (irengage.taiwanindex.com.tw/ConferenceList)：依年/月/市場別查詢，
  提供完整的原文摘要、多日活動的日期區間、已結束場次的簡報檔下載連結。

為什麼沒有玩股網與 MOPS：玩股網的 JSON 端點需要前端算出的簽章(純 HTTP 回 400)，且內容與上面兩者重疊；
MOPS 新版法說會頁只能單一公司查詢、舊版整批端點被反爬蟲封鎖。

兩個來源各有漏網場次（實測 Yahoo 缺 IR 有的、IR 也缺 Yahoo 有的），所以取聯集而非擇一。

資料存 SQLite（.agent/data/earnings_calls.db，已加入 .gitignore，不進 git）：
- events          : 每場法說會一列(目前狀態)，自然鍵 = (stock_code, event_date, event_time)
- event_changes   : 欄位異動歷史（改時間/改地點/摘要更新/簡報上傳/疑似取消 ...）
- fetch_runs      : 每次抓取每個來源的結果（筆數/成功與否/錯誤訊息），用來發現某來源悄悄壞掉

分層：
- fetch_yahoo / fetch_ir        : 純抓取+解析，回傳 observation list (dict)
- enrich_event                  : 純函式，從摘要/地點文字推導 形式/主辦/期別... (regex 規則，非語意理解)
- merge_observations            : 純函式，把兩個來源的 observation 合併成 event
- apply_events / sqlite 存取     : 寫入資料庫並產生異動紀錄
"""
import json
import os
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from html import unescape

from lxml import html as lxml_html

DB_PATH = r"C:\Users\User\Desktop\LucasBrain\.agent\data\earnings_calls.db"
STOCK_DIR = r"C:\Users\User\Desktop\LucasBrain\10_Stocks"

YAHOO_URL = "https://tw.stock.yahoo.com/calendar/earnings-call"
IR_URL = "https://irengage.taiwanindex.com.tw/ConferenceList"

REQUEST_INTERVAL_SEC = 1.0
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/130.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Accept-Encoding": "identity",
}

# 來源優先序：IR 是原文(未縮寫)，同一場次欄位衝突時以 IR 為準；scope(國內/國外) 只有 Yahoo 提供。
SOURCE_PRIORITY = ["ir", "yahoo"]

# 這些欄位的變動才寫進 event_changes。推導欄位(format/organizer...)是 regex 規則算出來的，
# 規則一改全庫都會「變」，記錄下來只是雜訊，所以只默默更新、不記異動。
TRACKED_FIELDS = ["event_time", "event_end_date", "location", "summary", "scope", "materials"]

# IR 才有原文；這些欄位本身是文字或由文字推導，只被 Yahoo(縮寫版)觀測到時不可覆蓋既有值
_TEXT_DERIVED_COLS = {"location", "summary", "format", "organizer_type", "organizer", "event_kind",
                      "event_series", "period_hint", "webcast_url"}


# ==========================================
# HTTP
# ==========================================
def _http_get(url, params=None, retries=3, timeout=30):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001 - 任何網路/解碼錯誤都重試
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url} 失敗 (重試{retries}次): {last_err}")


def _clean(text):
    # unescape：來源有些欄位被編碼兩次(解析後仍殘留 &#29319; 這類實體)，需要再解一層
    return re.sub(r"\s+", " ", unescape(text or "").replace("\xa0", " ")).strip()


def _norm_time(text):
    """'9:00' / '14:30~16:00' -> 'HH:MM'；無法辨識回傳空字串。"""
    m = re.search(r"(\d{1,2}):(\d{2})", text or "")
    if not m:
        return ""
    h, mi = int(m.group(1)), int(m.group(2))
    return f"{h:02d}:{mi:02d}" if h < 24 and mi < 60 else ""


# ==========================================
# Yahoo 解析
# 資料列 = <div class="table-body"> 底下的 <li>，li/div/div 依序是
# [股名+股號, 日期時間, 國內/國外, 地點, 相關訊息]。刻意不用 Yahoo 的原子化 CSS class
# (Pos(r) D(f)...) 定位，那種 class 隨時會改版；table-body 與欄位順序比較穩。
# ==========================================
# 後綴選填：少數公司(如已下市/特殊狀態者)Yahoo 只顯示純代號，沒有 .TW/.TWO
_YAHOO_CODE_RE = re.compile(r"^(\d{4,6}[A-Z]?)(?:\.(TWO?))?$")
_YAHOO_DT_RE = re.compile(r"(\d{4})/(\d{2})/(\d{2})(?:\s+(\d{1,2}:\d{2}))?")


def parse_yahoo(html_text):
    """回傳 (observations, skipped_rows)。"""
    doc = lxml_html.fromstring(html_text)
    rows, skipped = [], 0
    for li in doc.xpath('//div[contains(@class,"table-body")]//li'):
        cells = li.xpath("./div/div")
        if len(cells) != 5:
            skipped += 1
            continue
        pieces = [_clean(t) for t in cells[0].itertext() if _clean(t)]
        code_m = next((m for m in map(_YAHOO_CODE_RE.match, pieces) if m), None)
        dt_m = _YAHOO_DT_RE.match(_clean(cells[1].text_content()))
        if not code_m or not dt_m:
            skipped += 1
            continue
        name = next((p for p in pieces if not _YAHOO_CODE_RE.match(p)), "")
        scope = _clean(cells[2].text_content())
        rows.append({
            "source": "yahoo",
            "stock_code": code_m.group(1),
            "stock_name": name,
            "market": {"TW": "上市", "TWO": "上櫃"}.get(code_m.group(2), ""),
            "event_date": f"{dt_m.group(1)}-{dt_m.group(2)}-{dt_m.group(3)}",
            "event_end_date": "",
            "event_time": _norm_time(dt_m.group(4) or ""),
            "scope": scope if scope in ("國內", "國外") else "",
            "location": _clean(cells[3].text_content()),
            "summary": _clean(cells[4].text_content()),
            "materials": [],
        })
    return rows, skipped


def fetch_yahoo(start_date=None):
    """start_date=None 取預設(未來全部已公告)；給日期則取該日起約一週。"""
    params = {"date": start_date.isoformat()} if start_date else None
    rows, skipped = parse_yahoo(_http_get(YAHOO_URL, params))
    return rows, skipped


# ==========================================
# IR 議合平台解析
# 表格 6 欄：日期 | 時間 | 「代號 名稱」| 地點(<a data-msg=原文摘要>) | 摘要(同上，隱藏欄) | 下載(<button onclick=window.open(MOPS檔案))
# 注意：頁面把中文全部寫成數字實體(&#x53CB;)，所以不能對原始碼做字串比對，一律經 lxml 解析。
# 日期欄可能是區間 "2026/10/13~10/14"(多日活動，如 QIC CEO Week)。
# ==========================================
_IR_DATE_RE = re.compile(r"(\d{4})/(\d{2})/(\d{2})(?:\s*~\s*(?:(\d{4})/)?(\d{2})/(\d{2}))?")
_IR_COMPANY_RE = re.compile(r"^(\d{4,6}[A-Z]?)\s+(.+)$")
_IR_FILE_RE = re.compile(r"window\.open\('([^']+)'")
_IR_FILE_LANG_RE = re.compile(r"([ME])\d{3}\.\w+$")
_IR_MARKET = {"T": "上市", "O": "上櫃"}


def _parse_ir_materials(cell):
    out = []
    for btn in cell.xpath(".//button[@onclick]"):
        m = _IR_FILE_RE.search(btn.get("onclick", ""))
        if not m:
            continue
        url = m.group(1).replace("&amp;", "&")
        file_name = (urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("fileName") or [""])[0]
        lang_m = _IR_FILE_LANG_RE.search(file_name)
        out.append({"lang": {"M": "中文", "E": "英文"}.get(lang_m.group(1), "") if lang_m else "",
                    "file": file_name, "url": url})
    return out


def parse_ir(html_text):
    """回傳 (observations, skipped_rows)。market 欄位留空，由 fetch_ir 依 T/O 查詢結果補。"""
    doc = lxml_html.fromstring(html_text)
    rows, skipped = [], 0
    for tr in doc.xpath("//table//tbody/tr"):
        tds = tr.xpath("./td")
        if len(tds) < 5:
            # DataTables 的「查無資料」列只有 1 欄，不算解析失敗
            if not (len(tds) == 1 and tds[0].get("colspan")):
                skipped += 1
            continue
        date_m = _IR_DATE_RE.search(_clean(tds[0].text_content()))
        comp_m = _IR_COMPANY_RE.match(_clean(tds[2].text_content()))
        if not date_m or not comp_m:
            skipped += 1
            continue
        y, mo, d, end_y, end_mo, end_d = date_m.groups()
        end_date = f"{end_y or y}-{end_mo}-{end_d}" if end_mo else ""
        anchor = tds[3].xpath(".//a[@data-msg]")
        summary = _clean(anchor[0].get("data-msg")) if anchor else _clean(tds[4].text_content())
        rows.append({
            "source": "ir",
            "stock_code": comp_m.group(1),
            "stock_name": comp_m.group(2).strip(),
            "market": "",
            "event_date": f"{y}-{mo}-{d}",
            "event_end_date": end_date,
            "event_time": _norm_time(tds[1].text_content()),
            "scope": "",
            "location": _clean(tds[3].text_content()),
            "summary": summary,
            "materials": _parse_ir_materials(tds[-1]),
        })
    return rows, skipped


def fetch_ir_month(year, month):
    """抓某月全部場次(市場別=全部)，再各抓一次上市(T)/上櫃(O)用來標註市場別。
    市場別「全部」會比 T+O 多出興櫃等其他市場的場次，這些 market 留空。"""
    def query(market):
        return parse_ir(_http_get(IR_URL, {"Year": year, "Month": month, "Industry": "",
                                           "MarketType": market, "StockCode": ""}))

    all_rows, skipped = query("")
    time.sleep(REQUEST_INTERVAL_SEC)
    market_of = {}
    for code, label in _IR_MARKET.items():
        sub_rows, _ = query(code)
        time.sleep(REQUEST_INTERVAL_SEC)
        for r in sub_rows:
            market_of[(r["stock_code"], r["event_date"], r["event_time"])] = label
    for r in all_rows:
        r["market"] = market_of.get((r["stock_code"], r["event_date"], r["event_time"]), "")
    return all_rows, skipped


# ==========================================
# 推導欄位（純 regex 規則；摘要是公司自由填寫的文字，邊界案例會漏判，結果僅供快速篩選）
# ==========================================
_FOREIGN_RE = re.compile(
    r"香港|美國|日本|東京|大阪|新加坡|倫敦|紐約|舊金山|波士頓|歐洲|歐美|韓國|首爾|中國|上海|北京|深圳|"
    r"馬來西亞|泰國|越南|海外|澳門|Hong Kong|Singapore|Tokyo|London|New York|San Francisco", re.I)
_ONLINE_RE = re.compile(r"線上|網路|視訊|直播|webcast|zoom|teams|webex|google\s*meet", re.I)
_PHYSICAL_RE = re.compile(r"實體|會議室|飯店|酒店|大樓|廳|號|樓|路|街|Hotel|Road|Street", re.I)
_HYBRID_SUMMARY_RE = re.compile(r"同步(?:線上|直播|轉播)|線上同步|實體(?:及|與|暨|\+)線上|實體[/、]線上")
_URL_RE = re.compile(r"https?://[^\s，。；;)）」』]+")

# 主辦者名稱的字元：非標點非空白；但英文單字之間允許一個空白(CITIC CLSA、Morgan Stanley、J.P. Morgan)
_ORG_CHARS = r"(?:[^，。；,;「『\s]|(?<=[A-Za-z.])\s(?=[A-Za-z]))"
# 常見外資券商英文名（沒有「證券」二字，Chinese 規則抓不到）。CITIC CLSA 要排在 Citi 前面，並用 \b 避免 CITIC 被切成 CITI
_FOREIGN_IB_RE = (r"(?<![A-Za-z])(?i:J\.?\s?P\.?\s?Morgan|Morgan Stanley|Goldman Sachs|BofA(?:\s+Securities)?|Bank of America|"
                  r"CITIC CLSA|CLSA|Citi(?:group)?|UBS|Nomura|Macquarie|HSBC|Daiwa|Mizuho|Jefferies|Barclays|"
                  r"BNP Paribas|Deutsche Bank|Credit Suisse)(?![A-Za-z])")  # 不用 \b：中文字在 Python 也算 \w，「參加Nomura」中間沒有詞界
# 主辦者與動詞之間可能夾括號英文名「摩根士丹利證券 ( Morgan Stanley）」、時間地點「於115年10月7日…」「於2026/10/6在台北南港展覽館 所」
_ORG_GAP = r"\s*(?:[（(][^）)]{1,30}[）)])?\s*(?:於[^，。；,;]{1,40}?)?(?:所|之|的)?"
_ORG_PATTERNS = [
    re.compile(r"由\s*(?P<org>" + _ORG_CHARS + r"{2,24}?)" + _ORG_GAP + r"(?:主辦|舉辦|籌辦|召開|辦理)"),
    # 「受邀115年3月18日參加美銀證券所舉辦…」：受邀與參加之間可能夾日期
    re.compile(r"(?:受邀(?:\d+年\d+月\d+日)?(?:參加)?|參加)\s*(?P<org>" + _ORG_CHARS + r"{2,24}?)" + _ORG_GAP
               + r"(?:主辦|舉辦|舉行|籌辦|辦理)"),
    re.compile(r"受\s*(?P<org>" + _ORG_CHARS + r"{2,24}?)\s*(?:之)?邀請"),
    re.compile(r"應\s*(?P<org>" + _ORG_CHARS + r"{2,24}?)\s*之邀"),
    re.compile(r"參加\s*(?P<org>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)\s*(?:線上|實體)?(?:投資人|法人)?說明會"),
    # IR 平台常把摘要縮成「永豐金證券線上法說會」，沒有「舉辦/邀請」等動詞。[^\W\d_] = Unicode 字母(含中文)
    re.compile(r"(?P<org>[^\W\d_]{2,10}(?:證券|投顧|金控))\s*(?:線上|實體)?(?:投資人|法人)?(?:說明會|法說會)"),
    # 沒有「舉辦/主辦」動詞，只寫「受邀參加永豐金證券2026年第三季產業高峰論壇」。
    # (?!交易所) 避免把「台灣證券交易所」切成「台灣證券」
    re.compile(r"(?:參加|參與)\s*(?:由)?\s*(?P<org>[^\W\d_]{2,10}(?:證券|投顧|金控))(?!交易所)"),
    # 只寫英文機構名：「受邀參加Nomura Asia Tech Tour」「受邀參加 BofA 2026 Asia Pacific Conference」
    re.compile(r"(?:受邀|邀請|參加|參與|應)[^。]{0,40}?(?P<org>" + _FOREIGN_IB_RE + r")"),
    re.compile(r"(?:參加|參與)\s*(?P<org>台灣證券交易所|臺灣證券交易所|櫃買中心|證券櫃檯買賣中心)"),
]
_ORG_STOPWORDS = {"法人", "投資人", "本次", "線上", "實體", "公司", "海外", "國內", "本公司"}
_ORG_BAD_RE = re.compile(r"\d+\s*[年月日]|說明會$|法說會$|會議$")
_BROKER_RE = re.compile(r"證券|投顧|投信|資本|金控|銀行|期貨|Securities|Capital|Bank|BofA|Citi|Morgan|Goldman|"
                        r"Jefferies|UBS|Macquarie|Nomura|CLSA|HSBC|Daiwa|Mizuho|Barclays|BNP|Deutsche|Credit Suisse", re.I)
_ORG_SUFFIX_RE = re.compile(r"[（(]?股[)）]?(?:份有限)?公司$")
_SELF_RE = re.compile(r"自辦|自行(?:舉辦|召開|辦理)|本公司(?:將|擬)?(?:自行)?(?:舉辦|召開|辦理)|公司舉辦")
_NDR_RE = re.compile(r"NDR|海外路演|非交易路演|Roadshow", re.I)
_PERIOD_RE = re.compile(r"(?:(?P<roc>\d{2,3})|(?P<ad>20\d{2}))\s*年?(?:度)?\s*第\s*(?P<q>[1-4一二三四])\s*季")
_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4}


def infer_scope(location):
    return "國外" if _FOREIGN_RE.search(location or "") else "國內"


def infer_format(location, summary):
    """線上 / 電話會議 / 實體 / 實體+線上；地點空白回傳空字串。"""
    loc = location or ""
    if not loc:
        return ""
    if "電話" in loc:
        return "電話會議"
    online = bool(_ONLINE_RE.search(loc))
    physical = bool(re.search(r"實體", loc)) or (bool(_PHYSICAL_RE.search(loc)) and not online)
    if online and bool(re.search(r"實體", loc)):
        return "實體+線上"
    if online:
        return "線上"
    if physical and _HYBRID_SUMMARY_RE.search(summary or ""):
        return "實體+線上"
    return "實體"


def _infer_organizer_one(text):
    for pat in _ORG_PATTERNS:
        for m in pat.finditer(text):
            # 「A與B共同舉辦」取第一個主辦者。切分字元刻意不含「和」(大和國泰證券)
            org = re.split(r"[與及、]", m.group("org").strip("之所 "))[0]
            org = _ORG_SUFFIX_RE.sub("", org.removesuffix("共同").strip())
            # 「證券交易所舉辦」的「所」會被當成連接詞吃掉，補回
            org = re.sub(r"^([台臺]灣證券交易)$", r"\1所", org)
            # 名稱前黏著的項目編號「(1).」、日期「115/3/10」或動詞「參加」(動詞與主辦者之間夾了日期時會被一起吃進來)
            org = re.sub(r"^(?:(?:\(\d+\)[.、]?|\d{2,4}[/.-]\d{1,2}[/.-]\d{1,2}|參加|參與|受邀)\s*)+", "", org)
            if org and org not in _ORG_STOPWORDS and not _ORG_BAD_RE.search(org):
                if re.search(r"交易所|櫃買|櫃檯買賣", org):  # 名稱含「證券」但不是券商
                    return "其他主辦", org
                return ("券商主辦" if _BROKER_RE.search(org) else "其他主辦"), org
    if _SELF_RE.search(text):
        return "公司自辦", ""
    return "未明", ""


def infer_organizer(*summaries):
    """回傳 (organizer_type, organizer)。券商主辦 / 其他主辦(如 IR 顧問) / 公司自辦 / 未明。
    可傳入多個來源的摘要：IR 是原文、Yahoo 是縮寫，各自保留的線索不同，指名主辦者優先於自辦。"""
    results = [_infer_organizer_one(s or "") for s in summaries]
    for r in results:
        if r[1]:
            return r
    for r in results:
        if r[0] == "公司自辦":
            return r
    return "未明", ""


_FORUM_RE = re.compile(r"論壇|研討會|Conference(?!\s*Call)|Summit|Corporate Day|Tech Tour|Asia Tour|Investor Forum|業績發表會", re.I)


def infer_event_kind(summary, location):
    """法說會 / 券商論壇研討會 / 座談會 / 海外路演(NDR)。論壇類多家公司輪流上台，跟公司自己的法說會性質不同。"""
    text = f"{summary} {location}"
    if _NDR_RE.search(text):
        return "海外路演(NDR)"
    if "座談" in text:
        return "座談會"
    if _FORUM_RE.search(text):
        return "券商論壇/研討會"
    return "法說會"


def infer_event_series(summary):
    """多家公司共同參與的系列活動名稱，如 '20th QIC CEO Week'。"""
    for m in re.finditer(r"[「『]([^」』]{3,60})[」』]", summary or ""):
        s = m.group(1).strip()
        if re.search(r"[A-Za-z]{3,}", s):
            return s
    m = re.search(r"主辦之\s*([A-Za-z0-9][^，。；,;]{2,60})", summary or "")
    return m.group(1).strip() if m else ""


def infer_period(summary):
    """摘要中提到的財報期別，如 '2026Q3'。僅是摘要字面所述，公司偶爾會寫錯季別，勿當成事實。"""
    m = _PERIOD_RE.search(summary or "")
    if not m:
        return ""
    year = int(m.group("ad")) if m.group("ad") else int(m.group("roc")) + 1911
    q = m.group("q")
    return f"{year}Q{_CN_NUM.get(q) or int(q)}"


def infer_webcast_url(location, summary):
    m = _URL_RE.search(f"{location or ''} {summary or ''}")
    return m.group(0).rstrip(".,") if m else ""


def enrich_event(ev, all_summaries=()):
    """依 location/summary 補上推導欄位。scope 已由 Yahoo 給定時不覆蓋；
    all_summaries: 各來源的摘要，供主辦推導交叉參考。"""
    if ev.get("scope"):
        ev["scope_source"] = "yahoo"
    else:
        ev["scope"] = infer_scope(ev["location"])
        ev["scope_source"] = "inferred"
    ev["format"] = infer_format(ev["location"], ev["summary"])
    ev["organizer_type"], ev["organizer"] = infer_organizer(ev["summary"], *all_summaries)
    ev["event_kind"] = infer_event_kind(ev["summary"], ev["location"])
    ev["event_series"] = infer_event_series(ev["summary"])
    ev["period_hint"] = infer_period(ev["summary"])
    ev["webcast_url"] = infer_webcast_url(ev["location"], ev["summary"])
    return ev


_DERIVED_COLS = ["format", "organizer_type", "organizer", "event_kind", "event_series", "period_hint", "webcast_url"]


def rederive_all(conn):
    """
    不重新抓取，只用資料庫內已存的 location/summary 重算推導欄位。regex 規則改進後執行一次，
    就不必為了套用新規則而重建資料庫（重建會洗掉 event_changes 異動歷史）。
    沿用與 _update_event 相同的保守原則：空值不蓋既有值、「未明」不降級已判定的主辦；
    不寫 event_changes（推導欄位本來就不記異動）。回傳實際更新的場次數。
    """
    n = 0
    for row in conn.execute("SELECT * FROM events").fetchall():
        ev = {"scope": row["scope"] if row["scope_source"] == "yahoo" else "",
              "location": row["location"] or "", "summary": row["summary"] or ""}
        enrich_event(ev)
        updates = {}
        keep_organizer = bool(row["organizer"]) and not ev["organizer"]  # 既有主辦是靠另一來源的文字判出來的，別洗掉
        for col in _DERIVED_COLS:
            new, old = ev[col], row[col] or ""
            if (not new and old) or new == old:
                continue
            if col in ("organizer_type", "organizer") and keep_organizer:
                continue
            if col == "organizer_type" and new == "未明" and old:
                continue
            updates[col] = new
        if row["scope_source"] != "yahoo" and ev["scope"] != row["scope"]:
            updates["scope"] = ev["scope"]
        if updates:
            conn.execute(f"UPDATE events SET {', '.join(f'{k} = ?' for k in updates)} WHERE event_id = ?",
                         list(updates.values()) + [row["event_id"]])
            n += 1
    conn.commit()
    return n


# ==========================================
# 合併兩個來源
# ==========================================
def _merge_group(rows, note=""):
    by_src = {r["source"]: r for r in rows}
    ordered = [by_src[s] for s in SOURCE_PRIORITY if s in by_src]
    ev = {"sources": sorted(by_src), "from_ir": "ir" in by_src, "notes": note}
    for field in ("stock_code", "stock_name", "market", "event_date", "event_end_date", "event_time",
                  "scope", "location", "summary"):
        ev[field] = next((r[field] for r in ordered if r[field]), "")
    seen, materials = set(), []
    for r in ordered:
        for mat in r["materials"]:
            if mat["url"] not in seen:
                seen.add(mat["url"])
                materials.append(mat)
    ev["materials"] = materials
    return enrich_event(ev, [r["summary"] for r in ordered])


def merge_observations(observations):
    """同 (代號, 日期) 的各來源列合併為一場。兩來源時間不同但各只有一筆 → 視為同一場並註記時間不一致。"""
    groups = defaultdict(list)
    for o in observations:
        groups[(o["stock_code"], o["event_date"])].append(o)
    events = []
    for rows in groups.values():
        by_time = defaultdict(list)
        for r in rows:
            by_time[r["event_time"]].append(r)
        sources = {r["source"] for r in rows}
        if len(by_time) > 1 and len(rows) == len(sources):
            detail = " / ".join(f"{r['source']} {r['event_time'] or '無'}" for r in rows)
            events.append(_merge_group(rows, note=f"時間不一致: {detail}"))
        else:
            for group in by_time.values():
                events.append(_merge_group(group))
    return events


# ==========================================
# SQLite
# ==========================================
_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code      TEXT NOT NULL,
    stock_name      TEXT,
    market          TEXT,
    event_date      TEXT NOT NULL,
    event_end_date  TEXT,
    event_time      TEXT NOT NULL DEFAULT '',
    scope           TEXT,
    scope_source    TEXT,
    location        TEXT,
    format          TEXT,
    organizer_type  TEXT,
    organizer       TEXT,
    event_kind      TEXT,
    event_series    TEXT,
    period_hint     TEXT,
    webcast_url     TEXT,
    summary         TEXT,
    materials       TEXT,
    notes           TEXT,
    sources         TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL,
    last_changed    TEXT,
    UNIQUE (stock_code, event_date, event_time)
);
CREATE INDEX IF NOT EXISTS idx_events_date ON events (event_date);
CREATE INDEX IF NOT EXISTS idx_events_code ON events (stock_code);
CREATE TABLE IF NOT EXISTS event_changes (
    change_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER NOT NULL,
    changed_at  TEXT NOT NULL,
    field       TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT
);
CREATE INDEX IF NOT EXISTS idx_changes_event ON event_changes (event_id);
CREATE TABLE IF NOT EXISTS fetch_runs (
    run_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at       TEXT NOT NULL,
    source       TEXT NOT NULL,
    window_start TEXT,
    window_end   TEXT,
    ok           INTEGER NOT NULL,
    n_rows       INTEGER,
    n_skipped    INTEGER,
    error        TEXT
);
"""

_EVENT_COLS = ["stock_code", "stock_name", "market", "event_date", "event_end_date", "event_time", "scope",
               "scope_source", "location", "format", "organizer_type", "organizer", "event_kind",
               "event_series", "period_hint", "webcast_url", "summary", "materials", "notes"]


def connect(db_path=DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _log_change(conn, event_id, now, field, old, new):
    conn.execute("INSERT INTO event_changes (event_id, changed_at, field, old_value, new_value) "
                 "VALUES (?, ?, ?, ?, ?)", (event_id, now, field, old, new))


def _db_values(ev):
    """event dict -> 寫入 DB 的欄位值 (materials 轉 JSON 字串)。"""
    vals = {c: ev.get(c, "") or "" for c in _EVENT_COLS}
    vals["materials"] = json.dumps(ev["materials"], ensure_ascii=False) if ev["materials"] else ""
    return vals


def _insert_event(conn, ev, now):
    vals = _db_values(ev)
    cols = list(vals) + ["sources", "status", "first_seen", "last_seen"]
    params = list(vals.values()) + [",".join(ev["sources"]), "active", now, now]
    cur = conn.execute(f"INSERT INTO events ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", params)
    return cur.lastrowid


def _update_event(conn, row, ev, now, ok_sources):
    """用本次觀測更新既有場次，回傳異動欄位 list[(field, old, new)]。"""
    new_vals = _db_values(ev)
    changes = []
    updates = {}
    for col in _EVENT_COLS:
        new = new_vals[col]
        old = row[col] or ""
        if col == "notes":  # 時間不一致的註記只反映「這次」的狀態，不保留舊值
            if new != old:
                updates[col] = new
            continue
        # 空值不蓋掉既有值（例如 Yahoo 沒有「結束日」，不能把 IR 給的多日活動結束日洗掉）
        if not new and old:
            continue
        # 主辦判定「未明」只是沒線索，不蓋掉先前已判定出的結果
        if col == "organizer_type" and new == "未明" and old:
            continue
        # 文字及由文字推導的欄位：只有 IR(原文) 觀測到才覆蓋；只被 Yahoo(縮寫版) 觀測到時只補空白，
        # 否則 IR 暫時抓失敗的那天，摘要/主辦等會被換成 Yahoo 縮寫版的推導結果。
        if col in _TEXT_DERIVED_COLS and old and not ev["from_ir"]:
            continue
        # scope：Yahoo 才是權威；只有 IR 觀測到時，不拿推測值蓋掉 Yahoo 給的值
        if col in ("scope", "scope_source") and ev["scope_source"] != "yahoo" and row["scope_source"] == "yahoo":
            continue
        if new != old:
            updates[col] = new
            # scope 從「推測值」被 Yahoo 校正時只是補資料，不算異動
            if col in TRACKED_FIELDS and not (col == "scope" and row["scope_source"] != "yahoo"):
                changes.append((col, old, new))
    # 簡報檔只增不減(來源暫時缺漏不算異動)
    if "materials" in updates and not updates["materials"]:
        del updates["materials"]
        changes = [c for c in changes if c[0] != "materials"]

    # 來源清單 = (先前的來源 - 本次成功抓取的來源) + 本次觀測到的來源。
    # 本次抓取失敗的來源保留原狀，免得它暫時掛掉就被誤當成「已不再列出」。
    sources = ",".join(sorted((set(filter(None, row["sources"].split(","))) - ok_sources) | set(ev["sources"])))
    updates["last_seen"] = now
    if sources != row["sources"]:
        updates["sources"] = sources
    if row["status"] != "active":
        changes.append(("status", row["status"], "active"))
        updates["status"] = "active"
    if changes:
        updates["last_changed"] = now
    sets = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"UPDATE events SET {sets} WHERE event_id = ?", list(updates.values()) + [row["event_id"]])
    for field, old, new in changes:
        _log_change(conn, row["event_id"], now, field, old, new)
    return changes


_FILE_DATE_RE = re.compile(r"^\d{4,6}[A-Z]?(\d{4})(\d{2})(\d{2})[ME]\d{3}\.\w+$")


def material_file_date(file_name):
    """MOPS 簡報檔名 = 代號 + 上傳日期(YYYYMMDD) + M(中文)/E(英文) + 序號，如 300820260108M001.pdf。"""
    m = _FILE_DATE_RE.match(file_name or "")
    try:
        return date(int(m[1]), int(m[2]), int(m[3])) if m else None
    except ValueError:
        return None


def material_gap_days(event_date_iso, file_name):
    """場次日期 - 檔案日期(天)；檔名無法解析回傳 None。正數 = 檔案早於場次上傳。"""
    fd = material_file_date(file_name)
    return (date.fromisoformat(event_date_iso) - fd).days if fd else None


def resolve_material_owners(conn, events):
    """
    IR 平台會把公司「上一份簡報」掛在沒有自己簡報的場次上（例如券商座談會掛著上次法說會的簡報）。
    實測 5,069 份(公司,檔案)中有 628 份被掛在 2 個以上場次，共 1,441 筆錯掛。

    規則：同一公司的同一份檔案若出現在多個場次，只留給「場次日期離檔案上傳日最近」的那場。
    候選包含資料庫既有場次與本次新抓場次，所以只抓近 3 個月也能認出舊場次才是主人。
    只出現在單一場次的檔案無從比較，照單全收（CLI 顯示時會對日期差過大者另行標註）。
    直接修改 events 內的 materials。
    """
    candidates = defaultdict(set)  # (代號, 檔名) -> {掛有此檔的場次日期}
    for ev in events:
        for m in ev["materials"]:
            candidates[(ev["stock_code"], m["file"])].add(date.fromisoformat(ev["event_date"]))
    if not candidates:
        return
    for r in conn.execute("SELECT stock_code, event_date, materials FROM events WHERE materials != ''"):
        for m in json.loads(r["materials"]):
            key = (r["stock_code"], m["file"])
            if key in candidates:
                candidates[key].add(date.fromisoformat(r["event_date"]))
    for ev in events:
        d = date.fromisoformat(ev["event_date"])
        kept = []
        for m in ev["materials"]:
            fd = material_file_date(m["file"])
            dates = candidates[(ev["stock_code"], m["file"])]
            if fd is None or len(dates) < 2 or abs((d - fd).days) == min(abs((x - fd).days) for x in dates):
                kept.append(m)
        ev["materials"] = kept


def apply_events(conn, events, coverage, today, now, track_missing=True):
    """
    把本次合併後的 events 寫進資料庫。

    coverage: {source: (window_start_iso, window_end_iso)}，僅含「本次抓取成功且筆數合理」的來源。
    「疑似取消」判定：某未來場次先前被來源 S 列出，這次 S 抓取成功、場次日期落在 S 的涵蓋範圍內、
    卻沒被列出，就把 S 從該場次的 sources 拿掉；所有來源都拿掉 → status='missing'。
    只對未來場次判定；涵蓋範圍外的場次不動(例如 Yahoo 只列到某日為止，更遠的日期不能因此判定消失)。

    回傳 dict: new / changed / retimed / missing / restored (皆為 list)。
    """
    result = {"new": [], "changed": [], "retimed": [], "missing": [], "restored": []}
    resolve_material_owners(conn, events)
    rows_by_key ={(r["stock_code"], r["event_date"], r["event_time"]): r
                   for r in conn.execute("SELECT * FROM events")}
    rows_by_day = defaultdict(list)
    for r in rows_by_key.values():
        rows_by_day[(r["stock_code"], r["event_date"])].append(r)

    ok_sources = set(coverage)
    touched = set()
    leftovers = []

    for ev in events:
        row = rows_by_key.get((ev["stock_code"], ev["event_date"], ev["event_time"]))
        if row is None:
            leftovers.append(ev)
            continue
        touched.add(row["event_id"])
        changes = _update_event(conn, row, ev, now, ok_sources)
        _record_result(result, ev, row, changes)

    # 同代號同日期、時間不同：若既有只有一筆且本次沒被其他觀測命中、新來的也只有一筆 → 視為改時間
    incoming_by_day = defaultdict(list)
    for ev in leftovers:
        incoming_by_day[(ev["stock_code"], ev["event_date"])].append(ev)
    for day, evs in incoming_by_day.items():
        candidates = [r for r in rows_by_day.get(day, []) if r["event_id"] not in touched]
        if len(evs) == 1 and len(candidates) == 1:
            row = candidates[0]
            touched.add(row["event_id"])
            changes = _update_event(conn, row, evs[0], now, ok_sources)
            _record_result(result, evs[0], row, changes)
        else:
            for ev in evs:
                event_id = _insert_event(conn, ev, now)
                touched.add(event_id)  # 否則下面的「疑似取消」判定會把剛新增的場次當成沒被列出
                result["new"].append(dict(ev, event_id=event_id))

    if track_missing:
        for row in conn.execute("SELECT * FROM events WHERE event_date >= ? AND status = 'active'", (today.isoformat(),)):
            if row["event_id"] in touched:
                continue
            srcs = set(filter(None, row["sources"].split(",")))
            for s in ok_sources:
                start, end = coverage[s]
                if s in srcs and start <= row["event_date"] <= end:
                    srcs.discard(s)
            if srcs == set(filter(None, row["sources"].split(","))):
                continue
            if srcs:
                conn.execute("UPDATE events SET sources = ? WHERE event_id = ?", (",".join(sorted(srcs)), row["event_id"]))
            else:
                conn.execute("UPDATE events SET sources = '', status = 'missing', last_changed = ? WHERE event_id = ?",
                             (now, row["event_id"]))
                _log_change(conn, row["event_id"], now, "status", "active", "missing")
                result["missing"].append(dict(row))
    conn.commit()
    return result


def _record_result(result, ev, row, changes):
    fields = {c[0] for c in changes}
    info = dict(ev, event_id=row["event_id"], changes=changes, old_time=row["event_time"])
    if "status" in fields:
        result["restored"].append(info)
    if "event_time" in fields:
        result["retimed"].append(info)
    elif fields - {"status"}:
        result["changed"].append(info)


def guess_rescheduled(result):
    """同一代號本次同時『新增』與『疑似取消』→ 很可能是改期而非新增/取消，回傳 [(代號, 舊日期, 新日期)]。"""
    new_by_code = defaultdict(list)
    for ev in result["new"]:
        new_by_code[ev["stock_code"]].append(ev["event_date"])
    out = []
    for ev in result["missing"]:
        for new_date in new_by_code.get(ev["stock_code"], []):
            out.append((ev["stock_code"], ev["stock_name"], ev["event_date"], new_date))
    return out


def log_fetch_run(conn, now, source, window, ok, n_rows, n_skipped, error=""):
    conn.execute("INSERT INTO fetch_runs (run_at, source, window_start, window_end, ok, n_rows, n_skipped, error) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (now, source, window[0] if window else None, window[1] if window else None,
                  int(ok), n_rows, n_skipped, error))
    conn.commit()


def count_known_future(conn, source, today):
    """資料庫裡、先前被某來源列出的『今天以後』場次數，用來判斷這次抓到的筆數是否異常偏少。
    刻意不限縮在「這次回傳資料的日期範圍」內：回傳筆數少時該範圍會跟著縮小，已知筆數也就跟著變少，
    防護就失效了（頁面只載入一半時最需要它）。已過去的場次不算，所以場次自然結束造成的減少不會誤觸發。"""
    cur = conn.execute("SELECT COUNT(*) FROM events WHERE status = 'active' AND event_date >= ? "
                       "AND (',' || sources || ',') LIKE ?", (today.isoformat(), f"%,{source},%"))
    return cur.fetchone()[0]


# ==========================================
# 查詢
# ==========================================
_WEEKDAY = "一二三四五六日"


def load_vault_pages(stock_dir=STOCK_DIR):
    """10_Stocks/ 現有個股頁面：{代號: 頁面名稱(不含 .md，可直接用於 [[wikilink]])}，檔名形如 '2313華通.md'。"""
    if not os.path.isdir(stock_dir):
        return {}
    return {m.group(1): f[:-3] for f in os.listdir(stock_dir)
            if f.endswith(".md") and (m := re.match(r"^(\d{4,6}[A-Z]?)", f))}


def load_vault_tickers(stock_dir=STOCK_DIR):
    """10_Stocks/ 現有個股頁面的代號集合。"""
    return set(load_vault_pages(stock_dir))


def last_success_run(conn):
    """最近一次『所有來源都成功』的抓取時間 (ISO 字串)；沒有紀錄回傳 None。
    以各來源最近一次成功時間中較早的那個為準——只要有一個來源停擺，資料就不算新鮮。"""
    times = []
    for source in ("yahoo", "ir"):
        r = conn.execute("SELECT MAX(run_at) FROM fetch_runs WHERE source = ? AND ok = 1", (source,)).fetchone()
        if not r[0]:
            return None
        times.append(r[0])
    return min(times)


def tracking_baseline(conn):
    """開始追蹤的日期(第一次抓取)。這天(含)之前入庫的場次是回補的存量，不能算『新增』。"""
    r = conn.execute("SELECT MIN(run_at) FROM fetch_runs").fetchone()
    return date.fromisoformat(r[0][:10]) if r[0] else None


def query_new_events(conn, days=7, today=None):
    """近 N 天新入庫、尚未召開的場次；排除追蹤起始日(含)以前入庫的回補存量。"""
    today = today or date.today()
    baseline = tracking_baseline(conn)
    if baseline is None:
        return []
    since = max((today - timedelta(days=days)), baseline + timedelta(days=1)).isoformat()
    sql = ("SELECT * FROM events WHERE substr(first_seen, 1, 10) >= ? AND event_date >= ? "
           "AND status = 'active' ORDER BY first_seen DESC, event_date, event_time")
    return [dict(r) for r in conn.execute(sql, (since, today.isoformat()))]


def query_upcoming(conn, days=14, ticker=None, today=None, include_missing=False):
    today = today or date.today()
    sql = "SELECT * FROM events WHERE event_date BETWEEN ? AND ?"
    params = [today.isoformat(), (today + timedelta(days=days)).isoformat()]
    if not include_missing:
        sql += " AND status = 'active'"
    if ticker:
        sql += " AND stock_code = ?"
        params.append(ticker)
    sql += " ORDER BY event_date, event_time, stock_code"
    return [dict(r) for r in conn.execute(sql, params)]


def query_changes(conn, days=7, today=None):
    today = today or date.today()
    since = (datetime.combine(today, datetime.min.time()) - timedelta(days=days)).isoformat(timespec="seconds")
    sql = ("SELECT c.changed_at, c.field, c.old_value, c.new_value, e.stock_code, e.stock_name, e.event_date, e.event_time, "
           "e.status FROM event_changes c JOIN events e USING (event_id) WHERE c.changed_at >= ? ORDER BY c.changed_at DESC")
    return [dict(r) for r in conn.execute(sql, (since,))]


def format_event_line(ev, vault_tickers=()):
    """一場一行的人類可讀格式。"""
    d = date.fromisoformat(ev["event_date"])
    when = f"{ev['event_date']}({_WEEKDAY[d.weekday()]})"
    if ev["event_end_date"]:
        when += f"~{ev['event_end_date'][5:]}"
    star = " ★" if ev["stock_code"] in vault_tickers else ""
    org = ev["organizer"] or ev["organizer_type"]
    parts = [ev["scope"], ev["format"], org, ev["event_kind"] if ev["event_kind"] != "法說會" else ""]
    tags = "/".join(p for p in parts if p)
    flag = " ⚠疑似取消" if ev.get("status") == "missing" else ""
    return f"{when} {ev['event_time'] or '--:--'}  {ev['stock_code']} {ev['stock_name']}{star}  [{tags}] {ev['location']}{flag}"
