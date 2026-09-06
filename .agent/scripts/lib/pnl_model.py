# -*- coding: utf-8 -*-
"""
LucasBrain 損益表推估引擎 (Driver-based P&L Model Engine)

設計原則（見 31_Models/README.md）：
1. 兩層模型：Layer 1 骨架必填、Layer 2 細節選填；Layer 2 的作用是「交叉驗證」
   Layer 1，不是取代它。兩層差距超過門檻時預設視為 Layer 2 過擬合。
2. 每個參數都必須帶 source 與 confidence（硬/軟/反解/推估），推估參數會在
   稽核區塊被標示出來。
3. 不輸出單一數字：一律輸出三情境 + 機率加權 + 可量化失效條件。
4. 識別性檢查：自由參數數量相對於獨立觀測數過多時發出警告。

單位慣例：
    營收/獲利 = 億元    股數 = 億股    EPS = 元
    產能 = 萬張/月 (或其他 unit_note 註明之單位)   ASP = 元/張
"""

import csv
import os
import re
from collections import OrderedDict

CONFIDENCE_LEVELS = ("硬", "軟", "反解", "推估")
QUARTER_RE = re.compile(r"^(\d{4})Q([1-4])$")


# ---------------------------------------------------------------- 參數解析

class Param:
    """單一參數：value + source + confidence。允許直接寫純數字（視為推估）。"""

    __slots__ = ("value", "source", "confidence", "note")

    def __init__(self, raw, key_hint=""):
        if isinstance(raw, dict):
            if "value" not in raw:
                raise ValueError(f"參數 {key_hint} 缺少 value 欄位")
            self.value = raw["value"]
            self.source = raw.get("source", "")
            self.confidence = raw.get("confidence", "推估")
            self.note = raw.get("note", "")
        else:
            self.value = raw
            self.source = ""
            self.confidence = "推估"
            self.note = "以純數字寫入，未標註來源"
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(
                f"參數 {key_hint} 的 confidence='{self.confidence}' 不合法，"
                f"必須為 {CONFIDENCE_LEVELS} 之一"
            )

    def __repr__(self):
        return f"Param({self.value}, {self.confidence})"


class ParamSeries:
    """
    依季度查值的參數序列。支援：
      - default: 全期共用
      - 明確季度 key（2026Q3）
      - 未指定的季度沿用「最近一個已指定的較早季度」，若無則用 default
    """

    def __init__(self, raw, name=""):
        self.name = name
        self.default = None
        self.by_quarter = OrderedDict()
        if raw is None:
            return
        if not isinstance(raw, dict):
            self.default = Param(raw, name)
            return
        for k, v in raw.items():
            if k == "default":
                self.default = Param(v, f"{name}.default")
            elif QUARTER_RE.match(str(k)):
                self.by_quarter[str(k)] = Param(v, f"{name}.{k}")
            elif k in ("value", "source", "confidence", "note"):
                # 整個 series 就是單一 Param 寫法
                self.default = Param(raw, name)
                break
            else:
                raise ValueError(f"參數 {name} 含無法辨識的 key: {k}")

    def get(self, quarter):
        if quarter in self.by_quarter:
            return self.by_quarter[quarter]
        # 沿用最近一個較早的已指定季度
        earlier = [q for q in self.by_quarter if _q_index(q) < _q_index(quarter)]
        if earlier:
            return self.by_quarter[max(earlier, key=_q_index)]
        if self.default is not None:
            return self.default
        raise KeyError(f"參數 {self.name} 在 {quarter} 無值且未提供 default")

    def all_params(self):
        out = []
        if self.default is not None:
            out.append((f"{self.name}.default", self.default))
        for q, p in self.by_quarter.items():
            out.append((f"{self.name}.{q}", p))
        return out


def _q_index(q):
    m = QUARTER_RE.match(str(q))
    if not m:
        raise ValueError(f"季度格式錯誤: {q}（應為 2026Q3 這種格式）")
    return int(m.group(1)) * 4 + int(m.group(2)) - 1


def _q_label(idx):
    return f"{idx // 4}Q{idx % 4 + 1}"


