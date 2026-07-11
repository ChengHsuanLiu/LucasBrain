# 🧭 LucasBrain 核心運作指南 (SCHEMA.md)

> [!NOTE]
> 本文件為 LucasBrain 知識庫的最高運行憲章。當 Lucas 要求「幫我整理」、「Ingest」或進行任何知識管理時，AI 代理必須以此規範為唯一準則。

---

## 👤 第一部分：AI 角色定位與安全防線

### 1. 溝通風格與語氣
* **預設語意**：使用 **繁體中文 (台灣用語)** 回覆。
* **語氣原則**：清楚、實用、自然、冷計。
* **行動導向**：能直接動手做（如撰寫腳本、修改檔案）就直接執行，不要只給口頭建議，除非涉及安全防線。
* **誠實原則**：資訊不確定時，必須明確區分以下三者，嚴禁假裝有把握：
  1. **已知事實** (有法說、公告、一手報告支持)
  2. **合理推論** (由技術規格、供應鏈位置推導)
  3. **尚未查證** (缺乏公司層級證據，需後續補齊)

### 2. 安全防線 (不可逾越之邊界)
> [!CAUTION]
> 除非 Lucas 在對話中明確授權，否則絕對禁止執行以下高風險操作：
> * 刪除檔案或進行大範圍的目錄移動。
> * 重設 Git 歷史紀錄 (`git reset --hard` 等)。
> * 合併 Pull Request 或發布 Code Review。
> * 自動發送 Email、貼文、更改雲端檔案共享權限。
> * 進行帳號、系統層級的重大設定或下單交易。

---

## 📂 第二部分：目錄結構與 Obsidian 筆記規則

### 1. 知識庫目錄定義
* **`00_Inbox/`**：存放原始輸入、待整理的券商報告與臨時筆記。
  * **`00_Inbox/whales/`**：專放大戶券商庫存/未實現損益截圖，執行「更新大戶持股」時處理，
    結構化資料寫入 `.agent/data/whale_positions.csv`，原始截圖歸檔至 `98_Archives/Whale_Snapshots/`。
* **`10_Stocks/`**：個股專屬頁面，命名格式為 `[股票代號][名稱].md` (例如 `3189景碩.md`)。
* **`20_Garden/`**：結構化的產業知識筆記（如 `CCL銅箔基板.md`），注重長期的產業演化與技術壁壘。
* **`30_Projects/`**：專案報告與投資決策等可交付的完整成果，細分目錄如下：
  * **`30_Projects/Weekly_Focus/`**：存放週度投資決策與持股追蹤（命名為 `{當天日期}_Weekly_Focus.md`）。
  * **`30_Projects/Daily_Report/`**：存放盤後大盤日報（命名為 `{當天日期}_DailyReport.md`），內容涵蓋大盤指數/技術指標/融資/三大法人/外資期貨等大盤情況，未來將擴充族群強度掃描、大戶籌碼整合、個股買賣訊號。
  * **`30_Projects/Stock_Reports/`**：個股深入研報與分析（命名為 `{當天日期}_{股票代號}{股票名稱}_個股研報.md`）。
  * **`30_Projects/Garden_Reports/`**：產業深入研究報告（命名為 `{當天日期}_{產業名稱}_產業研報.md`）。
  * **`30_Projects/Invest_Timeline/`**：存放投資重點時間軸報告（命名為 `{當天日期}_投資時間軸.md`）。
* **`98_Archives/`**：已處理完成的原始素材與歷史報告存檔區，細分目錄如下：
  * **`98_Archives/Expert_Meetings/`**：專家會議與專家訪談相關的原始檔案（如：南亞專家會議、CCL產業專家會議）。
  * **`98_Archives/Research_Report/`**：各券商與研究機構出具的正式法人研報（如：摩根士丹利台積電報告、統一證券CCL研究報告、HSBC聯發科研究報告、大和證券MLCC產業報告）通常是 pdf 檔案，如果不是 pdf 檔案的可以放去 Stock_Memo。
  * **`98_Archives/Stock_Memo/`**：單一個股法說會、私訪、股東會等非正式會議紀要與單一個股 Memo（如：4764雙鍵股東會memo、2383台光電memo、2330台積電法說memo）。
  * **`98_Archives/Fund_Company_Memo/`**：其他投信/投資公司的討論內容，通常標題與「會議紀錄」相關，內容通常是針對多個不同股票或市場的看法。
  * **`98_Archives/Whale_Snapshots/`**：大戶券商庫存/未實現損益截圖原始檔（`00_Inbox/whales/` 底下的素材），結構化後的資料寫入 `.agent/data/whale_positions.csv`，此處僅保留原始截圖存查。
  * **`98_Archives/Others/`**：其他無明確分類歸屬的素材檔案均存放於此。
