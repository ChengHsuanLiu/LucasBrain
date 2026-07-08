import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.stock_metrics import fetch_financial_statements, format_financial_table

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    if len(sys.argv) < 2:
        print("Usage: python fetch_financials.py [stock_id]")
        sys.exit(1)
    sid = sys.argv[1].strip()
    records = fetch_financial_statements(sid, "2024-01-01")
    tbl = format_financial_table(records, quarters=5)
    if tbl:
        print(f"\n### 📊 {sid} 近五季財報數據 (FinMind 自動產出)")
        print(tbl)
    else:
        print(f"No records found for stock ID {sid}.")
