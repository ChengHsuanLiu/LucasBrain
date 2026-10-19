# -*- coding: utf-8 -*-
"""
TWMD (TW Market Data, twmarketdata.com) 資料存取層。

為什麼走 MCP 端點而不是 REST：
    REST (api.twmarketdata.com/v2/datasets/*) 每個端點都必須帶單一 symbol，只能逐檔查詢；
    MCP 端點 (mcp.twmarketdata.com/mcp) 的 query_dataset 可以不帶代號查全市場，並支援 as_of 與
    keyset cursor。點數是「每次呼叫固定計點」而非逐列計算，所以全市場分頁拉取比逐檔查詢便宜得多
    （2026-10-19 實測：上市單日股價 1,380 列 = 14 次呼叫 = 14 點；月營收全市場 1,980 檔 = 66 點）。
    這是把 MCP 傳輸層當批次 API 用的非文件化用法，格式日後可能變動；出問題先檢查本檔的
    _Session / query_dataset 兩處。

核心行為：
    - 分頁：沿 meta.pagination.next_cursor 一路取到沒有下一頁。
    - 自動縮頁：MCP 單次回應有 40,000 字元的 inline 上限，超過時只回 20 列預覽 + 無法兌換的
      handle（meta.result_delivery.all_rows_inlined == False）。偵測到就依預覽實際塞得下的列數
      縮小 limit，並用同一個 cursor 重試；學到的 limit 會記在行程內，同資料集下次直接用。
    - 快取：每次成功查詢都寫 .agent/data/cache/twmd/，即時抓取失敗（額度用盡、網路中斷）時退回最近
      一次成功的快取並印警告，與 stock_metrics._finmind_request 的備援慣例一致。
    - 金鑰：讀 .agent/credentials.json 的 twmd_api_key（檔案已被 .gitignore 排除），其次環境變數
      TWMD_API_KEY。金鑰絕不印出、不寫進快取或錯誤訊息。

三大法人注意：institutional_by_type 只有上櫃資料（上市 T86 無轉售授權，任何方案都買不到），
查上市代號會得到空結果並出現在 QueryResult.missing，不是 0。
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime

CREDENTIALS_PATH = r"C:\Users\User\Desktop\LucasBrain\.agent\credentials.json"
CACHE_DIR = r"C:\Users\User\Desktop\LucasBrain\.agent\data\cache\twmd"
MCP_URL = "https://mcp.twmarketdata.com/mcp"

INITIAL_LIMIT = 100        # 每頁列數起點；實際值會依 inline 上限自動調整並記住
MIN_LIMIT = 5
MAX_PAGES = 500            # 防呆：避免 cursor 異常時無限迴圈
REQUEST_TIMEOUT = 90
MAX_ATTEMPTS = 3           # 暫時性錯誤 (429/5xx/網路) 的重試次數


class TwmdError(RuntimeError):
    pass


class TwmdQuotaError(TwmdError):
    """HTTP 402：點數用盡或方案不含此資料集。"""


class TwmdNotLicensed(TwmdError):
    """資料集因授權裁定不對外供應（例如上市三大法人 institutional_flow）。"""


class QueryResult:
    """query_dataset 的回傳：rows 為全部資料列；missing 是請求了但沒有資料的代號
    （原因見 missing_reason，絕不能當 0 或沿用舊值）。"""

    def __init__(self, rows, missing=None, missing_reason=None, pages=0, credits=0,
                 from_cache=False, cached_at=None):
        self.rows = rows
        self.missing = missing or []
        self.missing_reason = missing_reason or {}
        self.pages = pages
        self.credits = credits
        self.from_cache = from_cache
        self.cached_at = cached_at

    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return len(self.rows)


# ==========================================
# 金鑰與連線
# ==========================================
def _load_api_key(credentials_path=CREDENTIALS_PATH):
    key = None
    try:
        if os.path.exists(credentials_path):
            with open(credentials_path, "r", encoding="utf-8") as cf:
                key = json.load(cf).get("twmd_api_key")
    except Exception as e:
        print(f"Warning: 讀取 credentials.json 失敗: {type(e).__name__}")
    key = key or os.environ.get("TWMD_API_KEY")
    if not key:
        raise TwmdError('找不到 TWMD 金鑰：請在 .agent/credentials.json 加入 "twmd_api_key"'
                        "（或設定環境變數 TWMD_API_KEY）")
    return key


class _Session:
    """最小 MCP streamable-HTTP 用戶端：initialize 一次，之後只用 tools/call。"""

    def __init__(self):
        self._key = None
        self._session_id = None
        self._ready = False
        self._next_id = 0

    def _headers(self):
        if self._key is None:
            self._key = _load_api_key()
        h = {"X-API-Key": self._key, "Content-Type": "application/json",
             "Accept": "application/json, text/event-stream"}
        if self._session_id:
            h["Mcp-Session-Id"] = self._session_id
        return h

    def _post(self, payload, expect_reply=True):
        data = json.dumps(payload).encode("utf-8")
        last_err = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            req = urllib.request.Request(MCP_URL, data=data, headers=self._headers(), method="POST")
            try:
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
                    sid = r.headers.get("Mcp-Session-Id")
                    if sid:
                        self._session_id = sid
                    body = r.read().decode("utf-8", "replace")
                    ctype = r.headers.get("Content-Type", "")
                break
            except urllib.error.HTTPError as e:
                if e.code == 402:
                    raise TwmdQuotaError("TWMD 回傳 402：點數用盡或方案不含此資料集") from None
                if e.code in (401, 403):
                    raise TwmdError(f"TWMD 認證失敗 (HTTP {e.code})：請檢查 credentials.json 的 twmd_api_key") from None
                last_err = f"HTTP {e.code}"
                if e.code != 429 and e.code < 500:
                    raise TwmdError(f"TWMD 請求失敗 ({last_err})") from None
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last_err = type(e).__name__
            if attempt < MAX_ATTEMPTS:
                time.sleep(2.0 * attempt)
        else:
            raise TwmdError(f"TWMD 請求失敗，重試 {MAX_ATTEMPTS} 次仍不成功 ({last_err})")

        if not expect_reply or not body.strip():
            return None
        if "event-stream" in ctype:
            for line in body.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:].strip())
            return None
        return json.loads(body)

    def _ensure_ready(self):
        if self._ready:
            return
        self._next_id += 1
        self._post({"jsonrpc": "2.0", "id": self._next_id, "method": "initialize",
                    "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                               "clientInfo": {"name": "lucasbrain-twmd-client", "version": "1"}}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect_reply=False)
        self._ready = True

    def call_tool(self, name, arguments):
        self._ensure_ready()
        self._next_id += 1
        reply = self._post({"jsonrpc": "2.0", "id": self._next_id, "method": "tools/call",
                            "params": {"name": name, "arguments": arguments}})
        if not reply:
            raise TwmdError(f"TWMD {name} 沒有回應內容")
        if "error" in reply:
            raise TwmdError(f"TWMD {name} JSON-RPC 錯誤: {str(reply['error'])[:200]}")
        result = reply.get("result") or {}
        payload = result.get("structuredContent")
        if payload is None:
            text = "".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
            try:
                payload = json.loads(text)
            except ValueError:
                raise TwmdError(f"TWMD {name} 回傳非 JSON 內容: {text[:120]}") from None
        return payload


_session = _Session()
_learned_limit = {}   # {dataset_id: 上次驗證過、整頁都塞得進 inline 上限的 limit}


# ==========================================
# 快取
# ==========================================
def _cache_path(dataset_id, params):
    tag = "_".join(params["tickers"]) if params.get("tickers") else "ALL"
    tag = re.sub(r"[^A-Za-z0-9_.-]", "_", tag)[:60]
    digest = hashlib.sha1(json.dumps(params, sort_keys=True, ensure_ascii=True).encode("ascii")).hexdigest()[:10]
    return os.path.join(CACHE_DIR, f"{dataset_id}__{tag}__{digest}.json")


def _read_cache(path):
    try:
        with open(path, "r", encoding="utf-8") as cf:
            return json.load(cf)
    except Exception:
        return None


def _write_cache(path, params, result):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as cf:
            json.dump({"cached_at": datetime.now().isoformat(), "params": params, "rows": result.rows,
                       "missing": result.missing, "missing_reason": result.missing_reason},
                      cf, ensure_ascii=False)
    except Exception:
        pass  # 快取寫入失敗不影響本次正常回傳


def _result_from_cache(cached):
    return QueryResult(cached["rows"], cached.get("missing"), cached.get("missing_reason"),
                       from_cache=True, cached_at=cached.get("cached_at"))


# ==========================================
# 查詢
# ==========================================
def _fetch_live(dataset_id, params):
    limit = _learned_limit.get(dataset_id, INITIAL_LIMIT)
    rows, cursor, pages, credits = [], None, 0, 0
    missing, missing_reason = [], {}
    for _ in range(MAX_PAGES):
        args = {"dataset_id": dataset_id, "limit": limit}
        for k in ("start", "end", "as_of"):
            if params.get(k):
                args[k] = params[k]
        if params.get("tickers"):
            args["tickers"] = params["tickers"]
        if cursor:
            args["cursor"] = cursor
        j = _session.call_tool("query_dataset", args)

        if j.get("error"):
            msg = str(j.get("message") or j["error"])[:300]
            if j.get("not_licensed") or "not_licensed" in str(j["error"]):
                raise TwmdNotLicensed(f"{dataset_id}: {msg}")
            raise TwmdError(f"{dataset_id}: {msg}")

        meta = j.get("meta") or {}
        delivery = meta.get("result_delivery") or {}
        if delivery and delivery.get("all_rows_inlined") is False:
            # 本頁超過 inline 上限、只拿到固定 20 列預覽：用「本頁總字元數 / 列數」估每列大小，
            # 算出 40,000 字元預算塞得下幾列（留 15% 餘裕），同一個 cursor 重試
            total_rows = int(delivery.get("total_rows") or 0)
            payload_chars = int(delivery.get("payload_chars") or 0)
            budget = int(delivery.get("char_budget") or 40000)
            if total_rows and payload_chars:
                new_limit = max(MIN_LIMIT, min(int(limit * 0.9), int(budget * 0.85 * total_rows / payload_chars)))
            else:
                new_limit = max(MIN_LIMIT, int(limit * 0.6))
            if new_limit >= limit:
                raise TwmdError(f"{dataset_id}: 單頁已縮到 limit={limit} 仍超過 inline 上限，無法再縮")
            limit = new_limit
            continue

        pages += 1
        credits += (j.get("credits") or {}).get("charged") or 0
        rows.extend(j.get("data") or [])
        cov = j.get("coverage") or {}
        for t in cov.get("missing") or []:
            if t not in missing:
                missing.append(t)
        if isinstance(cov.get("reason"), dict):
            missing_reason.update(cov["reason"])

        pg = meta.get("pagination") or j.get("pagination") or {}
        cursor = pg.get("next_cursor")
        if not cursor or not j.get("data"):
            break
    else:
        raise TwmdError(f"{dataset_id}: 超過 {MAX_PAGES} 頁仍未結束，中止")

    _learned_limit[dataset_id] = limit
    return QueryResult(rows, missing, missing_reason, pages=pages, credits=credits)


def query_dataset(dataset_id, tickers=None, start=None, end=None, as_of=None, max_age_hours=0):
    """查詢一個資料集的全部列（自動分頁/縮頁），回傳 QueryResult。

    tickers=None 為全市場；start/end 為 YYYY-MM-DD（篩的是該資料集自己的時間欄，例如月營收
    篩的是揭露日而非營收月份）；回測請務必帶 as_of 防未來函數。
    max_age_hours>0 且快取夠新時直接用快取、完全不連網；預設 0 = 一律即時抓取，失敗才退回快取。"""
    params = {"tickers": sorted(tickers) if tickers else None, "start": start, "end": end, "as_of": as_of}
    path = _cache_path(dataset_id, params)
    cached = _read_cache(path)
    if cached and max_age_hours > 0:
        try:
            age_h = (datetime.now() - datetime.fromisoformat(cached["cached_at"])).total_seconds() / 3600
            if age_h <= max_age_hours:
                return _result_from_cache(cached)
        except Exception:
            pass
    try:
        result = _fetch_live(dataset_id, params)
    except TwmdNotLicensed:
        raise
    except TwmdError as e:
        if cached:
            print(f"Warning: TWMD 即時抓取失敗 ({e})，改用 {cached.get('cached_at', '未知時間')} 的快取資料"
                  f" ({dataset_id}/{','.join(tickers) if tickers else '全市場'})")
            return _result_from_cache(cached)
        raise
    _write_cache(path, params, result)
    return result


# ==========================================
# 便利函式
# ==========================================
def monthly_revenue_history(ticker, since="2024-01", as_of=None, max_age_hours=12):
    """單檔月營收，由舊到新排序的 list：
        [{"year_month": "2026-09", "revenue": 5.824e9 (元), "revenue_k": 5824212.0 (千元),
          "yoy_pct": 110.7, "mom_pct": 15.5, "knowledge_date": "2026-10-10"}, ...]
    資料來源 MOPS t187ap05（TWMD 欄位單位為千元，這裡同時給元，與 FinMind 的「元」一致）。
    同一個月若有多列（修正公告）取 knowledge_date 最新者。查無代號會 raise，不回傳空 list。"""
    res = query_dataset("monthly_revenue", tickers=[str(ticker)], start=f"{since}-01", as_of=as_of,
                        max_age_hours=max_age_hours)
    if str(ticker) in res.missing:
        raise TwmdError(f"TWMD monthly_revenue 查無 {ticker}: {res.missing_reason.get(str(ticker), '無資料')}")
    best = {}
    for r in res.rows:
        ym = r.get("period")
        if not ym or ym < since or r.get("revenue") in (None, ""):
            continue
        if ym not in best or str(r.get("knowledge_date") or "") >= str(best[ym].get("knowledge_date") or ""):
            best[ym] = r

    def _f(v):
        return float(v) if v not in (None, "") else None

    out = [{"year_month": ym, "revenue": float(r["revenue"]) * 1000.0, "revenue_k": float(r["revenue"]),
            "yoy_pct": _f(r.get("revenue_yoy_pct")), "mom_pct": _f(r.get("revenue_mom_pct")),
            "knowledge_date": r.get("knowledge_date")} for ym, r in best.items()]
    out.sort(key=lambda x: x["year_month"])
    return out
