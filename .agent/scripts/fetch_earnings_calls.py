"""
法說會時程：每日抓取 + 查詢。

用法：
    python fetch_earnings_calls.py                      # 每日排程用：抓 Yahoo + IR 議合平台(本月起共3個月)，更新資料庫
    python fetch_earnings_calls.py --dry-run            # 只抓取+解析並印出統計，不寫資料庫
    python fetch_earnings_calls.py --backfill 2026-01   # 回補歷史：IR 從該月逐月抓、Yahoo 逐週抓（不做「疑似取消」判定）
    python fetch_earnings_calls.py --show               # 查詢未來14天場次 (★=10_Stocks 已有個股頁)
    python fetch_earnings_calls.py --show --days 45 --vault-only
    python fetch_earnings_calls.py --show --ticker 2330 # 單一個股：列出該公司所有場次，含摘要/簡報連結
    python fetch_earnings_calls.py --changes --days 7   # 近N天的異動(改時間/改地點/簡報上傳/疑似取消...)
    python fetch_earnings_calls.py --status             # 兩個來源最近的抓取結果 + 健康檢查（排程出問題先看這個）
    python fetch_earnings_calls.py --rederive           # 改進 regex 規則後，用已存文字重算推導欄位（不連網、不洗掉異動歷史）

資料庫：.agent/data/earnings_calls.db（SQLite，不進 git）。設計與來源取捨見 lib/earnings_calls.py 檔頭。
結束碼：任一來源抓取失敗為 1（讓 Task Scheduler 的「上次執行結果」看得到；成功的來源仍會照常寫入）。
注意：scheduled_logs 內的中文會是亂碼（run_scheduled_report.ps1 以 Big5 解碼 Python 的 UTF-8 輸出，既有排程同樣如此），
排程結果請用 --status 查。
"""
import argparse
import calendar
import json
import os
import sys
import time
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.earnings_calls import (
    apply_events,
    connect,
    count_known_future,
    fetch_ir_month,
    fetch_yahoo,
    format_event_line,
    guess_rescheduled,
    load_vault_tickers,
    log_fetch_run,
    material_gap_days,
    merge_observations,
    query_changes,
    query_upcoming,
    rederive_all,
    REQUEST_INTERVAL_SEC,
)

IR_MONTHS_AHEAD = 2          # 本月 + 往後2個月
MAX_SKIP_RATIO = 0.2         # 解析略過的列超過此比例 → 視為頁面改版，該來源判定失敗
MIN_COUNT_RATIO = 0.3        # 本次筆數低於「資料庫已知」的此比例 → 不用該來源判定「疑似取消」
VAULT_HIGHLIGHT_DAYS = 14


