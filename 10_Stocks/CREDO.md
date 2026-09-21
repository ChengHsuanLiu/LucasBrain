---
type: stock
ticker: "CRDO"
name: "Credo Technology"
market: "US-NASDAQ"
industry: "AI資料中心高速互連晶片（AEC銅纜/SerDes IP/光學DSP/矽光子）"
created: 2026-09-21
updated: 2026-09-21
review_by: 2026-10-21
tags: [investment/target, us-stock, aec, optical, serdes, ai-interconnect]
aliases: [Credo, CRDO, Credo Technology, Credo Technology Group]
currency: "USD"
current_price: 175.95
current_price_date: "2026-09-21"
forward_pe: 25.6
forward_pe_asof: "2026-09-18（股價188.00美元時點）"
valuation_rating: "HOLD"
---
# Credo Technology (CRDO)

> [!WARNING]
> **本頁性質與vault其他個股筆記不同，請注意**：這是Lucas目前完全沒有既有資料的美股標的，全部內容由AI於2026-09-21透過即時網路搜尋（WebSearch/WebFetch）研究後整理，**不是**像聯茂、仁新這些台股筆記一樣，累積自付費法人研報全文、法說會逐字稿、私訪紀錄等一手資料。深度與可靠度天生比vault其他筆記淺一截，尤其「財務模型」與「投資策略評等」是AI自行用公開數字推算，不是真正法人的內部模型。且本頁**不會**被`update_prices.py`等台股自動化腳本更新價格/技術面，也不會被`generate_weekly_focus.py`納入ADD/SELL篩選（因ticker非純數字）。之後若要繼續追蹤，需要手動更新或請Lucas上傳新資料。

## 🎯 投資建議與核心結論 (Executive Summary)
* **核心論點**：
  - **AI資料中心「電轉光」互連的關鍵供應商**：Credo是AEC（Active Electrical Cable，主動式銅纜）品類的開創者，客戶涵蓋Amazon(AWS)、Microsoft、xAI等超大型雲端業者；核心技術優勢是用**成熟製程節點**（12nm/28nm，業界多在5nm）做SerDes/DSP晶片，同時**不生產switch ASIC**、被視為中立供應商——超大型業者不論選Broadcom或Astera Labs的switch，都可以搭配Credo的線材/晶片，這是結構性的護城河論述。
  - **正從單一AEC產品，轉型為「電＋光」全連接矩陣**：2026年陸續透過收購Hyperlume（MicroLED光學互連，2025-09-29完成）、DustPhotonics（矽光子PIC，2026-05-28完成，總代價約13億美元）補齊光學版圖，目前產品線已涵蓋AEC銅纜、SerDes IP授權、PCIe Retimer、光學DSP、矽光子PIC、以及尚在樣品階段的ALC（Active Light Cable，MicroLED主動光纜，FY2027送樣、FY2028量產）。
  - **FY2027(2026/5~2027/4)財測：全年營收年增85%以上，成長引擎正在切換**：Q1 FY27(2026-09-01公布)營收4.79億美元創新高(QoQ+10%/YoY+115%)，優於財測；但值得注意管理層自己講的成長结构——**FY27新增的營收成長，光學業務約佔一半、AEC約佔另一半**，而近期(2026-09-17)已有媒體以「Credo Expands Into Optics as AEC Growth Slows」為題，點出AEC這個核心原始產品成長动能正在放緩、光學是接棒的第二引擎，這跟股價從6月高點(>300美元)拉回約37%的時間點大致吻合，值得持續觀察是「健康的產品組合多元化」還是「核心業務動能見頂」。
  - **法人評等偏多，但評價已不便宜、且近期有目標價下修案例**：19家法人平均評等「Strong Buy」（Strong Buy 21%／Buy 74%／Hold 5%／Sell 0%），平均12個月目標價282.47美元（現價175.95美元，隱含約60%上漲空間）；但同時也觀察到BofA近期把目標價從340美元下修至275美元(仍維持買進)，顯示評價高點後法人也開始收斂樂觀程度，並非一致無腦喊多。
  - **客戶集中度是最大結構性風險**：FY2025一家客戶就佔67%營收，FY2026前十大客戶佔比約90%、其中兩家個別佔比都超過10%——集中度有從「單一巨獸客戶」略微分散到「兩三家巨獸客戶」，但本質上仍是極端集中，任一大客戶砍單或轉單影響會非常直接。
