# -*- coding: utf-8 -*-
"""
建模前診斷：這家公司的 EPS 變異來自哪裡？該用哪種模型結構？

用法：
    python .agent/scripts/diagnose_model.py 1303
    python .agent/scripts/diagnose_model.py 6213 6805 1303   # 可一次多檔對照

為什麼需要這一步
----------------
不同公司需要不同的模型結構，但這不是憑感覺選的。核心原則只有一條：

    **模型結構要對準「變異數最大的地方」，其餘保持簡單。**

把細節花在低變異的環節（例如替一家獲利八成來自轉投資的公司細拆本業產品組合），
不會讓模型更準，只會讓它更難維護、更容易過擬合。

本腳本用近 N 季財報做「稅前淨利變異來源拆解」，把 ΔPretax 精確分解為：
    營收效應   = Δ營收 × 前期營益率
    毛利率效應 = 前期營收 × Δ毛利率
    費用率效應 = −前期營收 × Δ費用率
    交乘項     = Δ營收 × Δ營益率
    業外效應   = Δ業外（含權益法投資收益）
（上述五項加總恆等於 Δ稅前淨利，非近似）

再據此建議模型原型與情境軸。
"""

import os
import sys
import statistics
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.financial_screen import _fetch_raw_financials  # noqa: E402

FIELDS = {
    "Revenue", "GrossProfit", "OperatingIncome",
    "TotalNonoperatingIncomeAndExpense", "PreTaxIncome",
    "IncomeAfterTaxes", "EPS", "TAX",
}
YI = 1e8  # 元 → 億元


def load_quarters(ticker, n=9):
    raw = _fetch_raw_financials(ticker)
    by_date = {}
    for r in raw.get("financials", []):
        if r.get("type") in FIELDS and r.get("value") is not None:
            by_date.setdefault(r["date"], {})[r["type"]] = r["value"]
    out = []
    for d in sorted(by_date):
        v = by_date[d]
        if not {"Revenue", "GrossProfit", "OperatingIncome", "PreTaxIncome"} <= set(v):
            continue
        rev = v["Revenue"] / YI
        if rev <= 0:
            continue
        gp, oi = v["GrossProfit"] / YI, v["OperatingIncome"] / YI
        nonop = v.get("TotalNonoperatingIncomeAndExpense", 0.0) / YI
        pretax = v["PreTaxIncome"] / YI
        net = v.get("IncomeAfterTaxes", 0.0) / YI
        eps = v.get("EPS")
        out.append(OrderedDict([
            ("date", d), ("revenue", rev),
            ("gross_margin", gp / rev), ("op_margin", oi / rev),
            ("opex_ratio", (gp - oi) / rev),
            ("op_income", oi), ("non_op", nonop),
            ("pretax", pretax), ("net", net), ("eps", eps),
            ("nonop_share", nonop / pretax if pretax else 0.0),
        ]))
    return out[-n:]


def attribute(qs):
    """逐季拆解 Δ稅前淨利。回傳每季貢獻與整段期間的絕對貢獻佔比。"""
    rows, totals = [], {"營收": 0.0, "毛利率": 0.0, "費用率": 0.0, "交乘": 0.0, "業外": 0.0}
    for a, b in zip(qs, qs[1:]):
        d_rev = b["revenue"] - a["revenue"]
        d_gm = b["gross_margin"] - a["gross_margin"]
        d_ox = b["opex_ratio"] - a["opex_ratio"]
        d_om = b["op_margin"] - a["op_margin"]
        eff = {
            "營收": d_rev * a["op_margin"],
            "毛利率": a["revenue"] * d_gm,
            "費用率": -a["revenue"] * d_ox,
            "交乘": d_rev * d_om,
            "業外": b["non_op"] - a["non_op"],
        }
        for k, v in eff.items():
            totals[k] += abs(v)
        rows.append({"quarter": b["date"], "d_pretax": b["pretax"] - a["pretax"], **eff})
    grand = sum(totals.values()) or 1.0
    share = {k: v / grand for k, v in totals.items()}
    return rows, share