def quarter_range(start, end):
    return [_q_label(i) for i in range(_q_index(start), _q_index(end) + 1)]


def quarter_months(q):
    """回傳該季三個月的 (西元年, 月) tuple。"""
    m = QUARTER_RE.match(q)
    year, qn = int(m.group(1)), int(m.group(2))
    return [(year, (qn - 1) * 3 + i + 1) for i in range(3)]


# ---------------------------------------------------------------- 模型主體

class PnLModel:
    def __init__(self, params):
        self.raw = params
        self.meta = params.get("meta", {})
        self.consensus = params.get("consensus", {})
        self.invalidation = params.get("invalidation", []) or []

        horizon = params.get("horizon", {})
        self.start_q = horizon.get("start")
        self.end_q = horizon.get("end")
        if not self.start_q or not self.end_q:
            raise ValueError("horizon.start / horizon.end 為必填（例如 2026Q1 / 2027Q4）")
        self.quarters = quarter_range(self.start_q, self.end_q)

        l1 = params.get("layer1")
        if not l1:
            raise ValueError("layer1 為必填區塊")
        self.l1 = l1
        self.l2 = params.get("layer2", {}) or {}
        self.scenarios = params.get("scenarios", {}) or {}

        rev = l1.get("revenue", {})
        self.revenue_method = rev.get("method", "direct")
        self.capacity = ParamSeries(rev.get("capacity"), "layer1.revenue.capacity")
        self.utilization = ParamSeries(rev.get("utilization"), "layer1.revenue.utilization")
        self.asp = ParamSeries(rev.get("asp"), "layer1.revenue.asp")
        self.growth = ParamSeries(rev.get("growth"), "layer1.revenue.growth")
        self.direct_rev = ParamSeries(rev.get("direct"), "layer1.revenue.direct")
        self.capacity_months = rev.get("capacity_months_per_quarter", 3)
        self.asp_divisor = rev.get("asp_divisor", 10000)
        self.anchor_revenue = rev.get("anchor_revenue")  # growth 法的起點（億元）

        # 原型 B（專案/客戶驅動）：分部門營收。
        # 各部門直接給季營收(億元)，可選擇性帶各自毛利率；
        # 若所有部門都有毛利率，公司層級毛利率由部門加權推導（除非該季被明確指定）。
        self.segments = OrderedDict()
        for seg_name, seg in (rev.get("segments") or {}).items():
            self.segments[seg_name] = {
                "revenue": ParamSeries(seg.get("revenue"),
                                       f"segments.{seg_name}.revenue"),
                "gross_margin": (ParamSeries(seg["gross_margin"],
                                             f"segments.{seg_name}.gross_margin")
                                 if seg.get("gross_margin") else None),
                "note": seg.get("note", ""),
            }

        self.gross_margin = ParamSeries(l1.get("gross_margin"), "layer1.gross_margin")
        self.opex_ratio = ParamSeries(l1.get("opex_ratio"), "layer1.opex_ratio")
        self.opex_fixed = ParamSeries(l1.get("opex_fixed"), "layer1.opex_fixed")
        self.non_op = ParamSeries(l1.get("non_operating"), "layer1.non_operating")
        self.tax_rate = ParamSeries(l1.get("tax_rate"), "layer1.tax_rate")
        self.parent_ratio = ParamSeries(l1.get("parent_ratio"), "layer1.parent_ratio")
        self.shares = ParamSeries(l1.get("shares"), "layer1.shares")
        self.month_weights = l1.get("month_weights", {}) or {}

        # 權益法投資收益（控股型／轉投資比重高的公司必備，例如台塑集團）。
        # 依台灣稅制，國內轉投資之權益法收益不再課稅，故不計入課稅基礎。
        eq = l1.get("equity_income") or {}
        self.equity_taxable = eq.get("taxable", False)
        self.investees = OrderedDict()
        for name, spec in (eq.get("investees") or {}).items():
            self.investees[name] = {
                "ticker": spec.get("ticker", ""),
                "stake": ParamSeries(spec.get("stake"),
                                     f"equity_income.{name}.stake"),
                "net_income": ParamSeries(spec.get("net_income"),
                                          f"equity_income.{name}.net_income"),
                "note": spec.get("note", ""),
            }

    # ------------------------------------------------------------ 情境覆寫

    def _apply_overrides(self, overrides):
        """回傳一個以 (series_name, quarter) 為 key 的乘數/絕對值覆寫表。"""
        table = {}
        for path, spec in (overrides or {}).items():
            table[path] = spec
        return table

    def _ov(self, table, series_name, quarter, base_value):
        """
        套用覆寫：支援 {mul: 1.05} / {set: 0.30} / {add: 0.02}。

        查找順序與參數本身一致（forward-fill）：
          1. 該季精確覆寫             gross_margin.2027Q2
          2. 最近一個較早季度的覆寫    gross_margin.2027Q1  → 沿用至其後各季
          3. 整個 series 的覆寫        gross_margin
        沒有 forward-fill 的話，「2027 年毛利率降到 26%」只會作用在 2027Q1，
        情境之間的差異會被系統性低估。
        """
        spec = None
        exact = f"{series_name}.{quarter}"
        if exact in table:
            spec = table[exact]
        else:
            prefix = f"{series_name}."
            earlier = [k for k in table
                       if k.startswith(prefix)
                       and QUARTER_RE.match(k[len(prefix):])
                       and _q_index(k[len(prefix):]) < _q_index(quarter)]
            if earlier:
                spec = table[max(earlier, key=lambda k: _q_index(k[len(prefix):]))]
            elif series_name in table:
                spec = table[series_name]
        if spec is None:
            return base_value
        if isinstance(spec, dict):
            if "set" in spec:
                return spec["set"]
            v = base_value
            if "mul" in spec:
                v = v * spec["mul"]
            if "add" in spec:
                v = v + spec["add"]
            return v
        return spec

    # ------------------------------------------------------------ Layer 1

    def compute_layer1(self, overrides=None):
        table = self._apply_overrides(overrides)
        rows = []
        prev_rev = self.anchor_revenue
        for q in self.quarters:
            method = self.revenue_method
            if method == "capacity":
                cap = self._ov(table, "capacity", q, self.capacity.get(q).value)
                util = self._ov(table, "utilization", q, self.utilization.get(q).value)
                asp = self._ov(table, "asp", q, self.asp.get(q).value)
                revenue = cap * self.capacity_months * util * asp / self.asp_divisor
                drivers = {"capacity": cap, "utilization": util, "asp": asp}
            elif method == "growth":
                g = self._ov(table, "growth", q, self.growth.get(q).value)
                if prev_rev is None:
                    raise ValueError("growth 法需提供 layer1.revenue.anchor_revenue")
                revenue = prev_rev * (1 + g)
                drivers = {"growth": g}
            elif method == "direct":
                revenue = self._ov(table, "direct", q, self.direct_rev.get(q).value)
                drivers = {}
            elif method == "segments":
                revenue = 0.0
                drivers = {}
                seg_detail = []
                for name, seg in self.segments.items():
                    sr = self._ov(table, f"segments.{name}.revenue", q,
                                  seg["revenue"].get(q).value)
                    revenue += sr
                    drivers[name] = sr
                    sgm = None
                    if seg["gross_margin"] is not None:
                        sgm = self._ov(table, f"segments.{name}.gross_margin", q,
                                       seg["gross_margin"].get(q).value)
                    seg_detail.append((name, sr, sgm))
            else:
                raise ValueError(f"未知的 revenue.method: {method}")
            prev_rev = revenue

            # 毛利率：明確指定該季者優先（通常是已公布財報的實績），
            # 否則若各部門皆有毛利率則由部門加權推導，再否則走公司層級序列。
            blended_gm = None
            if method == "segments" and revenue:
                if all(sgm is not None for _, _, sgm in seg_detail):
                    blended_gm = sum(sr * sgm for _, sr, sgm in seg_detail) / revenue
            if q in self.gross_margin.by_quarter or blended_gm is None:
                gm = self._ov(table, "gross_margin", q, self.gross_margin.get(q).value)
            else:
                gm = self._ov(table, "gross_margin", q, blended_gm)
            gross = revenue * gm

            opex = 0.0
            try:
                opr = self._ov(table, "opex_ratio", q, self.opex_ratio.get(q).value)
                opex += revenue * opr
            except KeyError:
                opr = None
            try:
                opf = self._ov(table, "opex_fixed", q, self.opex_fixed.get(q).value)
                opex += opf
            except KeyError:
                opf = None

            op_income = gross - opex
            nonop = self._ov(table, "non_operating", q, self.non_op.get(q).value)

            # 權益法投資收益：各被投資公司淨利 × 持股比例
            equity_total = 0.0
            equity_detail = {}
            for name, inv in self.investees.items():
                stake = self._ov(table, f"equity_income.{name}.stake", q,
                                 inv["stake"].get(q).value)
                ni_i = self._ov(table, f"equity_income.{name}.net_income", q,
                                inv["net_income"].get(q).value)
                contrib = stake * ni_i
                equity_total += contrib
                equity_detail[name] = contrib

            pretax = op_income + nonop + equity_total
            tax = self._ov(table, "tax_rate", q, self.tax_rate.get(q).value)
            # 權益法收益預設免稅，不計入課稅基礎
            taxable = pretax if self.equity_taxable else (op_income + nonop)
            net = (pretax - taxable * tax)
            try:
                pr = self._ov(table, "parent_ratio", q, self.parent_ratio.get(q).value)
            except KeyError:
                pr = 1.0
            net *= pr
            sh = self.shares.get(q).value
            eps = net / sh if sh else 0.0

            rows.append(OrderedDict([
                ("quarter", q),
                ("revenue", revenue),
                ("gross_margin", gm),
                ("gross_profit", gross),
                ("opex", opex),
                ("op_income", op_income),
                ("op_margin", op_income / revenue if revenue else 0.0),
                ("non_operating", nonop),
                ("equity_income", equity_total),
                ("pretax", pretax),
                ("tax_rate", tax),
                ("net_income", net),
                ("shares", sh),
                ("eps", eps),
                # 業外依賴度：非本業貢獻佔稅後淨利比重。
                # 這個數字愈高，代表「替這家公司建模」實際上是在替它的轉投資建模。
                ("nonop_dependency",
                 (equity_total + nonop) / net if net else 0.0),
                ("_drivers", drivers),
                ("_equity", equity_detail),
            ]))
        return rows

    # ------------------------------------------------------------ Layer 2

    def layer2_enabled(self):
        return bool(self.l2.get("enabled"))

    def compute_layer2(self):
        """
        以產品組合重算營收與毛利率，作為 Layer 1 的交叉驗證。
        營收 = 產出量 × Σ(量佔比 × 價格指數) × 基準價
        毛利 = Σ(該級距營收 × 該級距毛利率)
        """
        if not self.layer2_enabled():
            return None
        tiers = self.l2.get("tiers", {})
        mix_raw = self.l2.get("mix", {})
        base_price = ParamSeries(self.l2.get("base_price"), "layer2.base_price")
        rows = []
        for q in self.quarters:
            mix = _nearest_quarter_value(mix_raw, q)
            if mix is None:
                continue
            cap = self.capacity.get(q).value
            util = self.utilization.get(q).value
            output = cap * self.capacity_months * util          # 萬張/季
            bp = base_price.get(q).value                        # 元/張

            weighted_index = 0.0
            gross = 0.0
            revenue = 0.0
            for tier, w in mix.items():
                spec = tiers.get(tier)
                if spec is None:
                    raise ValueError(f"layer2.mix 使用了未定義的級距: {tier}")
                pidx = spec["price_index"] if isinstance(spec, dict) else spec
                tier_gm = spec.get("gross_margin") if isinstance(spec, dict) else None
                tier_rev = output * w * pidx * bp / self.asp_divisor
                revenue += tier_rev
                weighted_index += w * pidx
                if tier_gm is not None:
                    gross += tier_rev * tier_gm
            implied_gm = gross / revenue if revenue else 0.0
            rows.append(OrderedDict([
                ("quarter", q),
                ("output", output),
                ("weighted_price_index", weighted_index),
                ("blended_asp", weighted_index * bp),
                ("revenue", revenue),
                ("gross_profit", gross),
                ("implied_gross_margin", implied_gm),
            ]))
        return rows

    # ------------------------------------------------------------ 月度拆分

    def monthly(self, quarterly_rows):
        rows = []
        for qr in quarterly_rows:
            q = qr["quarter"]
            weights = self.month_weights.get(q) or self.month_weights.get("default") \
                or [1 / 3, 1 / 3, 1 / 3]
            total = sum(weights)
            weights = [w / total for w in weights]
            for (year, month), w in zip(quarter_months(q), weights):
                rows.append(OrderedDict([
                    ("year_month", f"{year}-{month:02d}"),
                    ("quarter", q),
                    ("revenue", qr["revenue"] * w),
                    ("gross_profit", qr["gross_profit"] * w),
                    ("op_income", qr["op_income"] * w),
                    ("net_income", qr["net_income"] * w),
                    ("eps", qr["eps"] * w),
                ]))
        return rows

    # ------------------------------------------------------------ 彙總

    def annual_eps(self, quarterly_rows):
        out = OrderedDict()
        for r in quarterly_rows:
            year = r["quarter"][:4]
            out.setdefault(year, 0.0)
            out[year] += r["eps"]
        return out

    def rolling_forward_eps(self, monthly_rows, months=12, start_ym=None):
        """滾動未來 N 個月 EPS 合計（交易用 forward PE 的分母）。"""
        if start_ym is None:
            start_ym = self.meta.get("as_of_month")
        if start_ym is None:
            return None, None, None
        idx = next((i for i, r in enumerate(monthly_rows)
                    if r["year_month"] >= start_ym), None)
        if idx is None or idx + months > len(monthly_rows):
            return None, None, None
        window = monthly_rows[idx:idx + months]
        return (sum(r["eps"] for r in window),
                window[0]["year_month"], window[-1]["year_month"])


