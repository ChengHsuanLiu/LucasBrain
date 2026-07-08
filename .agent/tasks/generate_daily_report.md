# 任務工作流：生成盤後大盤日報 (Generate Daily Report)

> [!NOTE]
> 此工作流旨在每天盤後（建議晚上9點融資餘額資料更新後）產生一份整合大盤情況、族群強度、
> 大戶籌碼、個股買賣訊號的日報。目前已實作「一、大盤情況」與「四、資料庫個股買進/賣出訊號」，
> 其餘兩塊（族群強度掃描／大戶籌碼整合）將分階段加入。

## 📋 執行程序 (Execution Steps)

1. **執行自動化腳本**：
   ```powershell
   python .agent/scripts/generate_daily_report.py
   ```
   此腳本會：
   * 透過 FinMind 抓取上市加權指數(TAIEX)/上櫃指數(TPEx)的OHLC與成交量。
   * 計算 5/20/60 均線(斜率/股價位置/乖離率)、KD、MACD，並偵測黃金/死亡交叉與簡化版背離。
   * 透過 TWSE/TPEx 官方 Open API 加總融資餘額（上市/上櫃分開），並抓取 FinMind 融資維持率。
   * 透過 FinMind 抓取三大法人現貨買賣超（外資/投信/自營商細分）與外資台指期未平倉。
   * 掃描 `10_Stocks/` 全庫個股，依隔年預估EPS × 所屬概念股FPE（讀取
     `20_Garden/概念股FPE合理區間.md`，同屬多概念取平均）算出目標價與期望值%，
     疊加均線/乖離率評分、5日線站上狀態與扣抵值判斷，產出買進（期望值>60%）與
     賣出/減碼（期望值<30%、跌破5MA且期望值<60%、乖離率評分過低）訊號表格。
   * 產生 `30_Projects/Daily_Report/{YYYYMMDD}_DailyReport.md` 與對應 PDF。

2. **確認檔案生成與路徑**：
   * 確認新生成的日報位於 `30_Projects/Daily_Report/` 底下。

3. **回報執行結果**：
   * 告知使用者日報已成功生成，並提供連結與大盤情況的簡短摘要（例如：偏多/偏空訊號是否一致）。

## 🚧 開發現況與後續階段

目前已完成「一、大盤情況」與「四、資料庫個股買進/賣出訊號」。規劃中的後續階段（依優先順序）：

* **三、大戶籌碼整合**：呼叫 `lib/whale_tracking.py` 的 `get_consensus_stocks_latest()` /
  `get_whale_positions_for_ticker()`，標記大戶持股與資料庫個股重疊處。
* **二、族群強度掃描**：串接 Statementdog `https://statementdog.com/api/v1/market-trend/tw/{period}`
  （免登入公開API，period 可用 `1day`/`1week`/`1month`），找出當日/近幾日強勢概念族群。

## 🔗 共用模組

* `lib/market_data.py`：大盤指數/技術指標/融資/三大法人/外資期貨的資料抓取與計算。
* `lib/stock_signals.py`：個股目標價（隔年EPS×概念FPE）/期望值/5日線站上與扣抵值訊號計算。
* `lib/report_pdf.py`：Markdown -> PDF 產生器，與 `generate_stock_report.py`／
  `generate_weekly_focus.py` 共用同一套設計系統（serif標題、細線分隔、色塊評等徽章）。
