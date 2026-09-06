# -*- coding: utf-8 -*-
"""
建立個股月度/季度損益推估模型。

用法：
    python .agent/scripts/build_pnl_model.py 6213
    python .agent/scripts/build_pnl_model.py 6213 --price 517
    python .agent/scripts/build_pnl_model.py 31_Models/6213聯茂/params_v45.yaml

股價預設由 FinMind 即時抓取（meta.price_source: auto），避免寫死在參數檔而過期。

輸出（寫回同一個 31_Models/{代號}{名稱}/ 目錄）：
    output_{version}_quarterly.csv   季度損益表（各情境）
    output_{version}_monthly.csv     月度損益表（基準情境）
    模型摘要_{version}.md             人看的摘要：三情境、機率加權、稽核、失效條件
"""

import os
import sys
import glob
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml  # noqa: E402
from lib.pnl_model import (  # noqa: E402
    PnLModel, audit, crosscheck, calibration_check, write_csv,
)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(REPO, "31_Models")


def resolve_params_path(arg):
    if arg.endswith((".yaml", ".yml")):
        return arg if os.path.isabs(arg) else os.path.join(REPO, arg)
    hits = glob.glob(os.path.join(MODELS_DIR, f"{arg}*", "params_*.y*ml"))
    if not hits:
        raise SystemExit(f"找不到 {arg} 的參數檔（預期在 31_Models/{arg}*/params_*.yaml）")
    return sorted(hits)[-1]  # 取版本號最大的


def pct(x, digits=2):
    return f"{x * 100:.{digits}f}%"


def resolve_price(meta, cli_price=None):
    """
    股價優先序：CLI 指定 > FinMind 即時 > 參數檔 meta.price。
    寫死股價是 forward PE 最常見的錯誤來源（參數檔可能幾個月沒動）。
    """
    if cli_price is not None:
        return float(cli_price), "CLI 指定"
    if meta.get("price_source", "auto") == "auto" and meta.get("ticker"):
        try:
            from lib.stock_metrics import get_historical_prices_fallback
            prices = get_historical_prices_fallback(str(meta["ticker"]))
            if prices:
                return float(prices[-1]), "FinMind 即時收盤"
        except Exception as e:
            print(f"  [WARN] 股價自動抓取失敗，改用參數檔數值：{e}")
    p = meta.get("price")
    return (float(p), "參數檔 meta.price（可能已過期）") if p else (None, None)


