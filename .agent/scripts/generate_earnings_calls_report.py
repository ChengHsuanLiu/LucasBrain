"""
法說會時程報告產生器（`g EarningsCalls`），同時提供 `build_embedded_section()` 給盤後日報
（generate_daily_report.py）併入最後一節「七、法說會時程」。

獨立報告輸出至 `30_Projects/Earnings_Calls/`（.md + .pdf）。資料來自 fetch_earnings_calls.py 每日更新的
`.agent/data/earnings_calls.db`；產生報告時只讀資料庫、不連網（除非加 --refresh，或併入日報時資料超過
EMBED_REFRESH_HOURS 小時沒更新），所以報告頂端會標示資料最後更新時間，超過 36 小時未更新會警告。

報告內容（依閱讀優先順序）：
1. 追蹤個股（10_Stocks 已有個股頁者）未來 30 天的場次
2. 近 7 天異動（新增／改時間／改地點／簡報上傳／疑似取消），追蹤個股逐筆列出、其餘個股每類最多列 15 筆
3. 全市場未來 14 天的場次

用法：
    python generate_earnings_calls_report.py
    python generate_earnings_calls_report.py --days 21 --vault-days 45 --change-days 10
    python generate_earnings_calls_report.py --refresh      # 先執行一次 fetch_earnings_calls.py 再產生報告

註：PDF 轉換流程會移除所有 emoji（含 ★），所以追蹤個股在表格內用「◆」標示。
"""
import argparse
import contextlib
import io
import os
import sys
from collections import Counter
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.earnings_calls import (
    connect,
    last_success_run,
    load_vault_pages,
    query_changes,
    query_new_events,
    query_upcoming,
)
from lib.report_pdf import render_markdown_to_pdf, assemble_report

OUTPUT_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Earnings_Calls"

DEFAULT_DAYS = 14          # 全市場清單
DEFAULT_VAULT_DAYS = 30    # 追蹤個股清單
DEFAULT_CHANGE_DAYS = 7
STALE_HOURS = 36
EMBED_REFRESH_HOURS = 3    # 併入日報時，資料超過這麼久沒更新就先抓一次
LOCATION_MAX_CHARS = 46
OTHER_STOCK_CHANGE_CAP = 15

WEEKDAYS = "一二三四五六日"
KIND_TAG = {"券商論壇/研討會": "論壇", "海外路演(NDR)": "路演", "座談會": "座談"}
EMBED_CLASS = "earnings-calls"


def build_css(scope=""):
    """欄寬：日期時間(多日活動會換行)/個股/國內外/形式/主辦/地點。
    併入日報時 scope 傳 '.earnings-calls'，把規則限定在這一節，不影響日報其他表格。"""
    s = f"{scope} " if scope else ""
    return f"""
        {s}table {{ table-layout: fixed; font-size: 8pt; }}
        {s}th:nth-child(1), {s}td:nth-child(1) {{ width: 17%; }}
        {s}th:nth-child(2), {s}td:nth-child(2) {{ width: 15%; }}
        {s}th:nth-child(3), {s}td:nth-child(3) {{ width: 6%; text-align: center; }}
        {s}th:nth-child(4), {s}td:nth-child(4) {{ width: 8%; text-align: center; }}
        {s}th:nth-child(5), {s}td:nth-child(5) {{ width: 16%; }}
        {s}th:nth-child(6), {s}td:nth-child(6) {{ width: 38%; }}
        {s}th {{ padding: 5px 6px; }}
        {s}td {{ padding: 4px 6px; }}
"""


EARNINGS_CALLS_EXTRA_CSS = build_css()


def esc(text):
    return (text or "").replace("|", "\\|").replace("\n", " ")


def trunc(text, n=LOCATION_MAX_CHARS):
    text = (text or "").strip()
    return text if len(text) <= n else text[:n - 1] + "…"


def fmt_day(date_iso):
    d = date.fromisoformat(date_iso)
    return f"{d.month:02d}/{d.day:02d}({WEEKDAYS[d.weekday()]})"


def fmt_when(ev):
    day = fmt_day(ev["event_date"])
    if ev.get("event_end_date"):
        end = date.fromisoformat(ev["event_end_date"])
        day = f"{day[:5]}~{end.month:02d}/{end.day:02d}{day[5:]}"
    return f"{day} {ev['event_time'] or '--:--'}"


