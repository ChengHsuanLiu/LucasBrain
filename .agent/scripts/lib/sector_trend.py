"""
族群/概念股熱力圖強度掃描 (DailyReport 第二階段：二、股票族群情況)。

資料來源：Fugle 熱力圖公開API（使用者透過瀏覽器 F12 Network 分頁擷取確認，免登入）。
此API單次回應會同時包含「產業指數」列(type=INDEX)與「個股」列(type=EQUITY)，
個股列各自帶有官方產業分類代碼(industry欄位)，因此可以直接用個股列自行算出
各產業當日/近幾日的市值加權漲跌幅，並取得該產業內漲幅前幾名的成分股——
比先前 Statementdog 版本只有純標籤層級的資料更完整，能同時滿足「當日強勢族群」
與「族群內前三名個股」兩項需求。
"""
import json
import urllib.request

TWSE_SYMBOL = "IX0001"
TPEX_SYMBOL = "IX0043"

# TWSE/TPEx 官方產業分類代碼 -> 中文名稱。API本身的EQUITY列只給代碼、不給名稱，
# 此對照表為官方固定分類，不會隨時間變動，故直接靜態內建。
INDUSTRY_CODE_MAP = {
    "01": "水泥工業", "02": "食品工業", "03": "塑膠工業", "04": "紡織纖維",
    "05": "電機機械", "06": "電器電纜", "08": "玻璃陶瓷", "09": "造紙工業",
    "10": "鋼鐵工業", "11": "橡膠工業", "12": "汽車工業", "14": "建材營造",
    "15": "航運業", "16": "觀光餐旅", "17": "金融保險", "18": "貿易百貨",
    "20": "其他業", "21": "化學工業", "22": "生技醫療業", "23": "油電燃氣業",
    "24": "半導體業", "25": "電腦及週邊設備業", "26": "光電業", "27": "通信網路業",
    "28": "電子零組件業", "29": "電子通路業", "30": "資訊服務業", "31": "其他電子業",
    "32": "文化創意業", "33": "農業科技業", "35": "綠能環保業", "36": "數位雲端業",
    "37": "運動休閒業", "38": "居家生活業",
}


def fetch_heatmap(market_symbol, period=None):
    """market_symbol: TWSE_SYMBOL(上市) 或 TPEX_SYMBOL(上櫃)。
    period=None 為即時；"1w"為近一週(已驗證可用，其餘期間格式未測試暫不支援)。"""
    url = f"https://heatmap.fugle.tw/api/heatmaps/{market_symbol}"
    if period:
        url += f"?period={period}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.loads(response.read().decode('utf-8'))
        return data.get('data', [])


def compute_industry_performance(rows):
    """依 EQUITY 列的 industry 代碼，用市值權重(marketValueWeight)加權平均 changePercent，
    算出各產業表現，回傳 [{code, name, change_pct}] 依漲幅由高到低排序。"""
    agg = {}
    for r in rows:
        if r.get('type') != 'EQUITY':
            continue
        code = r.get('industry')
        weight = r.get('marketValueWeight') or 0
        change_pct = r.get('changePercent')
        if not code or change_pct is None or weight <= 0:
            continue
        entry = agg.setdefault(code, {"weighted_sum": 0.0, "weight_total": 0.0})
        entry["weighted_sum"] += change_pct * weight
        entry["weight_total"] += weight

    result = []
    for code, v in agg.items():
        if v["weight_total"] <= 0:
            continue
        result.append({
            "code": code,
            "name": INDUSTRY_CODE_MAP.get(code, f"未分類({code})"),
            "change_pct": v["weighted_sum"] / v["weight_total"],
        })
    result.sort(key=lambda x: x["change_pct"], reverse=True)
    return result


def top_stocks_in_industry(rows, industry_code, top_n=3):
    """回傳指定產業代碼中，該期間漲幅前 N 名的個股 [{symbol, name, change_pct}]（僅取有成交量者）。"""
    candidates = [
        r for r in rows
        if r.get('type') == 'EQUITY' and r.get('industry') == industry_code
        and r.get('changePercent') is not None and r.get('tradeVolume')
    ]
    candidates.sort(key=lambda r: r['changePercent'], reverse=True)
    return [
        {"symbol": r['symbol'], "name": r['name'], "change_pct": r['changePercent']}
        for r in candidates[:top_n]
    ]


def top_gaining_industries_with_stocks(market_symbol, period=None, top_n_industries=3, top_n_stocks=3):
    """整合函式：抓熱力圖 -> 算產業表現排名 -> 取前N產業，並各自附上族群內領漲前N檔個股。"""
    rows = fetch_heatmap(market_symbol, period)
    industries = compute_industry_performance(rows)
    top_industries = industries[:top_n_industries]
    for ind in top_industries:
        ind["top_stocks"] = top_stocks_in_industry(rows, ind["code"], top_n_stocks)
    return top_industries
