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
* **`10_Stocks/`**：個股專屬頁面，命名格式為 `[股票代號][名稱].md` (例如 `3189景碩.md`)。
* **`20_Garden/`**：結構化的產業知識筆記（如 `CCL銅箔基板.md`），注重長期的產業演化與技術壁壘。
* **`30_Projects/`**：專案報告與投資決策等可交付的完整成果。
* **`98_Archives/`**：已處理完成的原始素材與歷史報告存檔區。
* **`99_Templates/`**：存放 Stock/Industry 範本、系統指令、工作流與腳本。

### 2. Obsidian 筆記規範
* **標準範本**：
  * 個股筆記格式遵循 [Template_Stock.md](file:///c:/Users/User/Desktop/LucasBrain/99_Templates/Template_Stock.md)
  * 產業筆記格式遵循 [Template_Industry.md](file:///c:/Users/User/Desktop/LucasBrain/99_Templates/Template_Industry.md)
* **雙向連結 (WikiLinks)**：在更新內文時，提及任何相關個股或關鍵技術，必須自動用雙中括號連結（如 `[[2383台光電]]`、`[[CoWoS]]`）。
* **So What? 測試**：每一筆新增的資訊都要能回答「這對投資決策有什麼影響？」。
* **資訊完整性**：重構時絕不刪除既有資訊，暫時無用的宏觀背景可移入個股的 `## 📝 歷史筆記與會議紀要` 封存。

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
* **無損疊加**：將新資訊填入對應的 `10_Stocks/` 或 `20_Garden/` 頁面。
* **時序排列**：**時間近的資訊排在上方，舊的在下方**。
* **衝突處理**：新舊數據不同時**不可直接覆蓋**，必須在頁面上**並列標註**（如：「`2026-06-22` 大摩預估 2027 EPS 為 42.6 元；相較 `05-25` 高盛預估 30 元有所調升」）。
* **補齊 WikiLinks**：自動為文中出現的廠商加上雙中括號連結。

#### 步驟 4：歸檔 raw file (Archive)
將 `00_Inbox/` 中處理完畢的檔案移動至 `98_Archives/` 目錄。

#### 步驟 5：更新統計目錄 (Index)
更新 [index.md](file:///c:/Users/User/Desktop/LucasBrain/index.md) 的個股/產業最新統計數量與最近更新時間。

#### 步驟 6：追加歷史日誌 (Log)
在 [log.md](file:///c:/Users/User/Desktop/LucasBrain/log.md) 的尾端追加一行紀錄，格式如下：
`## [YYYY-MM-DD] ingest | 檔案名稱 | 影響的 Stocks 及 Garden`

#### 步驟 7：版本管理與回報 (Commit & Push)
完成後，主動為 Lucas 整理本次 commit 的簡短標題，詢問是否執行 `git commit` 與 `git push`。

---

## 📊 第四部分：投研分析與交付物標準

### 1. 投研分析維度
分析個股或產業鏈時，建議從以下面向切入，確保邏輯嚴密：
* **基本面**：營收與 EPS、產能規劃、BOM 表升級（如 Blackwell 規格變化）。
* **籌碼面**：大戶分點進出、籌碼集中度。
* **技術面**：價格與均線趨勢。
* **風險評估**：多情境敏感度分析（如價格不漲 vs. 漲價 30% / 50% 對 EPS 的影響）。

### 2. 投資裁決與標記
若 Lucas 要求對個股給出結論，必須明確下達以下裁決之一，並附帶具體原因：
* **`ADD`** (加碼) | **`HOLD`** (續抱觀察) | **`REDUCE`** (減碼) | **`SELL`** (避開)

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