* **`97_Settings/`**：存放腳本讀取的設定/參數表與規則定義文件（供人工審閱與調整），
  與 `20_Garden/` 的敘事型產業知識筆記區隔——判斷依據為「這是腳本會直接讀取的
  設定/公式，還是一篇產業研究筆記」。例如 `概念股FPE合理區間.md`（個股目標價計算
  用的FPE參數表）、`大盤分數計算方式.md`（DailyReport大盤評分的加減分規則與級距）。
  純粹由腳本產生、每次執行就覆蓋的「即時動態彙總/儀表板」（如 `大戶籌碼追蹤.md`）
  不屬於此類，仍留在 `20_Garden/`。
* **`99_Templates/`**：存放 Stock/Industry 範本、系統指令、工作流與腳本。

### 2. Obsidian 筆記規範
* **標準範本**：
  * 個股筆記格式遵循 [Template_Stock.md](file:///c:/Users/User/Desktop/LucasBrain/99_Templates/Template_Stock.md)
  * 產業筆記格式遵循 [Template_Industry.md](file:///c:/Users/User/Desktop/LucasBrain/99_Templates/Template_Industry.md)
* **雙向連結 (WikiLinks)**：在更新內文時，提及任何相關個股或關鍵技術，必須自動用雙中括號連結（如 `[[2383台光電]]`、`[[CoWoS]]`）。
* **So What? 測試**：每一筆新增的資訊都要能回答「這對投資決策有什麼影響？」。
* **資訊完整性**：重構時絕不刪除既有資訊，暫時無用的宏觀背景可移入個股的 `## 📝 歷史筆記與會議紀要` 封存。
* **詳盡優先於精簡**：`10_Stocks/` 與 `20_Garden/` 筆記主要供 AI 未來生成 `30_Projects/` 報告時讀取，不是給人類直接閱讀的最終文件。因此 ingest 新增資訊時，應保留原始數字、原文語句、法說/會議 Q&A 逐字內容，而非為了精簡易讀而摘要、改寫或省略細節——摘要後遺失的細節在未來生成報告時無法復原（因為報告是讀筆記而非回頭翻原始封存檔）。僅可省略重複贅述或與投資判斷完全無關的內容（如制式免責聲明）。

### 3. 產業分類架構：產業位置 vs. 題材（2026-07-11 起）
`20_Garden/` 的產業頁面分成兩種性質，分類判斷與檔名慣例不同：

* **產業位置（Industry Position）**：結構性、單一值。依照「需求端→晶片層→上游→系統層→應用端」五層供應鏈架構分類，檔名格式為 `{Tier編號}_{Tier名稱}_{子分類名稱}`（例如 `2_晶片層_ASIC客製晶片`、`3_上游_載板PCB_CCL`）。一檔股票通常只屬於一個產業位置，對應個股 frontmatter 的 `industry:` 欄位（單一值，描述核心業務）。
* **題材（Theme）**：跨層、可多值。代表特定的投資敘事/訂單機會（例如 `CoPoS與玻璃基板`、`伺服器無電纜化架構`），可能同時橫跨多個產業位置的股票。檔名不加 Tier 前綴，維持原本的敘事性命名。一檔股票可以同時有零到多個題材曝險。
* **其他**：不屬於 AI 供應鏈框架的分類（如 `生技醫療`）或純方法論頁面（如 `財務指標篩選機制`），不強制歸入五層架構。

**Garden 頁面 frontmatter** 需標註 `garden_type: industry` 或 `garden_type: theme` 以利區分；產業位置頁面另加 `tier: "N_層級名稱"` 欄位。

**新股票分類判斷流程**（ingest 時遇到現有 Garden 找不到對應分類的股票）：
1. 先判斷此股票核心業務對應哪個五層產業位置（通常唯一）。
2. 再檢查是否有具體題材曝險（供應鏈突破、新客戶、新技術導入等），可能零個到多個。
3. 若找不到合適的現有 Garden 分類，**先跟 Lucas 確認再新增頁面**，不要自行創造新分類——這會影響 `97_Settings/概念股FPE合理區間.md` 的估值分類，是需要人工把關的決策。

**FPE 表結構**：`97_Settings/概念股FPE合理區間.md` 用「類型」欄位（產業位置/題材/其他）標記每一列，但目標價計算邏輯不變——同一檔股票若同屬多個概念（產業位置+題材），FPE 區間仍取所有符合概念的平均值。

---

## ⚡ 第三部分：常用的 AI 工作流 (Task Workflows)

### 1. 指令映射表 (Command Mapping)
當收到特定指令時，優先閱讀對應的任務說明檔：

| 語意指令 | 核心目標 | 任務描述檔 |
| :--- | :--- | :--- |
| `幫我整理`、`run ingest`、`整理筆記`、`清洗 Inbox` | 整理並歸檔 `00_Inbox/` 中的文件 | `.agent/tasks/ingest.md` |
| `sort garden` | 重新分類與整理知識庫結構 | `.agent/tasks/restructure.md` |
| `process files` | 大量轉換 Office 或 PDF 檔案 | `.agent/tasks/process_files.md` |
| `update indices` | 更新個股與產業索引目錄 | `.agent/tasks/generate_indices.md` |
| `recall [主題]` / `brief [主題]` | 提取特定概念的歷史紀要與簡報 | `.agent/tasks/recall.md` / `brief.md` |
| `gaps` | 尋找個股或產業鏈的資訊缺口 | `.agent/tasks/gaps.md` |
| `challenge [[Note]]` | 挑戰既有投資假設並尋找漏洞 | `.agent/tasks/challenge.md` |
| `重新分類封存檔案` | 重新對 `98_Archives/` 底下所有子資料夾與檔案進行分類評估 | `.agent/tasks/reclassify_archives.md` |
| `gagp` | 快速執行 git add、commit 與 push | `.agent/tasks/gagp.md` |
| `g WeeklyFocus` | 生成週度投資建議與持股追蹤報告 | `.agent/tasks/generate_weekly_focus.md` |
| `更新大戶持股` | 將大戶券商庫存截圖萃取為結構化快照，更新籌碼追蹤資料庫 | `.agent/tasks/update_whale_positions.md` |
| `g DailyReport` | 生成盤後大盤日報（大盤情況/族群強度/大戶整合/個股買賣訊號） | `.agent/tasks/generate_daily_report.md` |

---

### 2. 📥 Ingest (整理與匯入) 標準七步驟流程

> [!IMPORTANT]
> 流程核心精神：**自由調用 Python/Git/Cmd 工具，無損疊加，時間近的在上，絕不覆蓋舊數據。**

#### 步驟 1：多格式檔案預處理 (Pre-process)
若 `00_Inbox/` 內有非 Markdown 檔案，必須依下列程序轉換後再行解析：
* **PNG / JPEG 圖片**：使用 Vision（多模態視覺能力）讀取，精準提取文字、圖表與數據，嚴禁跳過。
* **Docx 文件**：優先使用背景指令（如 `pandoc` 或 Python 套件）轉換為 Markdown 格式再讀取。
* **Excel / CSV 表格**：必須完整轉換為 Markdown Table，保留所有財務預估與籌碼數據。

#### 步驟 2：提取關鍵投資實體 (Analyze)
分析預處理後的內文，辨識關鍵數據：
* **個股實體**：個股財務數據、各年度 EPS 預估、有精確時間點的營運事件（如「2026Q3開出新產能」）。
* **產業實體**：產業供需缺口、技術迭代進程、材料升級（如 M7 ➡️ M8）。

#### 步驟 3：增量疊加寫入 (Compound & Link)
* **無損疊加**：將新資訊填入對應 of 10_Stocks/ 或 20_Garden/ 頁面。
* **詳盡優先於精簡**：法說會/專家訪談等 Q&A 型素材應盡量保留逐字內容寫入 `## 📝 歷史筆記與會議紀要`，不要只留一份「重點整理」——整理後的摘要無法逆向還原成原文，未來報告只讀筆記不會回頭查原始封存檔。
* **時序排列**：時間近的資訊排在上方，舊的在下方。
* **衝突處理**：新舊數據不同時不可直接覆蓋，必須在頁面上並列標註。
* **補齊 WikiLinks**：自動為文中出現的廠商加上雙中括號連結。

#### 步驟 4：歸檔 raw file (Archive)
將 `00_Inbox/` 中處理完畢的檔案分類移動至 `98_Archives/` 對應的分類資料夾（`Expert_Meetings/`、`Research_Report/`、`Stock_Memo/`、`Fund_Company_Memo/`、`Others/`）。無法明確歸類者，移動至 `Others/` 資料夾下。

#### 步驟 5：更新統計目錄 (Index)
更新 [index.md](file:///c:/Users/User/Desktop/LucasBrain/index.md) 的個股/產業最新統計數量與最近更新時間。

#### 步驟 6：追加歷史日誌 (Log)
在 [log.md](file:///c:/Users/User/Desktop/LucasBrain/log.md) 的尾端追加一行紀錄，格式如下：
`## [YYYY-MM-DD] ingest | 檔案名稱 | 影響的 Stocks 及 Garden`

#### 步驟 7：版本管理與回報 (Commit & Push)
* **回報檔案變化**：在回報整理成果時，必須清楚列出 `10_Stocks/` 或 `20_Garden/` 底下的檔案有什麼變化（例如新增了哪些重點、修改了哪些數據或段落等）。
* **版本管理**：主動為 Lucas 整理本次 commit 的簡短標題，詢問是否執行 `git commit` 與 `git push`。

---

## 📊 第四部分：投研分析與交付物標準

### 1. 投研分析維度
分析個股或產業鏈時，建議從以下面向切入，確保邏輯嚴密：
* **基本面**：營收與 EPS、產能規劃、BOM 表升級（如 Blackwell 規格變化）。
* **籌碼面**：大戶分點進出、籌碼集中度。
* **技術面**：價格與均線趨勢。
* **風險評估**：多情境敏感度分析（如價格不漲 vs. 漲價 30% / 50% 對 EPS 的影響）。

### 2. 投研裁決系統 (Dual-Track Ruling System)
個股筆記採用雙軌制裁決，以精確區分「長期基本面價值」與「短期技術/籌碼操作」：

#### (1) 評價裁決 (Valuation Rating) — 基於 N+1 遠期本益比 (Forward P/E)
基於當前即時收盤價與明年度 (即 $N+1$ 年，系統會自動偵測當前西元年份，例如當前為 2026 年，則以 2027 年計) 平均預估 EPS 算出的遠期本益比，由系統每日執行 `.agent/scripts/update_prices.py` 腳本自動判定並填寫：
* **遠期本益比公式**：$\text{Forward P/E} = \frac{\text{收盤股價}}{\text{N+1年平均預估 EPS}}$
* **自動判定評等門檻**：
  - **`ADD`** (加碼/買進)：Forward P/E < 25x (估值偏低，具安全邊際，偏向加碼買進)。
  - **`HOLD`** (續抱/中性)：25x <= Forward P/E <= 35x (估值合理，維持中性續抱)。
  - **`SELL`** (賣出/避開)：Forward P/E > 35x (估值偏高，偏向逢高獲利結清或減碼避開)。
  *備註：若尚未取得明年度的預估 EPS，系統會將 PE 與 Rating 標記為 `待補充` 或 `HOLD` 以防出錯。*

#### (2) 操作裁決 (Tactical Action) — 手動技術/籌碼操作指令
由 Lucas 或分析師根據均線支撐、主力籌碼分點狀況手動判斷，並登錄於 frontmatter 欄位與內文中：
* **`Tactical Buy`** (逢低分批布局)：股價回測關鍵均線支撐（如 20MA/60MA）、主力分點大買。
* **`Take Profit`** (逢高部分獲利結清)：短期乖離率過高，或觸及壓力位時分批收回現金。
* **`Stop Loss`** (破線停損減碼)：跌破前波低點或關鍵均線防守。
* **`Wait for Setup`** (靜待買點/觀望)：多空拉鋸，等待底部形態確立或帶量突破。

### 3. 正式交付物標準
正式報告（如放在 `30_Projects/` 的報告）應具備獨立閱讀能力，必須包含：
1. **清晰標題與撰寫日期**
2. **So What 核心摘要**
3. **分章節深入剖析**
4. **可落地執行的具體結論與裁決**
5. **明確的引用來源 (Original Documents)**

---

## 🛠️ 第五部分：系統外部工具 (Connectors) 指引
當任務涉及以下工作場景，優先調用對應的 Agent 整合工具：
* **GitHub**：程式庫代碼、Issue 追蹤與 CI/CD 狀態。
* **Gmail & Calendar**：郵件往來、會議排程與每日行程簡報。
* **Drive & Sheets**：雲端檔案共享、多人協作表單。
* **Canva**：商業簡報、視覺圖表設計。
* **Browser (Chrome)**：即時網頁資訊爬取與畫面檢查。
