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
| `g Diagnose {股票代號}` | `.agent/scripts/diagnose_model.py {股票代號}` | 建模前診斷：EPS變異來源拆解，建議模型原型與情境軸 |
| `g Model {股票代號}` | `.agent/scripts/build_pnl_model.py {股票代號}` | 損益推估模型：月/季損益表、三情境、滾動12M forward PE |
| `g Backtest {股票代號}` | `.agent/scripts/backtest_model.py {股票代號}` | 模型對帳：模型月營收 vs MOPS 實績，偏離示警 |

執行規則：
1. **只打 `g`（沒有帶報告類型）**：用 AskUserQuestion 工具列出上述 8 個報告類型讓 Lucas 選一個；選到 Stock_Reports / Model / Backtest 的話再追問一次股票代號。選完/回答完才執行。
2. **`g` 後面帶的文字明確對應到某個報告類型**（忽略大小寫、底線/空格差異做寬鬆比對，例如 `g daily report`、`g weekly_focus` 都算數）：直接執行對應腳本，不用再問。
3. **`g Stock_Reports` / `g Model` / `g Backtest` 後面帶了股票代號**：直接執行對應腳本；沒帶代號則追問。
4. **`g` 後面的文字看不出對應到哪個報告類型**：比照規則1跳出選單，不要用猜的執行錯誤的腳本。

執行細節：
- 在 repo 根目錄下用 Bash 工具執行 `python .agent/scripts/{腳本檔名}`。Financial_Screen、Momentum_Screen 這種全市場掃描通常要跑幾分鐘到幾十分鐘，用 `run_in_background: true`；其他幾種較快，前景執行即可。
- 執行完回報產出檔案路徑（.md 與 .pdf）與簡短重點摘要，不用整份貼出來。
- 若該報告會覆蓋今天已產生過的正式報告檔案，執行前用 `git status`/`git diff --stat` 快速確認一下是否有未提交的異動；有的話提醒一聲即可，不用阻擋執行。

### Model / Backtest 專屬規則

- **要替一檔新股票建模時，一律先跑 `g Diagnose`**，用 EPS 變異來源拆解決定模型原型與情境軸，不要憑感覺選結構。診斷結果應寫進 params.yaml 的註解裡。
- `g Model` 會讀取 `31_Models/{代號}{名稱}/params_v*.yaml`（自動取版本號最大者）。若該股尚無參數檔，**不要自己憑空生一份**，先問 Lucas 要不要建，並確認資料來源。
- **`g Model` 執行後一律接著跑一次 `g Backtest`**，因為模型改完必須立刻對帳；回報時把「基期校準是否通過」「有無連續偏離警示」講在前面，EPS 數字講在後面。
- 回報必須包含：三情境 EPS、機率加權、滾動 12M forward PE、以及稽核區塊列出的**推估參數**（那是模型最脆弱處，也是下次法說/私訪的提問清單）。
- **參數只能改 `params_*.yaml`**，`模型摘要_*.md` 與兩個 CSV 都是引擎產出，不要手動編輯。
- 若改版後某年度 EPS 上修超過 20%，先停下來說明是哪個參數造成的，不要直接當成新結論（聯茂 v20→v22 曾在兩天內把 2027 EPS 一路算到 78.56 元才修回 51.99）。
- 詳細設計原則見 `31_Models/README.md`。