def stock_label(code, name, vault):
    """追蹤個股：粗體 + ◆ + wikilink（PDF 轉換時 wikilink 會被拿掉只留文字）；其餘個股純文字。"""
    page = vault.get(code)
    return f"**◆ [[{page}]]**" if page else f"{code} {name}"


def organizer_label(ev):
    org = ev["organizer"] or ev["organizer_type"]
    tag = KIND_TAG.get(ev["event_kind"])
    return f"{org}（{tag}）" if tag else org


def build_event_table(events, vault):
    lines = ["| 日期時間 | 個股 | 國內外 | 形式 | 主辦 | 地點 |",
             "| :--- | :--- | :---: | :---: | :--- | :--- |"]
    for ev in events:
        lines.append(f"| {fmt_when(ev)} | {stock_label(ev['stock_code'], ev['stock_name'], vault)} | {ev['scope']} | "
                     f"{ev['format']} | {esc(organizer_label(ev))} | {esc(trunc(ev['location']))} |")
    return lines


def collect_change_items(conn, today, days):
    """近 N 天異動 -> list of dict(detected, type, code, name, when, detail)，新到舊。"""
    items = []
    for ev in query_new_events(conn, days, today):
        items.append({"detected": ev["first_seen"], "type": "新增", "code": ev["stock_code"], "name": ev["stock_name"],
                      "when": fmt_when(ev), "detail": f"{ev['scope']}／{ev['format']}／{organizer_label(ev)}"})
    for c in query_changes(conn, days, today):
        if c["event_date"] < today.isoformat():
            continue  # 已召開的場次，改什麼都沒有行動價值
        field = c["field"]
        when = f"{fmt_day(c['event_date'])} {c['event_time'] or '--:--'}"
        if field == "status" and c["new_value"] == "missing":
            if c["status"] != "missing":
                continue  # 後來又恢復列出了
            ctype, detail = "疑似取消", "兩個來源都不再列出（未必真的取消，也可能改期或漏列）"
        elif field == "status":
            ctype, detail = "恢復列出", "先前疑似取消，來源又重新列出"
        elif field == "event_time":
            ctype, detail = "改時間", f"{c['old_value'] or '--:--'} → {c['new_value'] or '--:--'}"
        elif field == "location":
            ctype, detail = "改地點", f"{trunc(c['old_value'], 24)} → {trunc(c['new_value'], 24)}"
        elif field == "event_end_date":
            ctype, detail = "改日期區間", f"結束日 {c['old_value'] or '無'} → {c['new_value'] or '無'}"
        elif field == "summary":
            ctype, detail = "摘要更新", "公司更新了公告內容"
        elif field == "materials":
            ctype, detail = "簡報上傳", "已上傳法說會簡報"
        elif field == "scope":
            ctype, detail = "國內外更正", f"{c['old_value']} → {c['new_value']}"
        else:
            continue
        items.append({"detected": c["changed_at"], "type": ctype, "code": c["stock_code"], "name": c["stock_name"],
                      "when": when, "detail": detail})
    items.sort(key=lambda i: i["detected"], reverse=True)
    return items


def change_bullet(it, vault):
    stamp = datetime.fromisoformat(it["detected"])
    return (f"- **{it['type']}**　{it['when']}　{stock_label(it['code'], it['name'], vault)}　"
            f"{esc(it['detail'])}　（{stamp.month}/{stamp.day} 偵測）")


def build_changes_section(items, vault, sub="###"):
    """sub: 子標題的 # 數（獨立報告 '###'，併入日報時再深一層）。"""
    if not items:
        return ["（無）"]
    lines = []
    counts = Counter(i["type"] for i in items)
    lines.append("　".join(f"{k} {v}" for k, v in counts.most_common()))
    lines.append("")

    mine = [i for i in items if i["code"] in vault]
    others = [i for i in items if i["code"] not in vault]
    lines += [f"{sub} 追蹤個股", ""]
    lines += [change_bullet(i, vault) for i in mine] or ["（無）"]
    lines += ["", f"{sub} 其他個股", ""]
    if not others:
        lines.append("（無）")
    for ctype in dict.fromkeys(i["type"] for i in others):  # 依首次出現順序
        group = [i for i in others if i["type"] == ctype]
        lines += [change_bullet(i, vault) for i in group[:OTHER_STOCK_CHANGE_CAP]]
        if len(group) > OTHER_STOCK_CHANGE_CAP:
            lines.append(f"- 　（「{ctype}」另有 {len(group) - OTHER_STOCK_CHANGE_CAP} 筆未列出）")
    return lines