def build(params_path, cli_price=None):
    with open(params_path, encoding="utf-8") as f:
        params = yaml.safe_load(f)

    model = PnLModel(params)
    meta = model.meta
    version = meta.get("version", "v1")
    outdir = os.path.dirname(params_path)

    price, price_src = resolve_price(meta, cli_price)
    meta["price"] = price
    meta["price_source_note"] = price_src

    # ---------------- 各情境 ----------------
    scenarios = model.scenarios or {"base": {"prob": 1.0}}
    if "base" not in scenarios:
        raise SystemExit("scenarios 必須包含 base（基準情境）")

    results = {}
    for name, spec in scenarios.items():
        rows = model.compute_layer1(spec.get("overrides"))
        results[name] = {
            "prob": spec.get("prob", 0.0),
            "label": spec.get("label", name),
            "quarterly": rows,
            "annual_eps": model.annual_eps(rows),
        }

    base_rows = results["base"]["quarterly"]
    monthly_rows = model.monthly(base_rows)

    # ---------------- 基期校準 ----------------
    calib = calibration_check(model, base_rows)

    # ---------------- Layer 2 交叉驗證 ----------------
    l2_rows = model.compute_layer2()
    cc = crosscheck(base_rows, l2_rows,
                    threshold=model.l2.get("crosscheck_threshold", 0.20))

    # ---------------- 機率加權 & rolling forward ----------------
    years = sorted({q[:4] for q in model.quarters})
    weighted = {}
    prob_sum = sum(r["prob"] for r in results.values())
    for y in years:
        weighted[y] = sum(r["annual_eps"].get(y, 0.0) * r["prob"]
                          for r in results.values())
        if prob_sum and abs(prob_sum - 1.0) > 1e-6:
            weighted[y] /= prob_sum

    fwd_eps, fwd_start, fwd_end = model.rolling_forward_eps(monthly_rows)
    fwd_pe = (price / fwd_eps) if (price and fwd_eps) else None

    aud = audit(model)

    # ---------------- 輸出 CSV ----------------
    q_all = []
    for name, r in results.items():
        for row in r["quarterly"]:
            row2 = dict(row)
            row2["scenario"] = name
            # 分部門營收攤平成欄位，方便直接看組合變化
            for dk, dv in (row.get("_drivers") or {}).items():
                if model.revenue_method == "segments":
                    row2[f"seg_{dk}"] = dv
            for ek, ev in (row.get("_equity") or {}).items():
                row2[f"eq_{ek}"] = ev
            row2.pop("_drivers", None)
            row2.pop("_equity", None)
            q_all.append(row2)
    q_all_sorted = sorted(q_all, key=lambda r: (r["scenario"], r["quarter"]))
    # 讓 scenario 欄位排在最前面
    ordered = []
    for r in q_all_sorted:
        o = {"scenario": r.pop("scenario")}
        o.update(r)
        ordered.append(o)

    q_csv = os.path.join(outdir, f"output_{version}_quarterly.csv")
    m_csv = os.path.join(outdir, f"output_{version}_monthly.csv")
    write_csv(q_csv, ordered)
    write_csv(m_csv, monthly_rows)

    # ---------------- 輸出 Markdown 摘要 ----------------
    md = render_markdown(model, params_path, results, weighted, monthly_rows,
                         l2_rows, cc, aud, fwd_eps, fwd_start, fwd_end, fwd_pe,
                         calib)
    md_path = os.path.join(outdir, f"模型摘要_{version}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[OK] {meta.get('name','')}({meta.get('ticker','')}) {version}")
    print(f"  季度表 : {os.path.relpath(q_csv, REPO)}")
    print(f"  月度表 : {os.path.relpath(m_csv, REPO)}")
    print(f"  摘要   : {os.path.relpath(md_path, REPO)}")
    print()
    for y in years:
        parts = " / ".join(
            f"{n}:{r['annual_eps'].get(y, 0.0):.2f}" for n, r in results.items())
        print(f"  {y} EPS  {parts}   機率加權 {weighted[y]:.2f}")
    if fwd_eps:
        print(f"  滾動12M EPS ({fwd_start}~{fwd_end}): {fwd_eps:.2f} 元", end="")
        print(f"  → forward PE {fwd_pe:.1f}x @ {price}元" if fwd_pe else "")
    bad = [c for c in calib if c["status"] != "OK"]
    if calib:
        print(f"  基期校準: {len(calib)-len(bad)}/{len(calib)} 項通過")
    for c in bad:
        print(f"  [WARN] 校準失敗 {c['quarter']} {c['field']}: "
              f"實際 {c['actual']} vs 模型 {c['model']:.4g} ({c['diff']})")
    for w in aud["warnings"]:
        print(f"  [WARN] {w}")
    for row in cc:
        if row["flag"] != "OK":
            print(f"  [WARN] {row['quarter']} Layer1/Layer2 差異: "
                  f"營收 {pct(row['revenue_diff_pct'])}, "
                  f"毛利率 {row['gross_margin_diff_pp']*100:+.1f}pp")
    return md_path


