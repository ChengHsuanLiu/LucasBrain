---
name: g
description: 產生投資報告（Daily_Report / Financial_Screen / Invest_Timeline / Momentum_Screen / Weekly_Focus / Stock_Reports）。使用者輸入 /g 或 /g <報告類型> 或 /g Stock_Reports <股票代號> 時觸發。
---

使用者呼叫了這個 skill，附帶的參數是本次訊息裡 `/g` 後面的文字（可能為空）。

報告類型與對應腳本的完整對照表：

| 報告類型 | 腳本 | 說明 |
| :--- | :--- | :--- |
| Daily_Report | `.agent/scripts/generate_daily_report.py` | 盤後大盤日報 |
| Financial_Screen | `.agent/scripts/scan_financial_score.py` | 全市場財務指標篩選 |
| Invest_Timeline | `.agent/scripts/generate_invest_timeline.py` | 投資事件行事曆 |
| Momentum_Screen | `.agent/scripts/scan_momentum_score.py` | 全市場動能篩選 |
| Weekly_Focus | `.agent/scripts/generate_weekly_focus.py` | 週度投資決策 |
| Stock_Reports | `.agent/scripts/generate_stock_report.py {股票代號}` | 單一個股深入研報，需要股票代號參數 |

執行規則：

1. **沒有帶參數**（使用者只打了 `/g`）：用 AskUserQuestion 工具列出上述 6 個報告類型讓使用者選一個。如果選到 Stock_Reports，再追問一次股票代號（純文字輸入，例如 2330）。使用者選完/回答完之後，才執行對應腳本。

2. **參數明確對應到某個報告類型**（例如 `Daily_Report`、`Financial_Screen` 等，允許忽略大小寫與底線/空格差異做寬鬆比對）：直接執行對應腳本，不用再問。

3. **參數以 `Stock_Reports` 開頭且後面帶了股票代號**（例如 `Stock_Reports 2330`）：直接執行 `python .agent/scripts/generate_stock_report.py 2330`，不用再問。如果 `Stock_Reports` 後面沒有帶代號，用 AskUserQuestion 或直接追問使用者要哪一檔。

4. **參數看不出對應到哪個報告類型**：比照情境1，跳出選單讓使用者選，不要用猜的執行錯誤的腳本。

執行時的注意事項（沿用這個 repo 既有的慣例，不需要重新確認）：
- 用 Bash 工具在 repo 根目錄下執行 `python .agent/scripts/{腳本檔名}`（Financial_Screen、Momentum_Screen 這種全市場掃描通常要跑幾分鐘到幾十分鐘，建議用 `run_in_background: true`；Stock_Reports、Daily_Report、Weekly_Focus、Invest_Timeline 通常較快，可以前景執行）。
- 執行前不需要再跟使用者確認「要不要跑」——選單選擇或明確指令本身就是確認。
- 執行完回報產出檔案路徑（.md 與 .pdf），簡短總結報告重點即可，不用整份貼出來。
- 如果該報告會覆蓋今天已經產生過的正式報告檔案，執行前用 `git status`/`git diff --stat` 快速確認一下目前檔案是否為已提交的乾淨狀態；如果有未提交的異動，執行前提醒使用者一聲即可，不用阻擋。