def gather(conn, today, days, vault_days, change_days):
    """從資料庫取出報告需要的全部資料。"""
    vault = load_vault_pages()
    updated = last_success_run(conn)
    stale = updated is None or (datetime.now() - datetime.fromisoformat(updated)).total_seconds() > STALE_HOURS * 3600
    return {
        "vault": vault, "updated": updated, "stale": stale,
        "all_events": query_upcoming(conn, days=days, today=today),
        "vault_events": [e for e in query_upcoming(conn, days=vault_days, today=today) if e["stock_code"] in vault],
        "changes": collect_change_items(conn, today, change_days),
    }


def summary_line(d, days, vault_days):
    updated = d["updated"].replace("T", " ") if d["updated"] else "未知"
    return (f"（全市場未來 {days} 天共 {len(d['all_events'])} 場；追蹤個股未來 {vault_days} 天共 {len(d['vault_events'])} 場；"
            f"資料更新於 {updated}）")


def stale_warning():
    return (f"**注意：資料已超過 {STALE_HOURS} 小時未成功更新，以下內容可能過期。"
            f"請先執行 `python .agent/scripts/fetch_earnings_calls.py`（或加 `--refresh` 重新產生報告）。**")


def build_sections(d, days, vault_days, change_days, heading="##"):
    """三個內容區塊。heading：區塊標題的 # 數（獨立報告 '##'，併入日報時 '####'）。"""
    sub = heading + "#"
    body = [f"{heading} 追蹤個股（未來 {vault_days} 天，共 {len(d['vault_events'])} 場）", ""]
    body += build_event_table(d["vault_events"], d["vault"]) if d["vault_events"] else ["（無）"]
    body += ["", f"{heading} 近 {change_days} 天異動", ""]
    body += build_changes_section(d["changes"], d["vault"], sub=sub)
    body += ["", f"{heading} 全市場時程（未來 {days} 天，共 {len(d['all_events'])} 場）", ""]
    body += build_event_table(d["all_events"], d["vault"]) if d["all_events"] else ["（無）"]
    return body


def build_legend():
    return ("*◆ = 10_Stocks 已有該個股頁。「疑似取消」是推論（來源不再列出，不代表一定取消）。"
            "國內外以 Yahoo 為準；主辦與形式是依公告文字的規則判斷，約 6% 的場次主辦為「未明」（公告本身沒寫或規則不猜）。"
            "主辦欄的「論壇／路演／座談」表示該場不是公司自己的法說會。*")


def build_note_block():
    return ["> [!NOTE]",
            "> 本報告由 `generate_earnings_calls_report.py` 讀取 `.agent/data/earnings_calls.db` 產生；資料庫由排程 "
            "`LucasBrain_EarningsCalls` 每天 18:30 執行 `fetch_earnings_calls.py` 更新（Yahoo 股市行事曆 + 臺灣指數公司 IR 議合平台，取聯集）。"
            "資料來源取捨、資料表與已知限制見 `.agent/tasks/fetch_earnings_calls.md`。"
            "排程是否正常請執行 `python .agent/scripts/fetch_earnings_calls.py --status`。"]


def _refresh_database():
    """執行一次每日抓取，輸出不顯示（併入日報時避免洗版）。回傳是否沒有任何來源失敗。"""
    from fetch_earnings_calls import run_daily
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return run_daily(dry_run=False) == 0