* **評價裁決 (Valuation)**：`HOLD`（依vault既有台股門檻機械判定：forward PE 25.6x落在25~35的HOLD區間邊緣，僅比ADD門檻<25高一點點；但這個門檻是校準給台股中小型零組件供應鏈用的，套在這種美股AI高成長股上未必有意義——19家法人評等平均是「Strong Buy」，兩者明顯衝突，**這裡刻意不強行給單一結論，並列呈現，留給Lucas自己判斷**：quant門檻說貴、sell-side共識說便宜，差異可能來自法人普遍給更高的成長溢價假設。）
* **操作裁決 (Tactical)**：目前無自動化技術面評分（見下方「技術面分析」段落的手動整理版本，訊號本身也偏多空互見）。

---

## 🏢 投資主軸與公司背景 (Company Background)
- **公司**：Credo Technology Group Holding Ltd（開曼群島註冊，NASDAQ: CRDO），無晶圓廠(fabless)的半導體公司，總部美國聖荷西，另有以色列（DustPhotonics團隊）等據點。
- **核心定位**：AI/雲端資料中心裡「機櫃內、機櫃間」高速資料傳輸的連接方案供應商，橫跨銅纜（電）與光學（光）兩種傳輸介質，业务模式包含賣自有品牌線材/晶片（AEC、光學DSP等）與授權SerDes IP給其他晶片商兩種。
- **產業位置類比**：概念上類似台股的[[3081聯亞]]（雷射/光學元件）、[[3363上詮]]（FAU光纖陣列）、[[2345智邦]]（交換器系統整合）、[[3665貿聯]]（線材組裝製造）等公司在AI供應鏈中扮演的「連接層」角色，但Credo更偏向IC設計端（晶片本身），實際的線材組裝很大一部分外包給像貿聯這樣的製造夥伴（見下方「供應鏈與vault既有交叉引用」）。

---

## 📦 產品與服務深度剖析 (Products & Services)
| 產品線 | 說明 | 現況/時程 |
| :--- | :--- | :--- |
| **AEC（Active Electrical Cable，主動式銅纜）** | Credo開創的品類，narrow-gauge銅纜兩端整合retimer/gearbox/FEC電路，56G/112G per lane，涵蓋0.5m-7m傳輸距離；2019年成立HiWire Consortium推動規格標準化，後併入OCP Interconnects/AEC工作小組 | 核心主力產品，已對AWS出貨近100萬條400G AEC，800G版本單價約500美元(2m)；FY27management框架下仍佔約一半的年增營收貢獻，但成長速度據報導已趨緩 |
| **SerDes IP 授權** | 將高速SerDes技術授權給其他晶片商整合進自家產品，屬於毛利率結構中較高的一塊 | 既有業務，具體佔營收比例未揭露 |
| **PCIe Retimer** | 訊號中繼晶片，用於延長/強化PCIe通道訊號完整性 | 既有產品線 |
| **光學DSP (Optical DSP)** | 資料中心光模組核心訊號處理晶片 | FY2027guidance目標單項超過1億美元 |
| **Zero-Flap Optics** | 訴求提升光學連結穩定性(降低斷線/重連, "flap")的光學方案 | FY2027guidance目標單項超過1億美元 |
| **矽光子PIC (Silicon Photonics PIC)** | 光學收發器用的矽光子光子積體電路，透過收購DustPhotonics取得 | 2026-04-13宣布收購、2026-05-28完成，代價：預付7.5億美元現金+約92萬股，另有最高約321萬股或有對價(視財務里程碑)，總代價約13億美元；FY2027guidance目標單項超過1億美元 |
| **ALC（Active Light Cable，主動光纜）** | 透過收購Hyperlume(2025-09-29完成)取得的MicroLED光學互連技術，訴求比傳統CPO(共同封裝光學)更省電、更可靠，傳輸距離可達30米，定位為AEC與CPO之間的第三選項 | 尚未量產：FY2027送樣、FY2028量產爬坡 |

