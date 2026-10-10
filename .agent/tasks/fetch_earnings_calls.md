# 任務工作流：法說會時程追蹤 (Earnings Calls Tracker)

> [!NOTE]
> 每天盤後自動抓取全市場法說會時程，存進 SQLite 資料庫並偵測異動（改時間／改地點／簡報上傳／疑似取消）。
> 資料是「多公司 x 多場次 x 隨時間會變」的結構化資料，需要跨日期比對與異動歷史，所以用資料庫而非 Markdown。
> 程式：`.agent/scripts/fetch_earnings_calls.py`（入口）、`.agent/scripts/lib/earnings_calls.py`（抓取/解析/合併/儲存）。
> 資料庫：`.agent/data/earnings_calls.db`（已加入 `.gitignore`，不進 git；要備份請自行複製）。

## 📋 排程

| 項目 | 內容 |
| :--- | :--- |
| 排程名稱 | `LucasBrain_EarningsCalls`（Windows Task Scheduler，每天 18:30，錯過會補跑） |
| 執行方式 | `run_scheduled_report.ps1 -ScriptName fetch_earnings_calls.py`（與日報、動能篩選同一個包裝腳本） |
| 每次動作 | 抓 Yahoo（未來全部已公告場次）+ IR 議合平台（本月起共 3 個月），合併後寫入資料庫 |
| 結束碼 | 任一來源失敗為 1（成功的來源仍照常寫入），Task Scheduler 的「上次執行結果」會顯示 |

> [!WARNING]
> `.agent/scheduled_logs/` 內的中文會是亂碼（包裝腳本以 Big5 解碼 Python 的 UTF-8 輸出，日報與動能篩選的日誌同樣如此）。
> **排程是否正常請用 `--status` 查**，不要看日誌。

## 🔧 常用指令

```powershell
python .agent/scripts/fetch_earnings_calls.py --status                 # 兩個來源最近的抓取結果 + 健康檢查（超過36小時沒成功會警告）
python .agent/scripts/fetch_earnings_calls.py --show                   # 未來14天場次（★ = 10_Stocks 已有該個股頁）
python .agent/scripts/fetch_earnings_calls.py --show --days 45 --vault-only
python .agent/scripts/fetch_earnings_calls.py --show --ticker 2330     # 單一公司全部場次，含摘要與簡報連結
python .agent/scripts/fetch_earnings_calls.py --changes --days 7       # 近7天異動
python .agent/scripts/fetch_earnings_calls.py --dry-run                # 只抓取+解析，不寫資料庫
python .agent/scripts/fetch_earnings_calls.py --rederive               # 改進 regex 規則後重算推導欄位（不連網、不洗掉異動歷史）
python .agent/scripts/fetch_earnings_calls.py --backfill 2026-01       # 回補歷史（約2.5分鐘）
```

## 📄 報告：`g EarningsCalls`

```powershell
python .agent/scripts/generate_earnings_calls_report.py                  # 預設：全市場14天、追蹤個股30天、異動7天
python .agent/scripts/generate_earnings_calls_report.py --days 21 --vault-days 45 --change-days 10
python .agent/scripts/generate_earnings_calls_report.py --refresh        # 先跑一次 fetch_earnings_calls.py 再產生
```

輸出 `30_Projects/Earnings_Calls/{YYYYMMDD}_宇宙資本_法說會時程.md` 與 `.pdf`（同一天重跑會覆蓋）。內容依序為：追蹤個股（10_Stocks 已有個股頁者）→ 近 N 天異動 → 全市場時程。
報告只讀資料庫、不連網，頂端標示資料更新時間，超過 36 小時未成功更新會警告。
- PDF 轉換會移除所有 emoji（含 ★），所以追蹤個股在報告裡用「◆」標示。
- 「新增」不含追蹤起始日（資料庫第一次抓取那天，含回補）以前入庫的存量，所以**剛開始的第一天異動區一定是空的**，之後才會累積。
- 異動區對追蹤個股逐筆列出；其他個股每類最多列 15 筆（旺季「簡報上傳」「新增」可達數百筆），超過的只顯示筆數，完整內容用 `--changes` 查。

### 併入盤後日報

`g Daily_Report` 的最後一節「七、法說會時程」與上述報告是同一份內容（`generate_earnings_calls_report.build_embedded_section()`）。
日報 16:30 產生、本資料庫 18:30 才更新，所以日報產生時若資料超過 3 小時沒更新，會先自動抓取一次；失敗就沿用既有資料，
該節出任何錯誤都只顯示「本次略過」，不影響日報其他部分。

## 🗂️ 資料來源與取捨

| 來源 | 狀態 | 備註 |
| :--- | :--- | :--- |
| Yahoo 股市行事曆 | ✅ 使用 | 唯一提供「國內/國外」；代號帶 `.TW`/`.TWO` 可分上市/上櫃；摘要是縮寫版 |
| 臺灣指數公司 IR 議合平台 | ✅ 使用 | 原文摘要、多日活動日期區間、已結束場次的簡報下載連結 |
| 玩股網 | ❌ 不用 | JSON 端點需前端算出的簽章（純 HTTP 回 400），要用就得逆向其防爬機制；且內容與上兩者重疊 |
| MOPS 公開資訊觀測站 | ❌ 不用 | 新版法說會頁強制輸入單一公司代號；舊版整批端點被反爬蟲封鎖 |
| TWSE / TPEx OpenAPI | ❌ 沒有 | 官方 OpenAPI 沒有法說會資料集 |