def render_markdown(model, params_path, results, weighted, monthly_rows,
                    l2_rows, cc, aud, fwd_eps, fwd_start, fwd_end, fwd_pe,
                    calib=None):
    meta = model.meta
    today = datetime.date.today().isoformat()
    years = sorted(weighted.keys())
    L = []
    a = L.append

    a(f"# {meta.get('name','')} ({meta.get('ticker','')}) 損益推估模型 {meta.get('version','')}")
    a("")
    a(f"> 產生日期：{today}｜參數檔：`{os.path.basename(params_path)}`"
      f"｜原型：{meta.get('archetype','')}｜基期：{meta.get('base_quarter','')}")
    a("")
    a("> [!WARNING]")
    a("> 本檔為引擎自動產出，**所有數字的可信度等於輸入參數的可信度**。")
    a("> 請先看「參數稽核」章節確認有多少假設是推估值，再看 EPS 數字。")
    a("")

    # 基期校準（放最前面：連已知的季度都算不準，後面所有數字都不用看）
    if calib:
        bad = [c for c in calib if c["status"] != "OK"]
        a("## ✅ 基期校準" + ("（**未通過**）" if bad else "（通過）"))
        a("")
        a("> 模型在已有實際財報的季度必須重現實績。若連上一季都對不上，")
        a("> 往前推的每一季都會帶著同一個系統性偏差。")
        a("")
        a("| 季別 | 項目 | 實際 | 模型 | 差異 | 判定 |")
        a("| :--- | :--- | ---: | ---: | ---: | :--- |")
        for c in calib:
            av = f"{c['actual']*100:.2f}%" if "率" in c["field"] else f"{c['actual']:.2f}"
            mv = f"{c['model']*100:.2f}%" if "率" in c["field"] else f"{c['model']:.2f}"
            a(f"| {c['quarter']} | {c['field']} | {av} | {mv} | {c['diff']} | {c['status']} |")
        a("")

    # 情境
    a("## 🎯 三情境與機率加權")
    a("")
    header = "| 情境 | 機率 | " + " | ".join(f"{y} EPS" for y in years) + " | 說明 |"
    a(header)
    a("| :--- | ---: | " + " | ".join("---:" for _ in years) + " | :--- |")
    for name, r in results.items():
        cells = " | ".join(f"{r['annual_eps'].get(y,0.0):.2f}" for y in years)
        a(f"| {r['label']} | {r['prob']*100:.0f}% | {cells} | "
          f"{model.scenarios.get(name,{}).get('note','')} |")
    cells = " | ".join(f"**{weighted[y]:.2f}**" for y in years)
    a(f"| **機率加權** | 100% | {cells} | — |")
    a("")

    # 共識對照
    cons = model.consensus or {}
    if cons.get("eps"):
        a("### 與法人共識對照")
        a("")
        a("| 年度 | 本模型(基準) | 法人共識 | 偏離 |")
        a("| :--- | ---: | ---: | ---: |")
        base_annual = results["base"]["annual_eps"]
        for y in years:
            c = cons["eps"].get(int(y)) or cons["eps"].get(y)
            if c is None:
                continue
            b = base_annual.get(y, 0.0)
            dev = (b - c) / c if c else 0.0
            flag = " 🚩" if abs(dev) > 0.30 else ""
            a(f"| {y} | {b:.2f} | {c:.2f} | {dev*100:+.0f}%{flag} |")
        a("")
        a(f"> 共識來源：{cons.get('source','（未註明）')}"
          f"｜資料日：{cons.get('as_of','—')}")
        a(">")
        a("> 🚩 標記代表偏離共識逾 30%。**偏離不等於錯**，但必須能說出共識隱含了什麼假設、"
          "而你為什麼認為那個假設會被推翻——說不出來就是模型在追價。")
        a("")

    # forward
    if fwd_eps:
        a("## 📈 交易用 Forward 估值")
        a("")
        a(f"* **滾動 12 個月 EPS**（{fwd_start} ~ {fwd_end}）：**{fwd_eps:.2f} 元**")
        if fwd_pe:
            a(f"* 現價 {meta.get('price')} 元 → **Forward P/E {fwd_pe:.1f}x**"
              f"　<sub>股價來源：{meta.get('price_source_note','')}</sub>")
        a("* 使用滾動 12 個月而非日曆年度，避免 forward PE 在跨年時跳空。")
        a("")

    # 季度表
    a("## 📊 季度損益表（基準情境）")
    a("")
    a("| 季別 | 營收(億) | 毛利率 | 營益(億) | 營益率 | 稅後淨利(億) | EPS(元) |")
    a("| :--- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in results["base"]["quarterly"]:
        a(f"| {r['quarter']} | {r['revenue']:.2f} | {pct(r['gross_margin'])} | "
          f"{r['op_income']:.2f} | {pct(r['op_margin'])} | "
          f"{r['net_income']:.2f} | {r['eps']:.2f} |")
    a("")

    # 權益法投資收益
    if model.investees:
        names = list(model.investees.keys())
        a("## 🏢 權益法投資收益（Look-through）")
        a("")
        dep = [r["nonop_dependency"] for r in results["base"]["quarterly"]]
        avg_dep = sum(dep) / len(dep) if dep else 0
        a("> [!WARNING]")
        a(f"> **業外貢獻平均佔稅後淨利 {avg_dep*100:.0f}%。**"
          f"這代表本模型的主要變數不是本業三率，而是下列被投資公司的獲利。")
        a("> 換句話說，替這家公司建模＝替它的轉投資建模；"
          "本業做得再細，也擋不住被投資公司獲利假設的誤差。")
        a("")
        a("| 季別 | " + " | ".join(f"{n}(億)" for n in names)
          + " | 權益法合計 | 其他業外 | 本業營益 | 業外依賴度 |")
        a("| :--- | " + " | ".join("---:" for _ in names) + " | ---: | ---: | ---: | ---: |")
        for r in results["base"]["quarterly"]:
            e = r.get("_equity") or {}
            vals = " | ".join(f"{e.get(n,0.0):.1f}" for n in names)
            a(f"| {r['quarter']} | {vals} | {r['equity_income']:.1f} | "
              f"{r['non_operating']:.1f} | {r['op_income']:.1f} | "
              f"{r['nonop_dependency']*100:.0f}% |")
        a("")
        for n in names:
            inv = model.investees[n]
            stake = inv["stake"].get(model.quarters[-1]).value
            a(f"* **{n}**（{inv['ticker']}）持股 {stake*100:.1f}%"
              + (f"　{inv['note']}" if inv["note"] else ""))
        a("")

    # 分部門營收（原型 B）
    if model.revenue_method == "segments":
        seg_names = list(model.segments.keys())
        a("## 🧩 產品組合與營收結構（基準情境）")
        a("")
        a("| 季別 | " + " | ".join(f"{s}(億)" for s in seg_names)
          + " | 合計 | " + " | ".join(f"{s}佔比" for s in seg_names) + " |")
        a("| :--- | " + " | ".join("---:" for _ in seg_names) + " | ---: | "
          + " | ".join("---:" for _ in seg_names) + " |")
        for r in results["base"]["quarterly"]:
            d = r.get("_drivers") or {}
            tot = r["revenue"]
            vals = " | ".join(f"{d.get(s,0.0):.2f}" for s in seg_names)
            shares_ = " | ".join(
                f"{(d.get(s,0.0)/tot*100 if tot else 0):.1f}%" for s in seg_names)
            a(f"| {r['quarter']} | {vals} | {tot:.2f} | {shares_} |")
        a("")
        for s in seg_names:
            note = model.segments[s].get("note")
            if note:
                a(f"* **{s}**：{note}")
        a("")

    # 月度表
    a("## 🗓️ 月度損益表（基準情境）")
    a("")
    a("> 月度數字由季度依 `month_weights` 拆分。**單月出貨時點噪音常達 ±10%**，")
    a("> 月度值的用途是與 MOPS 月營收對帳抓趨勢偏離，不是預測單月精確值。")
    a("")
    a("| 年月 | 營收(億) | 毛利(億) | 營益(億) | 稅後淨利(億) | EPS(元) |")
    a("| :--- | ---: | ---: | ---: | ---: | ---: |")
    for r in monthly_rows:
        a(f"| {r['year_month']} | {r['revenue']:.2f} | {r['gross_profit']:.2f} | "
          f"{r['op_income']:.2f} | {r['net_income']:.2f} | {r['eps']:.2f} |")
    a("")

    # Layer2
    a("## 🔬 Layer 1 vs Layer 2 交叉驗證")
    a("")
    if not model.layer2_enabled():
        a("Layer 2（產品組合拆解）**未啟用**。")
        a("")
        a("> 這不是缺陷。依設計原則，Layer 2 只有在你握有級距別的**一手資料**"
          "（公司親口給的各級距毛利率／實際組合佔比）時才值得開啟；")
        a("> 否則只是把「毛利率一個猜測」拆成「五個級距各自的猜測」，出錯的地方變多而非變少。")
    else:
        a("> Layer 2 的角色是**驗證** Layer 1，不是取代它。兩層差距過大時，")
        a("> 預設判定為 Layer 2 過擬合（參數多於可用觀測數），而非 Layer 2 較精確。")
        a("")
        a("| 季別 | L1營收 | L2營收 | 營收差異 | L1毛利率 | L2隱含毛利率 | 毛利率差 | 判定 |")
        a("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |")
        for r in cc:
            a(f"| {r['quarter']} | {r['l1_revenue']:.2f} | {r['l2_revenue']:.2f} | "
              f"{pct(r['revenue_diff_pct'])} | {pct(r['l1_gross_margin'])} | "
              f"{pct(r['l2_implied_gross_margin'])} | "
              f"{r['gross_margin_diff_pp']*100:+.1f}pp | {r['flag']} |")
    a("")

    # 稽核
    a("## 🔍 參數稽核")
    a("")
    c = aud["counts"]
    a(f"* Layer 1 參數 {aud['total_layer1']} 個"
      + (f"、Layer 2 參數 {aud['total_layer2']} 個" if aud['total_layer2'] else "")
      + f"，合計自由參數 **{aud['free_params']}** 個，涵蓋 {aud['n_quarters']} 季。")
    a(f"* 信心分布：硬 {c['硬']}｜軟 {c['軟']}｜反解 {c['反解']}｜**推估 {c['推估']}**")
    a("")
    if aud["warnings"]:
        for w in aud["warnings"]:
            a(f"> [!WARNING]")
            a(f"> {w}")
            a("")
    if aud["soft_list"]:
        a("### 需要一手資料補強的參數（軟／推估）")
        a("")
        a("| 參數 | 值 | 信心 | 來源 |")
        a("| :--- | ---: | :--- | :--- |")
        for name, val, conf, src in aud["soft_list"]:
            mark = "**推估**" if conf == "推估" else conf
            a(f"| `{name}` | {val} | {mark} | {src} |")
        a("")
        a("> 這張表就是**下次法說會/私訪的提問清單**。標記「推估」者代表沒有任何一手來源，")
        a("> 是模型最脆弱的環節——聯茂 v18 的 `α=0.90` 就是這類參數，"
          "後來被 0815 私訪拿到的級距毛利率直接取代。")
        a("")

    # 失效條件
    a("## ⛔ 失效條件 (Invalidation)")
    a("")
    if model.invalidation:
        for item in model.invalidation:
            a(f"* {item}")
    else:
        a("*（未設定——建議至少列出 3-5 條可量化、有明確查核日的失效條件）*")
    a("")
    a("> 模型的價值不在於預測準，而在於**知道自己什麼時候錯了**。"
      "每條失效條件都要可量化、有資料來源、有查核日期。")
    a("")

    a("---")
    a("")
    a(f"*本檔由 `.agent/scripts/build_pnl_model.py` 自動產生，請勿手動編輯；"
      f"要改數字請改 `{os.path.basename(params_path)}` 後重跑。*")
    return "\n".join(L)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    args = sys.argv[1:]
    cli_price = None
    if "--price" in args:
        i = args.index("--price")
        cli_price = float(args[i + 1])
        del args[i:i + 2]
    build(resolve_params_path(args[0]), cli_price)