**FY2027(2026/5~2027/4) 產品組合guidance重點**：管理層目標光學類業務(Zero-Flap Optics+矽光子PIC+光學DSP)合計超過6億美元，且明講「FY27新增的營收成長，光學業務跟AEC業務各貢獻約一半」——換句話說，過去純靠AEC一條產品線衝刺的成長模式正在轉變為「電+光」雙引擎，這既是分散風險的正面訊號，也隱含AEC單一產品線的成長天花板可能比市場先前預期更快浮現。

---

## ⚔️ 核心競爭力與同業比較 (Competitive Positioning & Peers)
| 公司 | 定位 | 相對Credo的意義 |
| :--- | :--- | :--- |
| **Astera Labs (ALAB)** | Taurus/Scorpion switch、CXL、UALink、光學與客製化連接方案，正往rack-scale系統擴張 | 被多份報導點名為Credo在「主動線纜+光學DSP」領域最直接的利基競爭對手 |
| **Marvell (MRVL)** | 光學DSP市佔約70%，Ara DSP採3nm製程、是業界首款1.6T產品，模組功耗可降20%以上 | 在光學DSP的技術/製程領先幅度目前大於Credo，是光學這塊最大的競爭壓力來源 |
| **Broadcom (AVGO)** | Switch ASIC龍頭 | 並非直接競品，但客戶選Broadcom switch時，Credo線材仍可搭配銷售——這正是Credo「中立供應商」定位的具體例子 |

**護城河論述**：
1. **成熟製程策略**：SerDes/DSP晶片用12nm/28nm等N-1甚至更舊的成熟節點，而非業界主流的5nm——換取更低成本、更高良率與更省電的設計空間，屬於「用工程取巧而非製程堆料」的差異化路線。
2. **中立供應商角色**：不做switch ASIC，避免被單一晶片生態系綁定，讓自己的線材/光學方案可以搭配任何一家switch供應商銷售，降低了「選邊站」的商業風險。
3. **⚠️ 風險面**：Marvell在光學DSP的製程與世代領先（已量產1.6T），若光學DSP真的成為Credo下一階段的主力成長引擎，Credo在這塊必須直接面對製程/世代都佔優勢的Marvell，護城河強度不如AEC銅纜那塊清楚。

---

## 💰 財務數據與估值 (Financials & Valuation)

### 近期營運數字
| 期間 | 營收 | 年增/季增 | 獲利指標 | 備註 |
| :--- | :--- | :--- | :--- | :--- |
| FY2026(全年) | 13.4億美元 | YoY +205.7% | — | 財年約對應2025/5~2026/4 |
| TTM(截至最近季) | 15.9億美元 | YoY +165.1% | 淨利5.38億美元(YoY+330%)、EPS約2.83美元 | trailing數字含較大幅度成長基期效應，需留意非線性外推 |
| Q1 FY2027(2026-09-01公布) | 4.79億美元 | QoQ+10%／YoY+115%，創新高 | Non-GAAP EPS 1.20美元(優於預期1.17美元)；Non-GAAP毛利率68%；Non-GAAP淨利2.363億美元 | 優於財測，帶動股價當日反應 |
| Q2 FY2027 guidance | 5.25~5.35億美元 | — | Non-GAAP毛利率67~69%；Non-GAAP營業費用1.00~1.05億美元 | 公司自結財測 |
| FY2027全年guidance | — | YoY +85%以上 | 光學業務目標>6億美元(Zero-Flap Optics/矽光子PIC/光學DSP各>1億美元) | 管理層框架：2H27為成長加速期 |