def _nearest_quarter_value(raw, quarter):
    if not raw:
        return None
    if quarter in raw:
        return raw[quarter]
    earlier = [q for q in raw if QUARTER_RE.match(str(q))
               and _q_index(q) <= _q_index(quarter)]
    if earlier:
        return raw[max(earlier, key=_q_index)]
    return None


# ---------------------------------------------------------------- 稽核

def audit(model):
    """回傳參數信心分布、推估參數清單、識別性警告。"""
    series = [
        model.capacity, model.utilization, model.asp, model.growth,
        model.direct_rev, model.gross_margin, model.opex_ratio,
        model.opex_fixed, model.non_op, model.tax_rate,
        model.parent_ratio, model.shares,
    ]
    for seg in model.segments.values():
        series.append(seg["revenue"])
        if seg["gross_margin"] is not None:
            series.append(seg["gross_margin"])
    for inv in model.investees.values():
        series.extend([inv["stake"], inv["net_income"]])
    counts = {lvl: 0 for lvl in CONFIDENCE_LEVELS}
    soft_list = []
    total = 0
    for s in series:
        for name, p in s.all_params():
            counts[p.confidence] += 1
            total += 1
            if p.confidence in ("推估", "軟"):
                soft_list.append((name, p.value, p.confidence, p.source or "（無來源）"))

    l2_params = 0
    if model.layer2_enabled():
        tiers = model.l2.get("tiers", {})
        for _, spec in tiers.items():
            if isinstance(spec, dict):
                l2_params += sum(1 for k in ("price_index", "gross_margin") if k in spec)
        for _, mix in (model.l2.get("mix", {}) or {}).items():
            l2_params += len(mix)

    n_quarters = len(model.quarters)
    observations = model.meta.get("independent_observations")
    warnings = []
    free_params = total + l2_params
    if observations:
        if free_params > observations * 2:
            warnings.append(
                f"識別性警告：自由參數 {free_params} 個 vs 宣告的獨立觀測 {observations} 個"
                f"（比值 {free_params / observations:.1f}x）。參數多於觀測數兩倍時，"
                f"多組參數組合可產生幾乎相同的擬合結果（參見聯茂 v44L 的交期/漲價幅度識別性問題）。"
            )
    if model.investees:
        warnings.append(
            f"結構警告：本模型含 {len(model.investees)} 家權益法被投資公司"
            f"（{'、'.join(model.investees.keys())}）。若業外依賴度偏高，"
            f"「替這家公司建模」實際上是在替它的轉投資建模——"
            f"被投資公司的獲利假設才是主要變數，本業三率反而是次要的。"
        )
    if counts["推估"] > counts["硬"]:
        warnings.append(
            f"來源警告：推估參數({counts['推估']})多於硬來源參數({counts['硬']})，"
            f"模型結論高度依賴未經一手驗證的假設。"
        )
    return {
        "counts": counts,
        "total_layer1": total,
        "total_layer2": l2_params,
        "free_params": free_params,
        "soft_list": soft_list,
        "warnings": warnings,
        "n_quarters": n_quarters,
    }


