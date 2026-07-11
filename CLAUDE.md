# LucasBrain 專案指示

## 報告產生快捷指令

Lucas 在對話中打出以下純文字指令時（不用斜線，直接打在訊息裡），代表要產生對應報告，直接執行對應腳本即可，不用先確認要不要跑：

| 指令 | 對應腳本 | 說明 |
| :--- | :--- | :--- |
| `g Daily_Report` | `.agent/scripts/generate_daily_report.py` | 盤後大盤日報 |
| `g Financial_Screen` | `.agent/scripts/scan_financial_score.py` | 全市場財務指標篩選 |
| `g Invest_Timeline` | `.agent/scripts/generate_invest_timeline.py` | 投資事件行事曆 |
| `g Momentum_Screen` | `.agent/scripts/scan_momentum_score.py` | 全市場動能篩選 |
| `g Weekly_Focus` | `.agent/scripts/generate_weekly_focus.py` | 週度投資決策 |
| `g Stock_Reports {股票代號}` | `.agent/scripts/generate_stock_report.py {股票代號}` | 單一個股深入研報（例如 `g Stock_Reports 2330`） |

執行規則：
1. **只打 `g`（沒有帶報告類型）**：用 AskUserQuestion 工具列出上述 6 個報告類型讓 Lucas 選一個；選到 Stock_Reports 的話再追問一次股票代號。選完/回答完才執行。
2. **`g` 後面帶的文字明確對應到某個報告類型**（忽略大小寫、底線/空格差異做寬鬆比對，例如 `g daily report`、`g weekly_focus` 都算數）：直接執行對應腳本，不用再問。
3. **`g Stock_Reports` 後面帶了股票代號**：直接執行對應腳本；沒帶代號則追問。
4. **`g` 後面的文字看不出對應到哪個報告類型**：比照規則1跳出選單，不要用猜的執行錯誤的腳本。

執行細節：
- 在 repo 根目錄下用 Bash 工具執行 `python .agent/scripts/{腳本檔名}`。Financial_Screen、Momentum_Screen 這種全市場掃描通常要跑幾分鐘到幾十分鐘，用 `run_in_background: true`；其他幾種較快，前景執行即可。
- 執行完回報產出檔案路徑（.md 與 .pdf）與簡短重點摘要，不用整份貼出來。
- 若該報告會覆蓋今天已產生過的正式報告檔案，執行前用 `git status`/`git diff --stat` 快速確認一下是否有未提交的異動；有的話提醒一聲即可，不用阻擋執行。