### 估值與法人評等（資料時點：2026-09-21，多來源交叉比對）
- **股價**：175.95美元（2026-09-21），52週區間86.49~308.67美元——波動區間極大，Beta 3.23屬高波動股。
- **市值**：約330.6億美元。
- **本益比**：trailing P/E約66x（受惠爆發性成長基期，數字參考性有限）；forward P/E約25.6x（2026-09-18、股價188美元時點資料，現價175.95美元下forward P/E會略低於此，但缺乏當下更新的一致性EPS共識來源，暫列此區間供參考）。
- **法人評等**：19家法人，平均「Strong Buy」（Strong Buy 21.05%／Buy 73.68%／Hold 5.26%／Sell 0%）；12個月平均目標價282.47美元（另一資料源：16家法人平均274.42美元，區間206~350美元）；BofA近期(確切日期未查得)將目標價由340美元下修至275美元、仍維持買進評等——顯示法人樂觀程度在股價回落後也有收斂跡象，不是單向上修。
- **⚠️ 數據一致性提醒**：不同財經網站對「當前股價」「均線水位」的數字在同一週內就有明顯落差（例如同樣號稱9月中旬的資料，股價從168到188美元都有），研判是各站台快取時間點不同、加上該股近期波動極大所致；若要據此做實際交易判斷，建議直接查證即時報價，不要只信任本筆記的靜態數字。

---

## 💵 現金流量與資產負債表 (Cash Flow & Balance Sheet)
- **Q1 FY2027自由現金流**：8,290萬美元（資本支出730萬美元），營運現金流9,020萬美元(季減9,200萬美元，主因營運資金變動)。
- **現金部位**：Q1 FY2027季底現金及約當現金7.643億美元，季減約6.79億美元——主因DustPhotonics收購支付現金對價。
- **負債**：公開資料未查得明確財報揭露數字；公司對外表態流動性「舒適」，預期營運現金流可望回升至每季約2億美元的水準。
- **解讀**：DustPhotonics收購用掉大部分現金儲備，是典型「用資產負債表換技術版圖」的動作，短期現金部位轉薄，需要留意後續季度自由現金流能否如公司所說回升到2億美元/季的水準，這會是驗證「收購有沒有拖累財務體質」的關�keta指標。

---

## 📈 技術面分析 (Technical Analysis)
- **價格趨勢**：6月中旬一度衝上300美元以上高點，之後拉回，至9月中旬已較高點下跌約37%，目前在170~190美元區間整理。
- **均線**（來源：2026-09-18某資料站快照，數字與其他來源有落差，僅供參考）：50日均線約236.70美元、200日均線約173.60美元；不同來源對「股價是否站上200日均線」的判讀不一致。
- **動能指標**：14日RSI約54（中性）；MACD於2026-08-21轉負；10日均線於2026-08-28死叉跌破50日均線——這兩個訊號偏空。
- **綜合解讀**：多空訊號互見，比較像是「急漲後进入修正/整理階段」，不是單邊趨勢，且如前述財務面提到的「AEC成長放緩、光學接棒」敘事轉變时间點大致重疊，可以合理推測近期拉回除了單純估值消化，也夾雜市場在消化「成長引擎交棒」的敘事風險，不完全是技術面自身的問題。

---

