"""
族群/概念股熱力圖強度掃描 (DailyReport 第二階段：二、股票族群情況)。

資料來源：Statementdog 公開 market-trend API（免登入，即前端熱力圖頁面實際呼叫的API，
使用者於瀏覽器 F12 Network 分頁擷取確認）。僅 1day/1week/1month 三個期間可用——
3month/5day 回傳空陣列，1year 會逾時，因此不支援。
"""
import json
import urllib.request

BASE_URL = "https://statementdog.com/api/v1/market-trend/tw/{period}"
SUPPORTED_PERIODS = ["1day", "1week", "1month"]


def fetch_sector_trend(period):
    """回傳 [{name, diff_percentage, url}]，API 原始順序已依漲跌幅絕對值由大到小排列。"""
    if period not in SUPPORTED_PERIODS:
        raise ValueError(f"Unsupported period '{period}', must be one of {SUPPORTED_PERIODS}")

    url = BASE_URL.format(period=period)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.loads(response.read().decode('utf-8'))
        return data.get('data', [])


def top_gaining_sectors(period, top_n=3):
    """回傳指定期間漲幅前 N 名的族群 (僅取 diff_percentage > 0 者)。"""
    sectors = fetch_sector_trend(period)
    gainers = [s for s in sectors if s.get('diff_percentage', 0) > 0]
    gainers.sort(key=lambda s: s['diff_percentage'], reverse=True)
    return gainers[:top_n]
