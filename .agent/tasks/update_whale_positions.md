# 任務工作流：更新大戶持股追蹤 (Update Whale Positions)

> [!NOTE]
> 此工作流旨在把使用者手動取得的大戶(重要投資人)券商庫存截圖/PDF，萃取為結構化資料並疊加進歷史資料庫，找出共識標的與部位變化。
> 資料是「多大戶 x 多股票 x 每日」的時間序列數字，儲存於 `.agent/data/whale_positions.csv`（非 Markdown 筆記），因為這類資料需要跨日期查詢/比對，Markdown 不適合。

## 📋 執行程序 (Execution Steps)

1. **辨識來源**：使用者會提供一批截圖或 PDF，每張/每份代表一位大戶當天的庫存/未實現損益列表（可能是手機 App 或券商網頁版，欄位格式不一）。

2. **視覺萃取為結構化快照**：逐一讀取每位大戶的截圖，萃取每一筆持股為一列，欄位對應：
   `whale_id, ticker, name, position_type(融資/現股), shares, cost_price, market_price, cost_basis, market_value, unrealized_pnl, pnl_pct`
   * **大戶身分一律用匿名代號標示**（大戶A、大戶B、大戶C...），不記錄真實姓名/帳號。同一位大戶下次更新時代號需維持一致（可依總市值量級或先前對話脈絡比對）。
   * 若截圖沒有股票代號（只有名稱），比對 `10_Stocks/` 現有筆記，或用 FinMind `TaiwanStockInfo` 查核正確代號（注意公司全名可能與簡稱不同，如京元電→京元電子2449、國巨→國巨*2327）。
   * 若截圖沒有顯示損益金額/比例，用 `(市價-成本均價)×股數` 概算 `unrealized_pnl`，`pnl_pct = unrealized_pnl / cost_basis × 100`。
   * **股票期貨帳戶命名規則**：商品名稱前綴「小」代表小型股票期貨（契約乘數 100 股/口），無前綴則為標準股票期貨（契約乘數 2,000 股/口）；名稱尾端數字為交割月份代碼，非公司名稱一部分（如「群創7」= 群創、「小聯發科7」= 聯發科）。換算股數 = 口數 × 契約乘數，可用報告本身的「口數 × 即時價位 × 乘數 = 總現值」反推驗證乘數是否正確。這類帳戶的 `position_type` 記為「股票期貨」；報告若只列即時價位與浮動損益、無成交均價，用 `entry_price = market_price - unrealized_pnl / shares` 反推成本價，`cost_basis = entry_price × shares`。
   * 將萃取結果寫成暫存 CSV（例如 `scratch/whale_snapshot_{YYYYMMDD}.csv`）。
   * **日期注意**：以資料本身標示的日期為準（如期貨報告的「留倉日期」），不要為了跟其他大戶對齊而竄改成別的日期——`track_whale_positions.py` 的共識分析已設計為採用「每位大戶各自最新一筆」，不要求同一天。

3. **執行更新腳本**：
   ```powershell
   python .agent/scripts/track_whale_positions.py {YYYY-MM-DD} scratch/whale_snapshot_{YYYYMMDD}.csv
   ```
   此腳本會：
   * 將快照併入 `.agent/data/whale_positions.csv` 主表（重複的 date+whale+ticker+position_type 列會自動跳過，可安全重跑）。
   * 對每位大戶計算與前一次快照的新增/加碼/減碼/出清部位。
   * 計算當天被 2 位以上大戶同時持有的共識標的。
   * 重新產生 `20_Garden/大戶籌碼追蹤.md` 彙總筆記。

4. **回報執行結果**：
   * 告知使用者本次新增了幾位大戶、幾筆部位資料。
   * 列出當天的共識標的清單（股票、持有大戶數）。
   * 若非首次更新，列出各大戶的加碼/減碼/新增/出清重點。
   * 提供 [大戶籌碼追蹤.md](20_Garden/大戶籌碼追蹤.md) 的連結。

## 🔗 與其他報告整合

`lib/whale_tracking.py` 提供 `get_whale_positions_for_ticker(ticker)`，可供 `generate_stock_report.py` 等腳本呼叫，在個股研報中附加「目前追蹤的大戶中有誰持有這檔股票」區塊。未來如需在 Weekly_Focus 加入「本週大戶共識標的」區塊，同樣呼叫 `get_consensus_stocks()`。