## ⚠️ 風險與待驗證事項 (Risks & Open Questions)
- **客戶集中度極高（結構性風險，非短期問題）**：FY2025單一客戶佔67%營收；FY2026前十大客戶約佔90%、兩家個別客戶各超過10%。集中度雖然比FY2025的「單一巨獸」略為分散，但本質仍是少數幾個巨型雲端業者主導營收，任一家轉單/砍單的影響會非常直接且劇烈。
- **AEC核心產品成長動能是否真的放緩**：這是目前最關鍵、也最沒有定論的問題——公司財測框架(光學/AEC各佔一半新增成長)本身就隱含AEC成長率正在被光學業務「稀釋佔比」，媒體報導也已經用「AEC Growth Slows」下標題，但目前查到的資料還不足以判斷這是「AEC絕對數字放緩」還是「AEC持續成長、只是光學成長更快導致佔比下降」兩種完全不同性質的情況，需要後續財報揭露更細的產品別數字才能確認。
- **光學DSP領域面對製程領先的Marvell**：Marvell在光學DSP的製程世代（3nm、1.6T量產）目前領先，若光學真的成為Credo下一階段主力，這塊的競爭壓力比AEC領域更直接。
- **評價是否已反映成長**：法人平均目標價隱含約60%上漲空間、評等接近一致偏多，但quant角度的forward PE(~25.6x)在vault既有台股門檻下只是勉強HOLD，兩種判斷角度的落差本身就是一個需要持續觀察、而非直接採信單一結論的訊號。
- **DustPhotonics併購整合成效未知**：矽光子PIC是全新技術領域，併購案剛完成不到半年，管理層對其FY27貢獻(>1億美元)的財測能否兌現，是驗證這筆併購成功與否的第一個檢查點。
- **本頁所有數字皆來自公開網路資料，非一手研報/法說逐字稿**：與vault既有台股筆記的資料可信度基礎不同，任何數字建議在真正下決策前再次查證最新公開財報/法說會內容。

---

## 🤝 供應鏈與vault既有交叉引用 (Supply Chain Cross-References)
- **[[3665貿聯]]（貿聯-KY）**：Credo是貿聯2Q26前十大客戶之一，營收占比約8-9%（貿聯負責Credo線材相關的組裝製造）。貿聯筆記裡已有UBS於2026-07-08參加「Credo台灣NDR(Non-Deal Roadshow)」後的既有記錄：**Credo對AEC TAM持續看多，8-10月OCP展會展示ALC，且MediaTek/AUO開始評估ALC方案**——這則MediaTek/AUO評估ALC的細節，本次網路搜尋並未能獨立查證到公開報導，屬於Lucas既有分析師資源才拿得到的資訊，正好印證「vault既有一手資料 vs. AI公開網路搜尋」的深度落差，建議後續若有機會可向同一批分析師追問ALC最新進度。
- **概念上相關但vault尚未追蹤的個股**：[[3081聯亞]]（雷射元件）、[[3363上詮]]（FAU光纖陣列）、[[2345智邦]]（交換器系統整合）——這幾檔台股都在同一個「AI資料中心高速互連」供應鏈上，但屬於不同環節（Credo是連接晶片/線材設計端，這幾檔多是上游元件或下游系統整合），非直接同業競爭關係。

---

## 📅 近期重大事件時間軸 (Recent Events Timeline)
- **2025-09-29**：完成收購Hyperlume（MicroLED光學互連技術），為後續ALC(Active Light Cable)產品線鋪路。
- **2026-04-13**：宣布收購DustPhotonics（矽光子PIC技術）。
- **2026-05-28**：完成DustPhotonics收購，總代價約13億美元。
- **2026-09-01**：公布Q1 FY2027財報，營收4.79億美元創新高，優於財測。
- **2026-09-08**：法說會後續analyst反應與目標價修訂陸續出爐（含BofA下修目標價案例）。
- **2026-09-17**：媒體報導聚焦「Credo Expands Into Optics as AEC Growth Slows」敘事轉變。
- **待驗證**：FY2027下半年（約2026/11~2027/4）是否如財測所言迎來加速成長，是驗證目前多空論點的下一個關鍵時間窗口。

---

