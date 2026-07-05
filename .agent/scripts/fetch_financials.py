import os
import urllib.request
import urllib.parse
import json
import sys
from datetime import datetime

def date_to_quarter(date_str):
    # Mapping "YYYY-MM-DD" to "YYYYQx (實)"
    try:
        parts = date_str.split('-')
        year = parts[0]
        month = parts[1]
        if month in ['03', '12', '01', '02'] and month == '03':
            return f"{year}Q1 (實)"
        elif month == '06':
            return f"{year}Q2 (實)"
        elif month == '09':
            return f"{year}Q3 (實)"
        elif month == '12':
            return f"{year}Q4 (實)"
        else:
            # Fallback based on month range
            m_int = int(month)
            if 1 <= m_int <= 3:
                return f"{year}Q1 (實)"
            elif 4 <= m_int <= 6:
                return f"{year}Q2 (實)"
            elif 7 <= m_int <= 9:
                return f"{year}Q3 (實)"
            else:
                return f"{year}Q4 (實)"
    except:
        return date_str

def fetch_financial_table(stock_id):
    # Try loading token from credentials.json
    token = None
    try:
        cred_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.json")
        if os.path.exists(cred_path):
            with open(cred_path, 'r', encoding='utf-8') as f:
                cred = json.load(f)
                token = cred.get("finmind_token")
    except:
        pass

    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockFinancialStatements",
        "start_date": "2024-01-01",
        "data_id": stock_id
    }
    if token:
        params["token"] = token
        
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    req = urllib.request.Request(full_url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            records = res_data.get('data', [])
            if not records:
                print(f"No records found for stock ID {stock_id}.")
                return None
                
            # Group by date
            by_date = {}
            for r in records:
                d = r.get('date')
                t = r.get('type')
                v = r.get('value')
                if d not in by_date:
                    by_date[d] = {}
                by_date[d][t] = v
                
            # Sort dates
            sorted_dates = sorted(by_date.keys())
            
            # Keep the last 6 quarters for history
            target_dates = sorted_dates[-6:] if len(sorted_dates) >= 6 else sorted_dates
            
            table_lines = []
            table_lines.append("| 季度 | 營收 (億元) | 毛利率 (%) | 營業利益率 (%) | EPS (元) | 備註 / 營運重點說明 |")
            table_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            
            for d in target_dates:
                data = by_date[d]
                q_label = date_to_quarter(d)
                
                rev = data.get('Revenue', 0.0)
                gp = data.get('GrossProfit', 0.0)
                op = data.get('OperatingIncome', 0.0)
                eps = data.get('EPS', 0.0)
                
                rev_in_hundred_millions = rev / 100000000.0
                gp_margin = (gp / rev * 100.0) if rev > 0 else 0.0
                op_margin = (op / rev * 100.0) if rev > 0 else 0.0
                
                rev_str = f"{rev_in_hundred_millions:.2f}"
                gp_str = f"{gp_margin:.2f}%"
                op_str = f"{op_margin:.2f}%"
                eps_str = f"{eps:.2f}"
                
                table_lines.append(f"| **{q_label}** | {rev_str} | {gp_str} | {op_str} | {eps_str} | |")
                
            return "\n".join(table_lines)
    except Exception as e:
        print("Error fetching from FinMind:", e)
        return None

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    if len(sys.argv) < 2:
        print("Usage: python fetch_financials.py [stock_id]")
        sys.exit(1)
    sid = sys.argv[1].strip()
    tbl = fetch_financial_table(sid)
    if tbl:
        print(f"\n### 📊 {sid} 近六季財報數據 (FinMind 自動產出)")
        print(tbl)