def calibration_check(model, l1_rows, tolerance=0.03):
    """
    基期校準：模型在「已有實際財報的季度」必須重現實績。

    這是最基本也最容易被跳過的檢查。若模型連已知的上一季都算不準，
    往前推的每一季都會帶著同一個系統性偏差。
    容差預設 3%（EPS 為 3%，三率為 0.5pp）。
    """
    actuals = model.raw.get("actuals") or {}
    if not actuals:
        return []
    by_q = {r["quarter"]: r for r in l1_rows}
    out = []
    for q, act in sorted(actuals.items()):
        if q not in by_q:
            continue
        m = by_q[q]
        for field, label, is_pct in (
            ("revenue", "營收(億)", False),
            ("gross_margin", "毛利率", True),
            ("op_margin", "營益率", True),
            ("eps", "EPS(元)", False),
        ):
            if field not in act:
                continue
            a, p = float(act[field]), float(m[field])
            if is_pct:
                diff = p - a
                ok = abs(diff) <= 0.005
                diff_s = f"{diff * 100:+.2f}pp"
            else:
                diff = (p - a) / a if a else 0.0
                ok = abs(diff) <= tolerance
                diff_s = f"{diff * 100:+.2f}%"
            out.append(OrderedDict([
                ("quarter", q), ("field", label),
                ("actual", a), ("model", p),
                ("diff", diff_s),
                ("status", "OK" if ok else "❌ 未校準"),
            ]))
    return out