def month_starts(first, last):
    """first/last 為 date，回傳涵蓋範圍內每個月的 (year, month)。"""
    y, m = first.year, first.month
    while (y, m) <= (last.year, last.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def collect_yahoo():
    rows, skipped = fetch_yahoo()
    window = (min(r["event_date"] for r in rows), max(r["event_date"] for r in rows)) if rows else None
    return rows, skipped, window


def collect_ir(first_month, last_month):
    rows, skipped = [], 0
    for y, m in month_starts(first_month, last_month):
        r, s = fetch_ir_month(y, m)
        rows += r
        skipped += s
        time.sleep(REQUEST_INTERVAL_SEC)
    last_day = calendar.monthrange(last_month.year, last_month.month)[1]
    window = (first_month.replace(day=1).isoformat(), last_month.replace(day=last_day).isoformat())
    return rows, skipped, window


def run_source(name, collector, conn, today, now):
    """
    執行單一來源的抓取並檢查合理性。回傳 (rows, coverage_window | None, error | None)。
    coverage_window 只在「抓取成功且筆數合理」時才回傳，供「疑似取消」判定使用。
    """
    try:
        rows, skipped, window = collector()
        if not rows:
            raise RuntimeError("解析結果為 0 筆（頁面改版或被擋？）")
        if skipped > max(3, MAX_SKIP_RATIO * (len(rows) + skipped)):
            raise RuntimeError(f"{skipped} 列解析失敗 / 共 {len(rows) + skipped} 列（頁面結構可能改版）")
    except Exception as e:  # noqa: BLE001
        if conn:
            log_fetch_run(conn, now, name, None, False, 0, 0, str(e))
        return [], None, str(e)

    coverage = window
    if conn:
        future_rows = sum(1 for r in rows if r["event_date"] >= today.isoformat())
        known = count_known_future(conn, name, today)
        if known >= 10 and future_rows < MIN_COUNT_RATIO * known:
            print(f"⚠️ {name}: 本次僅 {future_rows} 筆未來場次，資料庫已知 {known} 筆 → "
                  f"不用此來源判定『疑似取消』", file=sys.stderr)
            coverage = None
        log_fetch_run(conn, now, name, window, True, len(rows), skipped)
    return rows, coverage, None


def print_result(result, vault, today, rows_by_source, errors):
    print(f"\n=== 法說會時程更新結果 ({today}) ===")
    print("來源筆數: " + "、".join(f"{k} {n}" for k, n in rows_by_source.items()))
    print(f"新增 {len(result['new'])}　異動 {len(result['changed'])}　改時間 {len(result['retimed'])}　"
          f"疑似取消 {len(result['missing'])}　恢復列出 {len(result['restored'])}")
    for src, err in errors.items():
        print(f"❌ {src} 抓取失敗: {err}")

    def section(title, evs, show):
        if evs:
            print(f"\n[{title}]")
            for ev in evs:
                print("  " + show(ev))

    line = lambda ev: format_event_line(ev, vault)  # noqa: E731
    section("新增", sorted(result["new"], key=lambda e: (e["event_date"], e["stock_code"])), line)
    section("改時間", result["retimed"],
            lambda e: f"{e['stock_code']} {e['stock_name']} {e['event_date']} {e['old_time'] or '--'} → {e['event_time'] or '--'}")
    section("其他異動", result["changed"],
            lambda e: f"{e['stock_code']} {e['stock_name']} {e['event_date']} 欄位: " + "、".join(c[0] for c in e["changes"]))
    section("疑似取消（先前列出、這次所有可查來源都沒列）", result["missing"], line)
    resched = guess_rescheduled(result)
    section("疑似改期（同一檔同時『新增』與『疑似取消』）", resched,
            lambda t: f"{t[0]} {t[1]}: {t[2]} → {t[3]}")

    soon = [ev for ev in result["new"] if ev["stock_code"] in vault and
            ev["event_date"] <= (today + timedelta(days=VAULT_HIGHLIGHT_DAYS)).isoformat()]
    if soon:
        print(f"\n★ 你追蹤的個股，{VAULT_HIGHLIGHT_DAYS}天內新增的場次:")
        for ev in soon:
            print("  " + line(ev))


def run_daily(dry_run):
    today, now = date.today(), datetime.now().isoformat(timespec="seconds")
    conn = None if dry_run else connect()
    last_month = (today.replace(day=1) + timedelta(days=32 * IR_MONTHS_AHEAD)).replace(day=1)

    observations, coverage, errors, counts = [], {}, {}, {}
    for name, collector in (("yahoo", collect_yahoo),
                            ("ir", lambda: collect_ir(today.replace(day=1), last_month))):
        rows, window, err = run_source(name, collector, conn, today, now)
        counts[name] = len(rows)
        observations += rows
        if err:
            errors[name] = err
        elif window:
            coverage[name] = window
        time.sleep(REQUEST_INTERVAL_SEC)

    events = merge_observations(observations)
    if dry_run:
        print(f"[dry-run] 來源筆數 {counts}，合併後 {len(events)} 場；錯誤: {errors or '無'}")
        for ev in sorted(events, key=lambda e: (e["event_date"], e["event_time"]))[:15]:
            print("  " + format_event_line(dict(ev, status="active"), load_vault_tickers()))
        return 1 if errors else 0

    result = apply_events(conn, events, coverage, today, now)
    print_result(result, load_vault_tickers(), today, counts, errors)
    return 1 if errors else 0


def run_backfill(start_ym):
    today, now = date.today(), datetime.now().isoformat(timespec="seconds")
    start = datetime.strptime(start_ym, "%Y-%m").date()
    conn = connect()
    last_month = (today.replace(day=1) + timedelta(days=32 * IR_MONTHS_AHEAD)).replace(day=1)
    observations, errors, counts = [], {}, {}

    rows, _, err = run_source("ir", lambda: collect_ir(start, last_month), conn, today, now)
    counts["ir"], observations = len(rows), observations + rows
    if err:
        errors["ir"] = err

    def yahoo_weeks():
        out, skipped, d = [], 0, start
        while d <= today:
            r, s = fetch_yahoo(d)
            out += r
            skipped += s
            d += timedelta(days=7)
            time.sleep(REQUEST_INTERVAL_SEC)
        return out, skipped, (min(r["event_date"] for r in out), max(r["event_date"] for r in out)) if out else None

    rows, _, err = run_source("yahoo", yahoo_weeks, conn, today, now)
    counts["yahoo"], observations = len(rows), observations + rows
    if err:
        errors["yahoo"] = err

    result = apply_events(conn, merge_observations(observations), {}, today, now, track_missing=False)
    print(f"回補完成: 來源筆數 {counts}；新增 {len(result['new'])} 場、更新 {len(result['changed']) + len(result['retimed'])} 場")
    for src, e in errors.items():
        print(f"❌ {src}: {e}")
    return 1 if errors else 0


def run_show(days, ticker, vault_only):
    conn = connect()
    vault = load_vault_tickers()
    if ticker:  # 單一個股：不限天數，列出該公司全部場次
        events = [dict(r) for r in conn.execute(
            "SELECT * FROM events WHERE stock_code = ? ORDER BY event_date, event_time", (ticker,))]
    else:
        events = query_upcoming(conn, days=days, include_missing=True)
    if vault_only:
        events = [e for e in events if e["stock_code"] in vault]
    if not events:
        print("查無場次。")
        return 0
    for ev in events:
        print(format_event_line(ev, vault))
        if ticker:
            print(f"    摘要: {ev['summary']}")
            if ev["period_hint"]:
                print(f"    摘要提及期別: {ev['period_hint']}")
            if ev["webcast_url"]:
                print(f"    線上連結: {ev['webcast_url']}")
            for m in json.loads(ev["materials"] or "[]"):
                gap = material_gap_days(ev["event_date"], m["file"])
                # 會前 0~10 天上傳屬正常；差距過大代表可能是這家公司上一份簡報被掛錯場次
                warn = f"  ⚠檔案上傳日距場次 {gap} 天，可能不是這場的簡報" if gap is not None and (gap > 10 or gap < -3) else ""
                print(f"    簡報({m['lang'] or '?'}): {m['url']}{warn}")
    print(f"\n共 {len(events)} 場")
    return 0


def run_status(limit=8):
    """每個來源最近幾次抓取結果 + 健康檢查。資料來自 fetch_runs（UTF-8 存入資料庫，
    不受 Task Scheduler 日誌編碼影響，排程失敗時優先看這裡）。"""
    conn = connect()
    total, upcoming = conn.execute(
        "SELECT COUNT(*), SUM(event_date >= ?) FROM events", (date.today().isoformat(),)).fetchone()
    print(f"資料庫: {total} 場（未來 {upcoming or 0} 場）\n")
    stale = False
    for source in ("yahoo", "ir"):
        runs = conn.execute("SELECT * FROM fetch_runs WHERE source = ? ORDER BY run_id DESC LIMIT ?", (source, limit)).fetchall()
        print(f"[{source}] 最近 {len(runs)} 次:")
        for r in runs:
            status = "OK  " if r["ok"] else "FAIL"
            tail = f"  {r['error']}" if r["error"] else ""
            print(f"  {r['run_at']}  {status} 筆數={r['n_rows']} 略過={r['n_skipped']}{tail}")
        last_ok = conn.execute("SELECT run_at FROM fetch_runs WHERE source = ? AND ok = 1 ORDER BY run_id DESC LIMIT 1", (source,)).fetchone()
        if not last_ok:
            print(f"  ⚠️ {source} 從未成功抓取過")
            stale = True
        else:
            age_h = (datetime.now() - datetime.fromisoformat(last_ok["run_at"])).total_seconds() / 3600
            if age_h > 36:  # 每天跑一次，超過 36 小時沒成功代表排程沒跑或來源壞了
                print(f"  ⚠️ {source} 已 {age_h:.0f} 小時沒有成功抓取")
                stale = True
        print()
    print("健康檢查: " + ("❌ 有來源過期或失敗" if stale else "✅ 兩個來源近期皆成功"))
    return 1 if stale else 0


def run_changes(days):
    conn = connect()
    changes = query_changes(conn, days=days)
    if not changes:
        print(f"近 {days} 天無異動紀錄。")
        return 0
    for c in changes:
        old, new = (c["old_value"] or "")[:40], (c["new_value"] or "")[:40]
        print(f"{c['changed_at']}  {c['stock_code']} {c['stock_name']} ({c['event_date']} {c['event_time']})  "
              f"{c['field']}: {old} → {new}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="法說會時程每日抓取 / 查詢", usage=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backfill", metavar="YYYY-MM")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--changes", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--rederive", action="store_true")
    parser.add_argument("--days", type=int)
    parser.add_argument("--ticker")
    parser.add_argument("--vault-only", action="store_true")
    a = parser.parse_args()

    if a.show:
        sys.exit(run_show(a.days or 14, a.ticker, a.vault_only))
    if a.changes:
        sys.exit(run_changes(a.days or 7))
    if a.status:
        sys.exit(run_status())
    if a.rederive:
        print(f"已重算推導欄位的場次數: {rederive_all(connect())}")
        sys.exit(0)
    if a.backfill:
        sys.exit(run_backfill(a.backfill))
    sys.exit(run_daily(a.dry_run))