def recommend(qs, share):
    """依診斷結果給出模型結構建議。"""
    nonop_dep = statistics.mean(abs(q["nonop_share"]) for q in qs)
    gm_vals = [q["gross_margin"] for q in qs]
    gm_range = (max(gm_vals) - min(gm_vals)) * 100
    rev_growths = [(b["revenue"] / a["revenue"] - 1) for a, b in zip(qs, qs[1:])]
    rev_vol = statistics.pstdev(rev_growths) * 100 if len(rev_growths) > 1 else 0.0

    recs, notes = [], []
    if nonop_dep > 0.40 or share["業外"] > 0.35:
        recs.append("**必須啟用 `equity_income` look-through**")
        notes.append(
            f"業外佔稅前淨利平均 {nonop_dep*100:.0f}%、佔變異來源 {share['業外']*100:.0f}%。"
            "把業外當常數會讓模型系統性失真——替這家公司建模＝替它的轉投資建模。")
    # 業外主導時，情境軸必須放在被投資公司的獲利，而非本業三率——
    # 本業毛利率上下幾個百分點的影響，遠小於被投資公司的循環轉折。
    if share["業外"] >= max(share["營收"], share["毛利率"]):
        recs.append("情境軸放在**被投資公司獲利**（非本業三率）")
        notes.append(
            f"業外效應佔變異 {share['業外']*100:.0f}%，是最大單一來源。"
            "情境分歧點應設在轉投資標的的獲利假設；本業毛利率變動屬次要變數，"
            "把情境軸放在本業會嚴重低估真實的 EPS 區間。")
    elif share["毛利率"] > share["營收"] * 1.3:
        recs.append("情境軸放在**毛利率**")
        notes.append(
            f"毛利率效應佔變異 {share['毛利率']*100:.0f}%，大於營收效應 {share['營收']*100:.0f}%。"
            "獲利由利潤率而非量能驅動，情境分歧點應設在毛利率而非營收。")
    elif share["營收"] > share["毛利率"] * 1.3:
        recs.append("情境軸放在**營收（量／產能）**")
        notes.append(
            f"營收效應佔變異 {share['營收']*100:.0f}%，大於毛利率效應 {share['毛利率']*100:.0f}%。"
            "產能、稼動率、出貨量是主要變數。")
    else:
        recs.append("情境軸需**同時涵蓋營收與毛利率**")
        notes.append(
            f"營收效應 {share['營收']*100:.0f}% 與毛利率效應 {share['毛利率']*100:.0f}% 相當，"
            "單押一邊會低估情境帶寬度。")
    if gm_range > 15:
        notes.append(
            f"⚠️ 毛利率近 {len(qs)} 季全距達 {gm_range:.1f}pp——這通常是模型中方差最大的單一變數，"
            "務必用區間而非點估計，且優先用一手資料（法說/私訪的級距毛利率）取代推估。")
    if share["費用率"] > 0.20:
        notes.append(
            f"費用率效應佔變異 {share['費用率']*100:.0f}%，偏高。"
            "建議把費用拆成固定＋變動（`opex_fixed` + `opex_ratio`），不要只用單一費用率。")
    return nonop_dep, gm_range, rev_vol, recs, notes


def run(ticker):
    qs = load_quarters(ticker)
    if len(qs) < 3:
        print(f"  {ticker}: 財報季數不足（{len(qs)}），無法診斷")
        return
    rows, share = attribute(qs)
    nonop_dep, gm_range, rev_vol, recs, notes = recommend(qs, share)

    print(f"\n{'='*74}\n【{ticker}】建模前診斷　近 {len(qs)} 季（{qs[0]['date']} ~ {qs[-1]['date']}）\n{'='*74}")
    print("  季別         營收(億)  毛利率  營益率  營益(億)  業外(億)  業外/稅前   EPS")
    for q in qs:
        eps = f"{q['eps']:6.2f}" if q["eps"] is not None else "   n/a"
        print(f"  {q['date']}  {q['revenue']:8.1f}  {q['gross_margin']*100:5.1f}%  "
              f"{q['op_margin']*100:5.1f}%  {q['op_income']:8.1f}  {q['non_op']:8.1f}  "
              f"{q['nonop_share']*100:7.0f}%  {eps}")

    print(f"\n  ── 稅前淨利變異來源拆解（絕對貢獻佔比）──")
    for k, v in sorted(share.items(), key=lambda kv: -kv[1]):
        bar = "█" * max(1, round(v * 40))
        print(f"    {k:<5} {v*100:5.1f}%  {bar}")

    print(f"\n  ── 關鍵統計 ──")
    print(f"    業外依賴度（平均）  {nonop_dep*100:.0f}%")
    print(f"    毛利率全距          {gm_range:.1f}pp")
    print(f"    營收季增波動度      {rev_vol:.1f}pp")

    print(f"\n  ── 建模建議 ──")
    for r in recs:
        print(f"    ▸ {r}")
    for n in notes:
        print(f"      · {n}")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for t in sys.argv[1:]:
        run(t.strip())
    print()