實測**兩個來源各有漏網場次**（Yahoo 缺的 IR 有、IR 缺的 Yahoo 有），所以取聯集。同一欄位衝突時以 IR（原文）為準，`scope` 以 Yahoo 為準。

## 🗃️ 資料表

- **`events`**：每場一列（目前狀態）。自然鍵 `(stock_code, event_date, event_time)`。欄位：公司/市場別、日期/結束日(多日活動)/時間、
  `scope`(國內/國外)、`location`、`format`(線上/實體/電話會議/實體+線上)、`organizer_type`(券商主辦/其他主辦/公司自辦/未明)、`organizer`、
  `event_kind`(法說會/券商論壇/研討會/海外路演NDR/座談會)、`event_series`(如 20th QIC CEO Week)、`period_hint`(摘要提到的財報期別)、`webcast_url`、
  `summary`、`materials`(簡報檔 JSON)、`sources`、`status`(active/missing)、`first_seen/last_seen/last_changed`。
- **`event_changes`**：欄位異動歷史。只記錄來源欄位的變動（時間/結束日/地點/摘要/國內外/簡報），regex 推導欄位只默默更新不記錄。
- **`fetch_runs`**：每次抓取每個來源的結果（筆數/略過列數/成敗/錯誤訊息），`--status` 的資料來源。

## ⚠️ 設計上的重要決定與已知限制

1. **「疑似取消」只是推論，不是事實。** 判定條件：某未來場次先前被來源 S 列出，這次 S 抓取成功、場次日期落在 S 的涵蓋範圍內、
   卻沒被列出；所有來源都不再列出才標 `missing`。公司真的取消、改期，或來源單純漏列，都會是這個結果。
   同一檔同時「新增」與「疑似取消」時，執行結果會另列「疑似改期」。
2. **來源壞掉時不會誤判。** 抓到 0 筆、略過列超過 20%、或筆數低於資料庫已知筆數的 30%，該來源本次不用於判定「疑似取消」
   （例如頁面只載入一半，不能把其餘場次全標成取消）。
3. **IR 平台會把公司「上一份簡報」掛在沒有自己簡報的場次上**（實測 5,069 份檔案中 628 份被掛在 2 個以上場次）。
   寫入前做歸屬判定：同一公司的同一份檔案出現在多個場次時，只留給場次日期離檔案上傳日（檔名內的 YYYYMMDD）最近的那場。
   只出現在單一場次的檔案無從比較；`--show --ticker` 會對「上傳日距場次超過 10 天」者標 ⚠。
4. **推導欄位是 regex 規則，不是語意理解。** 摘要是公司自由填寫的文字，主辦/形式/期別會有漏判（實測約 6% 的場次主辦為「未明」，
   多半是來源文字本身沒講，如「本公司財務業務相關資訊說明」，或是多家券商/共同主辦這類規則刻意不猜的情況）。`period_hint` 只是摘要字面所述，
   公司偶爾會寫錯季別。**主辦名稱未做別名正規化**：同一家券商會以不同寫法分開出現（`花旗證券`/`Citi`、`高盛證券`/`Goldman Sachs`、
   `BofA Securities`/`BANK OF AMERICA`），依主辦統計時要自行合併。
   - `event_kind` 把「券商論壇/研討會」（J.P. Morgan Taiwan CEO-CFO Conference、BofA Asia Tech 等，多家公司輪流上台）與公司自己的「法說會」分開；
     實測約 31% 的場次屬於前者，不分開會高估公司開法說會的頻率。
   - 改進 regex 規則後，執行 `--rederive` 用資料庫已存的文字重算推導欄位即可，**不要刪庫重建**（會洗掉 `event_changes` 異動歷史）。
     只有改動了「抓取/解析」本身（如新增欄位）才需要 `--backfill`。
5. **多日活動**（如 QIC CEO Week 10/13~10/14）以首日為 `event_date`，結束日在 `event_end_date`。
6. **IR 偶爾分不出市場別**（市場別「全部」比「上市+上櫃」多出興櫃/其他），這類 `market` 留空；Yahoo 的 `.TW`/`.TWO` 可補。
7. Yahoo 少數公司只顯示純代號沒有 `.TW`/`.TWO`（如已下市者），`market` 一樣留空。

## 🔗 與其他功能整合（目前未做，未來可接）

`lib/earnings_calls.py` 的 `query_upcoming()`、`load_vault_tickers()` 可直接供其他腳本呼叫，例如：
`generate_invest_timeline.py` 補入追蹤個股的法說會日期、`generate_weekly_report.py` 的「近期關注事件」段落自動帶入下週法說會。
