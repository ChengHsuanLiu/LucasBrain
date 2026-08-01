"""
統計分析：大盤融資維持率（FinMind原始值，未校正）與後續大盤表現的關聯，驗證
「維持率偏低時大盤容易築底反彈」的經驗法則。

方法：
1. 抓 FinMind TaiwanTotalExchangeMarginMaintenance 過去N年逐日原始資料。
2. 抓同期間 TAIEX 逐日收盤價，依日期對齊。
3. 分組統計：依原始維持率切分區間，計算各區間「未來N個交易日」報酬平均值/勝率。
4. 事件研究：抓出維持率「首次跌破THRESHOLD」的事件日（同一波修正只取第一天），
   列出事件前後大盤走勢與後續N日報酬。

⚠️ 重要限制：
- 本腳本改用FinMind「原始未校正」數值統計，不套用DailyReport用的-25.5pp
  MacroMicro校正值——該校正值是用近期(~15個交易日)資料比對得出，套到6年
  歷史回測會嚴重失真(實測：套用後歷史中位數會落到145%以下，明顯不合理)。
  若你平常看的維持率門檻(如150%)是校正後的口徑，套用本報告門檻前請先換算。
- 融資維持率與大盤同步變動（維持率低通常是大盤已經跌了的結果），本分析僅能看
  「維持率低點附近大盤是否容易止跌」，不構成領先預測。

用法：
    python analyze_margin_rebound.py [years_back] [threshold]
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.market_data import fetch_margin_maintenance_ratio, fetch_index_history

THRESHOLD_DEFAULT = 150.0
FORWARD_WINDOWS = [5, 10, 20, 40, 60]
BIN_EDGES = [0, 150, 155, 160, 165, 170, 175, 180, 999]

OUTPUT_DIR = r"C:\Users\User\Desktop\LucasBrain\30_Projects\Stock_Margin"


def bin_label(ratio):
    for i in range(len(BIN_EDGES) - 1):
        lo, hi = BIN_EDGES[i], BIN_EDGES[i + 1]
        if lo <= ratio < hi:
            if hi >= 999:
                return f">={lo}%"
            if lo <= 0:
                return f"<{hi}%"
            return f"{lo}-{hi}%"
    return "?"


def main():
    years_back = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else THRESHOLD_DEFAULT
    start_date = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")

    print(f"抓取融資維持率資料 (起始日 {start_date})...")
    maint = fetch_margin_maintenance_ratio(start_date)
    if not maint:
        print("查無融資維持率資料")
        return
    for row in maint:
        row["ratio"] = round(row["ratio"], 2)
    print(f"取得 {len(maint)} 筆，實際起始日：{maint[0]['date']}，最新日：{maint[-1]['date']}")

    print("抓取TAIEX指數資料...")
    idx = fetch_index_history("TAIEX", start_date)
    idx_by_date = {r["date"]: r["close"] for r in idx if r.get("close")}
    print(f"取得 {len(idx)} 筆指數資料")

    # 對齊：只保留維持率與指數皆有資料的日期，依日期排序
    merged = []
    for row in maint:
        d = row["date"]
        if d in idx_by_date:
            merged.append({"date": d, "ratio": row["ratio"], "close": idx_by_date[d]})
    merged.sort(key=lambda r: r["date"])
    print(f"對齊後共 {len(merged)} 個交易日\n")

    if len(merged) < 30:
        print("資料筆數過少，無法進行有意義的統計。")
        return

    closes = [r["close"] for r in merged]
    n = len(merged)

    # 計算每日的未來N日報酬 / 未來N日內最大報酬
    for i, row in enumerate(merged):
        for w in FORWARD_WINDOWS:
            if i + w < n:
                row[f"fwd_{w}"] = (closes[i + w] / closes[i] - 1) * 100
                future_slice = closes[i + 1: i + w + 1]
                row[f"fwdmax_{w}"] = (max(future_slice) / closes[i] - 1) * 100
            else:
                row[f"fwd_{w}"] = None
                row[f"fwdmax_{w}"] = None

    ratios_sorted = sorted(r["ratio"] for r in merged)
    print(f"原始維持率分佈：min={ratios_sorted[0]:.1f} median={ratios_sorted[n//2]:.1f} "
          f"5th_pct={ratios_sorted[int(n*0.05)]:.1f} max={ratios_sorted[-1]:.1f}\n")

    # ---------- 分組統計 ----------
    lines = []
    lines.append("# 大盤融資維持率(FinMind原始值，未校正) vs 後續大盤表現統計\n")
    lines.append(f"資料期間：{merged[0]['date']} ~ {merged[-1]['date']}（{n} 個交易日）")
    lines.append("⚠️ 本表使用FinMind原始未校正數值，未套用DailyReport用的-25.5pp MacroMicro校正——")
    lines.append("該校正值僅用近期資料比對得出，套到6年歷史會系統性失真，詳見腳本docstring。")
    lines.append(f"原始值分佈：最小值{ratios_sorted[0]:.1f}%、中位數{ratios_sorted[n//2]:.1f}%、"
                 f"5th百分位{ratios_sorted[int(n*0.05)]:.1f}%、最大值{ratios_sorted[-1]:.1f}%\n")
    lines.append("## 一、依維持率區間分組的未來報酬統計\n")
    header = "| 維持率區間 | 樣本數 | " + " | ".join(f"未來{w}日均報酬%" for w in FORWARD_WINDOWS) + " | " + " | ".join(f"未來{w}日勝率%" for w in FORWARD_WINDOWS) + " |"
    sep = "|" + "---|" * (2 + len(FORWARD_WINDOWS) * 2)
    lines.append(header)
    lines.append(sep)

    bins = {}
    for row in merged:
        lbl = bin_label(row["ratio"])
        bins.setdefault(lbl, []).append(row)

    bin_order = sorted(bins.keys(), key=lambda lbl: min(r["ratio"] for r in bins[lbl]))

    for lbl in bin_order:
        rows = bins[lbl]
        cells = [lbl, str(len(rows))]
        for w in FORWARD_WINDOWS:
            vals = [r[f"fwd_{w}"] for r in rows if r[f"fwd_{w}"] is not None]
            cells.append(f"{sum(vals)/len(vals):+.2f}" if vals else "-")
        for w in FORWARD_WINDOWS:
            vals = [r[f"fwd_{w}"] for r in rows if r[f"fwd_{w}"] is not None]
            winrate = sum(1 for v in vals if v > 0) / len(vals) * 100 if vals else 0
            cells.append(f"{winrate:.0f}" if vals else "-")
        lines.append("| " + " | ".join(cells) + " |")

    # ---------- 事件研究：首次跌破threshold ----------
    lines.append(f"\n## 二、事件研究：維持率(原始值)首次跌破 {threshold}% 的事件\n")
    events = []
    prev_above = True
    for i, row in enumerate(merged):
        below = row["ratio"] < threshold
        if below and prev_above:
            events.append(i)
        prev_above = not below
    print(f"找到 {len(events)} 次「首次跌破{threshold}%」事件")

    if events:
        header2 = "| 事件日 | 當日維持率% | 當日TAIEX | " + " | ".join(f"未來{w}日報酬%" for w in FORWARD_WINDOWS) + " | " + " | ".join(f"未來{w}日內最大漲幅%" for w in FORWARD_WINDOWS) + " |"
        lines.append(header2)
        lines.append("|" + "---|" * (3 + len(FORWARD_WINDOWS) * 2))
        for i in events:
            row = merged[i]
            cells = [row["date"], f"{row['ratio']:.1f}", f"{row['close']:.0f}"]
            for w in FORWARD_WINDOWS:
                v = row[f"fwd_{w}"]
                cells.append(f"{v:+.2f}" if v is not None else "資料不足")
            for w in FORWARD_WINDOWS:
                v = row[f"fwdmax_{w}"]
                cells.append(f"{v:+.2f}" if v is not None else "資料不足")
            lines.append("| " + " | ".join(cells) + " |")

        # 事件平均值總結
        lines.append("\n### 事件平均表現")
        for w in FORWARD_WINDOWS:
            vals = [merged[i][f"fwd_{w}"] for i in events if merged[i][f"fwd_{w}"] is not None]
            maxvals = [merged[i][f"fwdmax_{w}"] for i in events if merged[i][f"fwdmax_{w}"] is not None]
            if vals:
                winrate = sum(1 for v in vals if v > 0) / len(vals) * 100
                lines.append(f"- 未來{w}日：平均報酬 {sum(vals)/len(vals):+.2f}%，勝率 {winrate:.0f}%，樣本數 {len(vals)}；未來{w}日內最大漲幅平均 {sum(maxvals)/len(maxvals):+.2f}%")
    else:
        lines.append("（資料期間內維持率未曾跌破此門檻，或資料筆數不足以偵測事件）")

    lines.append("\n## 三、限制與注意事項")
    lines.append("- 本表為FinMind原始未校正數值，與DailyReport顯示的校正後維持率口徑不同，兩者不可直接比較")
    lines.append("- 融資維持率與大盤同步變動，本分析僅能看「維持率低點附近大盤是否容易止跌」，非領先預測")
    lines.append("- 事件研究法樣本數可能偏少，個別極端事件（如系統性股災）會拉高變異")

    out_path = os.path.join(OUTPUT_DIR, f"{datetime.now().strftime('%Y%m%d')}_融資維持率反彈統計_原始值.md")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n報告已輸出至：{out_path}")


if __name__ == "__main__":
    main()
