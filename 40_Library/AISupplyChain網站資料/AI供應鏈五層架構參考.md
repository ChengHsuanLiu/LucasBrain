---
type: reference
title: "AI 供應鏈五層架構參考 (Supply Chain Map)"
created: 2026-07-10
updated: 2026-07-10
review_by: 2026-10-10
tags: [reference, taxonomy, ai-supply-chain]
source_type: web_capture
source_url: "https://supply-chain-map.pages.dev/learn"
---

# AI 供應鏈五層架構參考

> [!NOTE]
> 擷取自外部網站 [supply-chain-map.pages.dev/learn](https://supply-chain-map.pages.dev/learn)（研究截止 2026-07-04），非本庫原創研究。此頁作為**分類框架參考**，供未來規劃 Garden 產業頁面與概念股分類時對照使用，不直接驅動 DailyReport 計算。

## 核心框架：五層資金傳導鏈

該網站依「資金與需求由下游往上游傳導」的邏輯，將 AI 供應鏈拆成五層（144 檔正式收錄公司、29 個分類）：

> CSP capex → GPU/ASIC 晶片設計 → 晶圓代工＋先進封裝 → HBM 記憶體 → 設備／材料／載板 → 伺服器 ODM／散熱電源／網通

| 層級 | 說明 | 代表公司 |
| :--- | :--- | :--- |
| Tier 1：需求端 | AI Labs 與雲端平台，消耗運算容量 | OpenAI、Anthropic、xAI、Microsoft、Google、Amazon、Meta、Oracle、CoreWeave |
| Tier 2：晶片層 | GPU/ASIC 設計、晶圓代工、記憶體、封測 | NVIDIA、AMD、TSMC(2330)、聯電(2303)、Broadcom、聯發科(2454)、創意(3443)、日月光投控(3711)、Micron、SK Hynix、Samsung |
| Tier 3：上游 | 設備、材料、載板 | ASML、應材(AMAT)、Lam Research、KLA、信越化學、SUMCO、南電(8046)、景碩(3189)、台光電(2383) |
| Tier 4：系統層 | 散熱、電源、伺服器、網通 | Vertiv、台達電(2308)、緯穎(6669)、鴻海(2317)、廣達(2382)、智邦(2345) |
| Tier 5：新興環節 | 被動元件、類比IC、機器人 | 村田(Murata)、國巨(2327)、TI、ADI、Tesla Optimus、Fanuc |

## 分類方式（可與本庫概念股分類對照）

* **商業模式分類**：IDM／Fabless／Foundry／OSAT／ODM。
* **上市地區色碼**：藍=美股、綠=台股、紅=日股、灰=未上市/N/A。
* **54 張技術概念卡**：以圖解說明各元件如何實體/功能整合（例如 HBM 疊構、TSV、CoWoS 封裝彼此串接的方式）。
* **瓶頸與落後指標追蹤**：強調各層之間的稀缺性與傳導延遲（例如 HBM 僅三家供應商、ASML EUV 獨占、台灣 ODM 集中度）。

## 完整分類與公司清單（依 Tier 分節）

### Tier 1：需求端
- **AI Labs/Models**：OpenAI、Anthropic、xAI、SoftBank(9984)
- **雲端/軟體平台**：Microsoft(MSFT)、Google(GOOGL)、Amazon(AMZN)、Meta(META)、Oracle(ORCL)、CoreWeave(CRWV)、Palantir(PLTR)、Fujitsu(6702)、Cloudflare(NET)、CrowdStrike(CRWD)、Snowflake(SNOW)

### Tier 2：晶片層
- **晶片設計/EDA/IP - GPU**：NVIDIA(NVDA)、AMD(AMD)、Qualcomm(QCOM)、Apple(AAPL)、聯發科(2454)
- **客製化 ASIC 設計**：Broadcom(AVGO)、Marvell(MRVL)、創意(3443)、Socionext(6526)
- **特殊 IC**：聯詠(3034)、譜瑞(4966)、祥碩(5269)、群聯(8299)、瑞薩(6723)
- **EDA/IP**：Synopsys(SNPS)、Cadence(CDNS)、ARM(ARM)、力旺(3529)
- **晶圓代工**：Intel(INTC)、台積電(2330)、聯電(2303)、Rapidus、世界先進(5347)
- **記憶體/HBM**：Micron(MU)、SK Hynix、Samsung
- **封裝測試**：日月光投控(3711)、京元電(2449)、力成(6239)、Amkor

### Tier 3：上游（設備／材料／載板）
- **前段設備**：應材(AMAT)、Lam Research(LRCX)、KLA(KLAC)、東京威力科創(8035)、雷射科(6920)、SCREEN(7735)、Onto Innovation(ONTO)
- **測試設備**：愛德萬(6857)、Teradyne(TER)
- **先進封裝設備**：弘塑(3131)、辛耘(3583)、萬潤(6187)、迪思科(6146)
- **材料**：信越化學(4063)、SUMCO(3436)、Hoya(7741)、Resonac(4004)、東京應化(4186)、味之素(2802)、Entegris(ENTG)
- **載板/PCB**：欣興(3037)、景碩(3189)、台光電(2383)、金像電(2368)、Ibiden(4062)、新光電氣(6967)、南電(8046)、台燿(6274)

### Tier 4：系統層
- **散熱/電源/機構**：奇鋐(3017)、雙鴻(3324)、健策(3653)、Vertiv(VRT)、台達電(2308)、光寶科(2301)、日立(6501)
- **伺服器/ODM**：Dell(DELL)、HPE(HPE)、Supermicro(SMCI)、鴻海(2317)、廣達(2382)、緯創(3231)、緯穎(6669)、英業達(2356)、技嘉(2376)、華碩(2357)
- **網通/光通訊**：Arista(ANET)、智邦(2345)、Ciena(CIEN)、Astera Labs(ALAB)、Credo(CRDO)、Coherent(COHR)、Lumentum(LITE)、Fabrinet(FN)、聯亞(3081)、華星光(4979)、光聖(6442)、波若威(3163)、上詮(3363)
- **光纖**：Fujikura(5803)、Furukawa(5801)、Sumitomo(5802)

### Tier 5：新興環節
- **被動元件**：國巨(2327)、華新科(2492)、村田(Murata)、TDK(6762)、太陽誘電(6976)
- **電源/類比IC**：Monolithic Power(MPWR)、Navitas(NVTS)、TI(TXN)、ADI(ADI)、onsemi(ON)、ROHM(6963)、富士電機(6504)、三菱電機(6503)
- **機器人**：Tesla(TSLA)、Intuitive Surgical(ISRG)、所羅門(2359)、Fanuc(6954)、Yaskawa(6506)、Keyence(6861)、上銀(2049)、亞德客(1590)、SMC(6273)、Nabtesco(6268)、Harmonic Drive(6324)

---

## 📄 原始文件與連結 (Original Documents)
* [supply-chain-map.pages.dev/learn](https://supply-chain-map.pages.dev/learn) - AI 供應鏈五層架構與 144 檔公司地圖 (擷取於 2026-07-10，站方研究截止 2026-07-04)