## 📄 原始文件與參考來源 (Sources)
> 以下皆為2026-09-21透過WebSearch/WebFetch取得之公開網路資料，非vault既有付費研報/一手記錄；標記日期為資料本身內容所屬時間，非查詢時間。
- [Credo (CRDO) Q1 2027 Earnings Call Transcript](https://www.theglobeandmail.com/investing/markets/stocks/CRDO-Q/pressreleases/4501263/credo-crdo-q1-2027-earnings-call-transcript/) — Q1 FY27財報電話會議逐字稿
- [Credo Technology Group Holding Ltd Reports First Quarter of Fiscal Year 2027 Financial Results](https://investors.credosemi.com/news-events/news/news-details/2026/Credo-Technology-Group-Holding-Ltd-Reports-First-Quarter-of-Fiscal-Year-2027-Financial-Results/) — 公司官方Q1 FY27法說新聞稿
- [Credo Technology Group Holding (CRDO) Stock Price & Overview - stockanalysis.com](https://stockanalysis.com/stocks/crdo/) — 估值/財務數字（2026-09-18時點）
- [Credo Technology Group (CRDO) Stock Forecast and Price Target 2026 - MarketBeat](https://www.marketbeat.com/stocks/NASDAQ/CRDO/forecast/) — 法人評等/目標價彙整
- [These Analysts Revise Their Forecasts On Credo Technology Group Following Q1 Results - Benzinga](https://www.benzinga.com/analyst-stock-ratings/price-target/26/09/61572886/these-analysts-revise-their-forecasts-on-credo-technology-group-following-q1-results) — 財報後法人目標價異動
- [$500 purple cables put Credo in middle of the AI boom - CNBC](https://www.cnbc.com/2025/10/17/500-purple-cables-put-credo-in-middle-of-the-ai-boom.html) — AEC產品/客戶背景報導
- [Credo AECs - Chipstrat](https://www.chipstrat.com/p/credo-aecs) — AEC技術與競爭定位分析
- [Credo's Free Cash Flow Soars: Can the Momentum Continue? - Yahoo Finance](https://finance.yahoo.com/markets/stocks/articles/credos-free-cash-flow-soars-144300383.html) — 現金流分析
- [Credo Technology Group (CRDO) Free Cash Flow 2026 - StockTitan](https://www.stocktitan.net/financials/CRDO/free-cash-flow/) — FCF歷史數字
- [Credo Completes Acquisition of DustPhotonics](https://investors.credosemi.com/news-events/news/news-details/2026/Credo-Completes-Acquisition-of-DustPhotonics/default.aspx) — DustPhotonics收購完成公告
- [Credo Agrees to Acquire DustPhotonics](https://www.businesswire.com/news/home/20260413933103/en/Credo-Agrees-to-Acquire-DustPhotonics-Accelerating-Expansion-into-Silicon-Photonics-and-Next-Generation-Optical-Connectivity) — DustPhotonics收購宣布細節/代價結構
- [Credo Expands Into Optics as AEC Growth Slows - Seoul Economic Daily](https://en.sedaily.com/finance/2026/09/17/credo-expands-into-optics-as-aec-growth-slows) — AEC成長放緩/光學接棒敘事
- [ALAB Broadens Leo Portfolio: Can It Stay Ahead of MRVL & CRDO? - Yahoo Finance](https://finance.yahoo.com/technology/articles/alab-broadens-leo-portfolio-stay-154200386.html) — Astera Labs同業比較
- [Credo to Acquire Hyperlume, Inc. - 官方公告](https://investors.credosemi.com/news-events/news/news-details/2025/Credo-to-Acquire-Hyperlume-Inc-/default.aspx) — Hyperlume收購公告
- [Credo Acquires Hyperlume, Taps MicroLED Tech for AI Data Centers - Yahoo Finance](https://finance.yahoo.com/news/credo-acquires-hyperlume-taps-microled-122100852.html) — ALC產品規劃細節
- [CRDO Technical Analysis - Investing.com](https://www.investing.com/equities/credo-technology-holding-technical) — 技術面數據
- 10_Stocks/3665貿聯.md 內部既有記錄（2026-07-08 UBS「Credo台灣NDR」段落）——vault既有交叉引用來源