def crosscheck(l1_rows, l2_rows, threshold=0.20):
    """Layer1 vs Layer2 差異檢查。預設差距 >20% 視為 Layer2 過擬合疑慮。"""
    if not l2_rows:
        return []
    l2_by_q = {r["quarter"]: r for r in l2_rows}
    out = []
    for r in l1_rows:
        q = r["quarter"]
        if q not in l2_by_q:
            continue
        l2 = l2_by_q[q]
        rev_diff = (l2["revenue"] - r["revenue"]) / r["revenue"] if r["revenue"] else 0.0
        gm_diff = l2["implied_gross_margin"] - r["gross_margin"]
        out.append(OrderedDict([
            ("quarter", q),
            ("l1_revenue", r["revenue"]),
            ("l2_revenue", l2["revenue"]),
            ("revenue_diff_pct", rev_diff),
            ("l1_gross_margin", r["gross_margin"]),
            ("l2_implied_gross_margin", l2["implied_gross_margin"]),
            ("gross_margin_diff_pp", gm_diff),
            ("flag", "⚠️過擬合疑慮" if abs(rev_diff) > threshold
                     or abs(gm_diff) > threshold / 2 else "OK"),
        ]))
    return out


# ---------------------------------------------------------------- 輸出

def write_csv(path, rows, exclude=("_drivers",)):
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = [k for k in rows[0].keys() if k not in exclude]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _fmt(v) for k, v in r.items() if k in fields})


def _fmt(v):
    if isinstance(v, float):
        return round(v, 4)
    return v