def build_embedded_section(today=None, days=DEFAULT_DAYS, vault_days=DEFAULT_VAULT_DAYS,
                           change_days=DEFAULT_CHANGE_DAYS, heading_number="七"):
    """
    併入盤後日報的「七、法說會時程」。回傳 (lines, css)。

    - 資料超過 EMBED_REFRESH_HOURS 小時沒更新就先抓一次（日報 16:30 跑、資料庫 18:30 才更新，
      不先更新會拿到前一晚的資料）。抓取失敗不阻擋日報，沿用既有資料，過期由頂端警告提示。
    - 任何例外都不往外丟：法說會區塊壞掉最多是日報裡這一節顯示「本次略過」，不能拖垮日報其他六節。
    """
    title = f"### {heading_number}、法說會時程"
    try:
        today = today or date.today()
        conn = connect()
        updated = last_success_run(conn)
        conn.close()
        age_h = (datetime.now() - datetime.fromisoformat(updated)).total_seconds() / 3600 if updated else None
        if age_h is None or age_h > EMBED_REFRESH_HOURS:
            try:
                ok = _refresh_database()
                print("法說會資料庫已更新" + ("" if ok else "（有來源失敗，沿用既有資料）"))
            except Exception as e:  # noqa: BLE001
                print(f"Warning: 法說會資料庫更新失敗，沿用既有資料: {e}")

        conn = connect()
        if conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
            return [title, "", "*（法說會資料庫是空的，請先執行 `python .agent/scripts/fetch_earnings_calls.py --backfill 2026-01`）*"], ""
        d = gather(conn, today, days, vault_days, change_days)
        lines = [title, "", f"*{summary_line(d, days, vault_days)}*", ""]
        if d["stale"]:
            lines += [stale_warning(), ""]
        lines += [f'<div class="{EMBED_CLASS}" markdown="1">', ""]
        lines += build_sections(d, days, vault_days, change_days, heading="####")
        lines += ["", build_legend(), "", "</div>", ""]
        return lines, build_css(f".{EMBED_CLASS}")
    except Exception as e:  # noqa: BLE001
        print(f"Warning: 法說會時程區塊產生失敗，已略過: {e}")
        return [title, "", f"*（法說會時程區塊產生失敗，本次略過：{e}）*", ""], ""


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="法說會時程報告")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--vault-days", type=int, default=DEFAULT_VAULT_DAYS)
    parser.add_argument("--change-days", type=int, default=DEFAULT_CHANGE_DAYS)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    if args.refresh:
        from fetch_earnings_calls import run_daily
        print("先更新資料庫...")
        run_daily(dry_run=False)

    today = date.today()
    conn = connect()
    if conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
        print("資料庫是空的，請先執行 python .agent/scripts/fetch_earnings_calls.py --backfill 2026-01")
        sys.exit(1)

    d = gather(conn, today, args.days, args.vault_days, args.change_days)
    print(f"全市場 {len(d['all_events'])} 場（{args.days} 天）、追蹤個股 {len(d['vault_events'])} 場（{args.vault_days} 天）、"
          f"異動 {len(d['changes'])} 筆（{args.change_days} 天）；資料更新於 {d['updated']}{'（已過期）' if d['stale'] else ''}")

    body = build_sections(d, args.days, args.vault_days, args.change_days, heading="##")
    body += ["", "---", "", build_legend()]

    title_block = ["# 宇宙資本 法說會時程", "", f"**{today.strftime('%Y-%m-%d')}**", "",
                   summary_line(d, args.days, args.vault_days)]
    if d["stale"]:
        title_block += ["", stale_warning()]
    frontmatter = ["---", "type: earnings_calls_schedule", f"date: {today.strftime('%Y-%m-%d')}",
                   "author: LucasBrain AI", "tags: [report/earnings-calls]", "---", ""]
    md_lines, pdf_lines = assemble_report(title_block, body, note_block=build_note_block())
    md_lines = frontmatter + md_lines

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stem = f"{today.strftime('%Y%m%d')}_宇宙資本_法說會時程"
    out_path = os.path.join(OUTPUT_DIR, f"{stem}.md")
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Generated earnings calls report at: {out_path}")

    try:
        render_markdown_to_pdf(pdf_lines, OUTPUT_DIR, stem, extra_css=EARNINGS_CALLS_EXTRA_CSS)  # 自己會印出 PDF 路徑
    except Exception as e:
        print(f"Warning: Failed to generate PDF: {e}")


if __name__ == "__main__":
    main()
