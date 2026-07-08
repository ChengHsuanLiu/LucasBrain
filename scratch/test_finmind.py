import os
import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta

ticker = "2303"
start_date = (datetime.now() - timedelta(days=70)).strftime("%Y-%m-%d")

# Load token
token = None
try:
    cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".agent", "credentials.json")
    print(f"Cred path: {cred_path}")
    if os.path.exists(cred_path):
        with open(cred_path, 'r', encoding='utf-8') as f:
            cred = json.load(f)
            token = cred.get("finmind_token")
            print("Token loaded successfully")
except Exception as e:
    print(f"Error loading token: {e}")

url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockHoldingSharesPer&data_id={ticker}&start_date={start_date}"
if token:
    url += f"&token={token}"

print(f"URL: {url}")
try:
    headers = {'User-Agent': 'Mozilla/5.0'}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        print(response.read().decode('utf-8')[:500])
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code} - {e.reason}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
