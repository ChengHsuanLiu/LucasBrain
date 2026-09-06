# -*- coding: utf-8 -*-
"""
模型對帳（Backtest）：把模型的月度預估與 MOPS 實際月營收逐月比對。

用法：
    python .agent/scripts/backtest_model.py 6213
    python .agent/scripts/backtest_model.py 6213 --quiet      # 只輸出警訊

這是整套系統的「回顧迴圈」。模型的價值不在預測準，而在**知道自己什麼時候錯了**；
本腳本每次執行都會把結果追加寫入 backtest_log.md，讓誤差軌跡累積成可檢視的紀錄，
而不是每季悄悄 re-base。

判定規則（可於 params.yaml 的 backtest 區塊覆寫）：
    monthly_tolerance   單月偏離容忍度，預設 10%（單月出貨時點噪音本來就大）
    consecutive_alert   連續幾個月超標即示警，預設 2
"""

import os
import sys
import csv
import io
import glob
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(REPO, "31_Models")


def resolve_model_dir(arg):
    if os.path.isdir(arg):
        return arg
    hits = glob.glob(os.path.join(MODELS_DIR, f"{arg}*"))
    hits = [h for h in hits if os.path.isdir(h)]
    if not hits:
        raise SystemExit(f"找不到 {arg} 的模型目錄（預期在 31_Models/{arg}*）")
    return hits[0]


def latest(pattern, d):
    hits = sorted(glob.glob(os.path.join(d, pattern)))
    if not hits:
        raise SystemExit(f"{d} 內找不到 {pattern}")
    return hits[-1]


def fetch_actual_monthly(ticker):
    """FinMind TaiwanStockMonthRevenue → {'2026-07': 47.49(億元), ...}"""
    from lib.momentum_screen import fetch_revenue_history
    out = {}
    for r in fetch_revenue_history(str(ticker)):
        key = f"{r['revenue_year']}-{r['revenue_month']:02d}"
        out[key] = r["revenue"] / 1e8      # 元 → 億元
    return out


def run(model_dir, quiet=False):
    params_path = latest("params_*.y*ml", model_dir)
    with open(params_path, encoding="utf-8") as f:
        params = yaml.safe_load(f)
    meta = params.get("meta", {})
    ticker = str(meta.get("ticker", ""))
    version = meta.get("version", "v1")
    bt = params.get("backtest", {}) or {}
    tol = bt.get("monthly_tolerance", 0.10)
    consec_alert = bt.get("consecutive_alert", 2)

    monthly_csv = os.path.join(model_dir, f"output_{version}_monthly.csv")
    if not os.path.exists(monthly_csv):
        raise SystemExit(f"找不到 {monthly_csv}，請先執行 build_pnl_model.py")
    with io.open(monthly_csv, encoding="utf-8-sig") as f:
        model_rows = list(csv.DictReader(f))
    model_map = {r["year_month"]: float(r["revenue"]) for r in model_rows}

    actual = fetch_actual_monthly(ticker)

    compare = []
    for ym in sorted(set(model_map) & set(actual)):
        m, a = model_map[ym], actual[ym]
        dev = (m - a) / a if a else 0.0
        compare.append({
            "year_month": ym, "model": m, "actual": a, "dev": dev,
            "over": abs(dev) > tol,
        })

    # 連續超標偵測（只看最近一段）
    streak, streak_dir = 0, None
    for row in reversed(compare):
        if not row["over"]:
            break
        d = "高估" if row["dev"] > 0 else "低估"
        if streak_dir is None:
            streak_dir = d
        elif d != streak_dir:
            break
        streak += 1

    alerts = []
    if streak >= consec_alert:
        recent = compare[-streak:]
        avg = sum(r["dev"] for r in recent) / streak
        alerts.append(
            f"模型連續 {streak} 個月{streak_dir}（平均偏離 {avg*100:+.1f}%，"
            f"容忍度 ±{tol*100:.0f}%）→ 觸發參數檢討："
            f"{'稼動率/ASP 假設可能偏高' if streak_dir == '高估' else '稼動率/ASP 假設可能偏保守'}"
        )

    # 季度累計對照（只比對已有完整月份的季）
    q_cmp = []
    by_q = {}
    for r in model_rows:
        by_q.setdefault(r["quarter"], []).append(r["year_month"])
    for q, yms in sorted(by_q.items()):
        if not all(ym in actual for ym in yms):
            continue
        m = sum(model_map[ym] for ym in yms)
        a = sum(actual[ym] for ym in yms)
        q_cmp.append({"quarter": q, "model": m, "actual": a,
                      "dev": (m - a) / a if a else 0.0})

    write_log(model_dir, meta, compare, q_cmp, alerts, tol, streak, streak_dir)

    if not quiet:
        print(f"[對帳] {meta.get('name','')}({ticker}) {version}"
              f"　容忍度 ±{tol*100:.0f}%")
        print()
        print("  年月        模型(億)   實際(億)   偏離")
        for r in compare:
            flag = "  ⚠️" if r["over"] else ""
            print(f"  {r['year_month']}   {r['model']:8.2f}   {r['actual']:8.2f}   "
                  f"{r['dev']*100:+6.1f}%{flag}")
        if q_cmp:
            print()
            print("  季別      模型(億)   實際(億)   偏離")
            for r in q_cmp:
                print(f"  {r['quarter']}  {r['model']:8.2f}   {r['actual']:8.2f}   "
                      f"{r['dev']*100:+6.1f}%")
    print()
    if alerts:
        for al in alerts:
            print(f"  [ALERT] {al}")
    else:
        print("  [OK] 未觸發連續偏離警示")
    print(f"  紀錄已追加：{os.path.relpath(os.path.join(model_dir, 'backtest_log.md'), REPO)}")
    return compare, alerts


