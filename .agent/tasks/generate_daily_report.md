# 任務工作流：生成盤後大盤日報 (Generate Daily Report)

> [!NOTE]
> 此工作流旨在每天盤後（建議晚上9點融資餘額資料更新後）產生一份整合大盤情況、族群強度、
> 大戶籌碼、個股買賣訊號的日報。四大區塊皆已實作完成。

## 📋 執行程序 (Execution Steps)

1. **執行自動化腳本**：
   ```powershell
   python .agent/scripts/generate_daily_report.py
   ```
   此腳本會：
   * 透過 FinMind 抓取上市加權指數(TAIEX)/上櫃指數(TPEx)的OHLC與成交量。
   * 計算 5/20/60 均線(斜率/股價位置/乖離率)、KD、MACD，並偵測黃金/死亡交叉與簡化版背離。
   * 透過 TWSE/TPEx 官方 Open API 加總融資餘額（上市/上櫃分開，以「億」為單位顯示）；
     上市金額取自 FinMind `TaiwanStockTotalMarginPurchaseShortSale` 的 `MarginPurchaseMoney`
     （官方無金額欄位，該資料集雖名為全市場但實測僅涵蓋上市）；上櫃因無官方金額資料集，
     改用 Fugle 熱力圖(上櫃)收盤價將個股張數換算金額後加總，**屬近似值**。並抓取 FinMind
     融資維持率。
   * 透過 FinMind 抓取三大法人現貨買賣超（外資/投信/自營商細分，以「億」為單位）與外資
     台指期未平倉。
   * 透過 Fugle 熱力圖公開API（上市IX0001／上櫃IX0043），用個股列的市值權重加權
     平均漲跌幅算出當日/近1週漲幅前3名產業，並列出各產業內領漲前3檔個股
     （不限資料庫既有個股）。
   * 讀取 `.agent/data/whale_positions.csv`，列出各大戶當日買進/賣出重點（首次記錄
     顯示總持股數與市值；有前次快照可比較時列出新建倉/出清/加碼/減碼前3大），彙整
     2位以上大戶同時持有的共識標的，並標記是否已存在於 `10_Stocks/` 資料庫。
   * 掃描 `10_Stocks/` 全庫個股，依隔年預估EPS × 所屬概念股FPE（讀取
     `20_Garden/概念股FPE合理區間.md`，同屬多概念取平均）算出目標價與期望值%，
     疊加均線/乖離率評分、5日線站上狀態與扣抵值判斷，產出買進（期望值>60%）與
     賣出/減碼（期望值<30%、跌破5MA且期望值<60%、乖離率評分過低）訊號表格。
   * 產生 `30_Projects/Daily_Report/{YYYYMMDD}_DailyReport.md` 與對應 PDF。

2. **確認檔案生成與路徑**：
   * 確認新生成的日報位於 `30_Projects/Daily_Report/` 底下。

3. **回報執行結果**：
   * 告知使用者日報已成功生成，並提供連結與大盤情況的簡短摘要（例如：偏多/偏空訊號是否一致）。

## 🚧 開發現況

四大區塊（一、大盤情況／二、族群強度／三、大戶籌碼／四、個股買賣訊號）皆已實作完成
並驗證可產出完整報告。後續若有調整需求（例如訊號門檻微調、族群強度改抓個股層級數據），
於此文件與對應 `lib/` 模組上增修即可。

## 🔗 共用模組

* `lib/market_data.py`：大盤指數/技術指標/融資/三大法人/外資期貨的資料抓取與計算。
* `lib/sector_trend.py`：Fugle 熱力圖公開API的產業漲跌幅計算（個股市值權重加權平均）
  與族群內領漲個股排序。
* `lib/whale_tracking.py`：大戶持股時間序列存取、部位變化比對、共識標的計算。
* `lib/stock_signals.py`：個股目標價（隔年EPS×概念FPE）/期望值/5日線站上與扣抵值訊號計算。
* `lib/report_pdf.py`：Markdown -> PDF 產生器，與 `generate_stock_report.py`／
  `generate_weekly_focus.py` 共用同一套設計系統（serif標題、細線分隔、色塊評等徽章）。