def write_log(model_dir, meta, compare, q_cmp, alerts, tol, streak, streak_dir):
    path = os.path.join(model_dir, "backtest_log.md")
    new = not os.path.exists(path)
    today = datetime.date.today().isoformat()
    L = []
    a = L.append
    if new:
        a(f"# {meta.get('name','')} ({meta.get('ticker','')}) 模型對帳紀錄")
        a("")
        a("> 每次執行 `backtest_model.py` 自動追加。**本檔只增不刪**——")
        a("> 誤差軌跡本身就是資訊，悄悄 re-base 會讓模型永遠學不會東西。")
        a("")
        a("---")
        a("")
    a(f"## {today}　對帳（模型 {meta.get('version','')}）")
    a("")
    a("| 年月 | 模型(億) | 實際(億) | 偏離 |")
    a("| :--- | ---: | ---: | ---: |")
    for r in compare:
        flag = " ⚠️" if r["over"] else ""
        a(f"| {r['year_month']} | {r['model']:.2f} | {r['actual']:.2f} | "
          f"{r['dev']*100:+.1f}%{flag} |")
    a("")
    if q_cmp:
        a("**季度累計**")
        a("")
        a("| 季別 | 模型(億) | 實際(億) | 偏離 |")
        a("| :--- | ---: | ---: | ---: |")
        for r in q_cmp:
            a(f"| {r['quarter']} | {r['model']:.2f} | {r['actual']:.2f} | "
              f"{r['dev']*100:+.1f}% |")
        a("")
    if alerts:
        a("> [!WARNING]")
        for al in alerts:
            a(f"> {al}")
        a("")
        a("**待辦**：檢討上述參數並升版；若決定不改，須在此記錄不改的理由。")
    else:
        a(f"未觸發警示（最近連續超標 {streak} 個月"
          f"{('，方向：' + streak_dir) if streak_dir else ''}，門檻 ±{tol*100:.0f}%）。")
    a("")
    a("---")
    a("")
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    args = [x for x in sys.argv[1:] if x != "--quiet"]
    run(resolve_model_dir(args[0]), quiet="--quiet" in sys.argv)
