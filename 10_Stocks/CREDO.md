---
type: stock
ticker: "CRDO"
name: "Credo Technology"
market: "US-NASDAQ"
industry: "AI資料中心高速互連晶片（AEC銅纜/SerDes IP/光學DSP/矽光子）"
created: 2026-09-21
updated: 2026-10-12
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
  - **⚠️ 2026-10-12 新增（一手管理層溝通，補足本頁原本僅有的公開網路資料）：2026-10-07 Credo管理層Call Memo(Judy Hsiao)——1.6T AEC營收2027財年Q4(約4-5月)或2028財年初開始、2027日曆年中明顯放量，首個1.6T商業訂單為Scale-Up銅纜Retimer(未來9-12個月US$5,000萬採購單)，ZeroFlap Optics以專屬遙測/診斷為差異化，BizLink「非Credo業績代理指標」**（來源：`[[20261011_182620_file.docx]]`，中英雙語call memo；與談內容為Credo管理層對投資人問答，原文標題「202610.07 CREDO callmemo」）：**1.6T AEC**：確認1.6T AEC營收將於**FY27 Q4(約2027年4-5月)或FY28初期**開始，預期2027日曆年中起顯著放量；預計由**多家超大型雲端客戶**共同部署而非單一客戶；1.6T成本增幅低於ASP提升幅度→毛利率比前幾代更好；最長傳輸約6公尺(800G世代為7公尺)；800G(100G/lane)近期才躍升為AEC主要營收來源，25G/50G/lane仍貢獻相當比重；絕大多數AEC纜線≤3公尺，6-7公尺僅個位數百分比；1.6T產品家族橫跨光學(Scale-Out)、AEC(Scale-Out)、Retimer(Scale-Up)與PIC(Scale-Up)。**首個1.6T商業捷報**：Scale-Up**銅纜Retimer**取得**未來9-12個月高達US$5,000萬採購訂單**。**ZeroFlap Optics差異化**：市場上唯一能在光收發器提供豐富診斷與即時鏈路健康數據(可辨識ESD損傷、系統整合時光纖未對準、光纖灰塵造成光子反射等根因，由Credo專用DSP偵測)，同業(旭創、易飛揚、AOI、Coherent/Lumentum)缺乏專用DSP/軟體/韌體；僅買獨立PIC無法享有此功能(診斷能力來自整顆收發器內嵌的DSP/軟體/韌體)；Marvell理論上可複製但會侵蝕自家DSP業務與損害客戶(Inphi/Eoptolink)關係→Credo約有一年先發優勢。**客戶價值**：商品化光模組叢集上線需4-6週(鏈路抖動與試錯)、AEC/ZeroFlap約1週；以US$6/GPU/小時(每週US$1,000)計，節省3-5週=每張GPU多創造約US$3,000-5,000租金；主動監測可在模組完全故障前關閉問題節點。**PIC業務**：US$1億+的PIC營收目標**100%來自外售給其他光收發器廠商的獨立PIC**(不含整合於自家ZeroFlap的PIC)；已拿下**兩個大型NPO客戶的design win**，預計FY28貢獻營收；第一代ZeroFlap使用第三方PIC，收購DustPhotonics之PIC整合進自家模組預計再約9個月(收購後約3個月時談話)。**庫存/供應鏈**：近兩季原物料占比顯著上升，主因為ZeroFlap備料(雷射、DSP、PIC、時脈元件、微控制器)；最長交期是台積電IC晶圓13-14週，Credo採購晶圓後存為裸晶庫(die bank)，收單後封裝約1週、組裝成AEC/ZeroFlap約1個月；LNP(薄膜鋰鈮酸鹽)供應吃緊，Credo稱已兩年預先佈局鎖定產能，但「成長潛力大、非無限」。**客戶**：4家營收占比>10%的超大型雲端客戶+正在成長的第5家(細節因保密協議不公開)；目前營收多來自2-3年前開發的產品，現在的開發將於未來1-2年落地。**Micro-LED vs Micro-VCSEL**(英文原稿「micro-vixel」為VCSEL之誤植/音譯)：依應用情境兩者並提，無特定偏好。**活動**：次週(10/13)OCP大會展出新技術並發布新聞稿。**⚠️與本頁既有內容的並列(待確認)**：①本頁寫「FY2026前十大客戶約90%、兩家個別>10%」，本memo稱現有「4家營收占比>10%的超大型客戶+第5家」——可能是客戶集中度從FY26到現在的變化(或口徑不同)，**待下次財報客戶別揭露核實**；②本頁「貿聯為Credo線材組裝」，本memo稱**BizLink僅為多家合約製造商之一，不應用BizLink業績作為Credo業務指標**，兩者並列；③本頁寫ALC「FY2027送樣、FY2028量產」，memo未提ALC時程，僅提1.6T AEC/Retimer/PIC時程；④本memo的「US$5,000萬Retimer訂單」「兩個NPO design win(FY28貢獻)」為管理層說法，非財報揭露數字。**待確認項目(memo列示)**：ZeroFlap與ALC的合約製造商尚未揭露；1.6T AEC首批部署客戶明細未確認(保密)；自家PIC整合進ZeroFlap約9個月內；LNP供應吃緊是否限制超出財測的上行。
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
| 期間                                | 營收           | 年增/季增                | 獲利指標                                                                     | 備註                                                                                                     |
| :-------------------------------- | :----------- | :------------------- | :----------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------- |
| FY2026(全年)                        | 13.4億美元      | YoY +205.7%          | —                                                                        | 財年約對應2025/5~2026/4                                                                                     |
| TTM(截至最近季)                        | 15.9億美元      | YoY +165.1%          | 淨利5.38億美元(YoY+330%)、EPS約2.83美元                                           | trailing數字含較大幅度成長基期效應，需留意非線性外推                                                                         |
| Q1 FY2027(2026-09-01公布)           | 4.79億美元      | QoQ+10%／YoY+115%，創新高 | Non-GAAP EPS 1.20美元(優於預期1.17美元)；Non-GAAP毛利率68%；Non-GAAP淨利2.363億美元        | 優於財測，帶動股價當日反應                                                                                          |
| Q2 FY2027 guidance                | 5.25~5.35億美元 | —                    | Non-GAAP毛利率67~69%；Non-GAAP營業費用1.00~1.05億美元                               | 公司自結財測                                                                                                 |
| FY2027全年guidance                  | —            | YoY +85%以上           | 光學業務目標>6億美元(Zero-Flap Optics/矽光子PIC/光學DSP各>1億美元)；non-GAAP淨利率guidance近50% | 管理層框架：2H27為成長加速期                                                                                       |

### 📊 EPS預估比對
| 估算日期 | 預估期間 | 預估/實際 EPS (美元，non-GAAP) | 情境/假設條件 | 來源文件/備註 |
| :--- | :--- | :--- | :--- | :--- |
| (實際) | Q1 FY2027(2026-05~2026-07) | 1.20 | 已公布實際值，優於共識1.17 | 公司2026-09-01法說新聞稿 |
| 2026-09-21查 | **FY2027整年**(公司財年2026/5~2027/4) | **6.31** | 18家法人共識，內含Q1FY27已公布的1.20實際值 | stockanalysis.com，明確標註「EPS/Forward PE均採non-GAAP口徑」 |
| 2026-09-21查 | NTM未來4季(Q2FY27~Q1FY28，滾動窗口) | 約7.48 | 與上面「FY2027整年」**非同一區間**，不可直接比較——此窗口換掉了FY27已知偏低的Q1、換入了成長更快的FY28首季 | 另一資料源之分析師共識彙整 |

**⚠️ EPS共識口徑提醒**：Credo財年為每年5月至隔年4月，「FY2027」＝2026/5~2027/4，跟一般講的「2027年」（公曆年）不是同一個區間，目前查到的資料都是財年口徑，若你要的是calendar year 2027，需要另外查證，暫不代入猜測。上述兩個非同期數字（6.31 vs 7.48）皆為non-GAAP（排除股票薪酬、DustPhotonics/Hyperlume併購攤銷等），GAAP EPS目前查無明確共識、一般會明顯更低，留待後續財報揭露。

### 估值與法人評等（資料時點：2026-09-21，多來源交叉比對）
- **股價**：175.95美元（2026-09-21），52週區間86.49~308.67美元——波動區間極大，Beta 3.23屬高波動股。
- **市值**：約330.6億美元。
- **本益比**：trailing P/E約66x（受惠爆發性成長基期，數字參考性有限）；forward P/E因EPS分母口徑不同而有數個版本——用FY2027共識6.31美元算，175.95/6.31≈**27.9x**；用NTM口徑7.48美元算則約23.5x；另有資料站於2026-09-18(股價188美元時點)單獨標示25.6x，三者定義互不相同，不強行合一，實際使用時請先確認分母口徑。
- **法人評等**：19家法人，平均「Strong Buy」（Strong Buy 21.05%／Buy 73.68%／Hold 5.26%／Sell 0%）；12個月平均目標價282.47美元（另一資料源：16家法人平均274.42美元，區間206~350美元）；BofA近期(確切日期未查得)將目標價由340美元下修至275美元、仍維持買進評等——顯示法人樂觀程度在股價回落後也有收斂跡象，不是單向上修。
- **⚠️ 數據一致性提醒**：不同財經網站對「當前股價」「均線水位」的數字在同一週內就有明顯落差（例如同樣號稱9月中旬的資料，股價從168到188美元都有），研判是各站台快取時間點不同、加上該股近期波動極大所致；若要據此做實際交易判斷，建議直接查證即時報價，不要只信任本筆記的靜態數字。

---

## 💵 現金流量與資產負債表 (Cash Flow & Balance Sheet)
- **Q1 FY2027自由現金流**：8,290萬美元（資本支出730萬美元），營運現金流9,020萬美元(季減9,200萬美元，主因營運資金變動)。
- **現金部位**：Q1 FY2027季底現金及約當現金7.643億美元，季減約6.79億美元——主因DustPhotonics收購支付現金對價。
- **負債**：公開資料未查得明確財報揭露數字；公司對外表態流動性「舒適」，預期營運現金流可望回升至每季約2億美元的水準。
- **解讀**：DustPhotonics收購用掉大部分現金儲備，是典型「用資產負債表換技術版圖」的動作，短期現金部位轉薄，需要留意後續季度自由現金流能否如公司所說回升到2億美元/季的水準，這會是驗證「收購有沒有拖累財務體質」的關鍵指標。

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
- **⚠️ 2026-10-12 補充(Credo管理層10/7 call memo)**：管理層指出**BizLink(貿聯)只是Credo多家AEC合約製造商之一，投資人不應把貿聯的表現視為Credo業務的代理指標**；與上一條「貿聯負責Credo線材相關組裝/貿聯2Q26前十大客戶之一」並列(貿聯端數字確屬其營收占比，但反向推Credo需求不宜直接等同)。
- **[[3665貿聯]]（貿聯-KY）**：Credo是貿聯2Q26前十大客戶之一，營收占比約8-9%（貿聯負責Credo線材相關的組裝製造）。貿聯筆記裡已有UBS於2026-07-08參加「Credo台灣NDR(Non-Deal Roadshow)」後的既有記錄：**Credo對AEC TAM持續看多，8-10月OCP展會展示ALC，且MediaTek/AUO開始評估ALC方案**——這則MediaTek/AUO評估ALC的細節，本次網路搜尋並未能獨立查證到公開報導，屬於Lucas既有分析師資源才拿得到的資訊，正好印證「vault既有一手資料 vs. AI公開網路搜尋」的深度落差，建議後續若有機會可向同一批分析師追問ALC最新進度。
- **概念上相關但vault尚未追蹤的個股**：[[3081聯亞]]（雷射元件）、[[3363上詮]]（FAU光纖陣列）、[[2345智邦]]（交換器系統整合）——這幾檔台股都在同一個「AI資料中心高速互連」供應鏈上，但屬於不同環節（Credo是連接晶片/線材設計端，這幾檔多是上游元件或下游系統整合），非直接同業競爭關係。

---

## 📝 管理層/法人溝通紀要 (Call Memos)

### 📌 [2026-10-07] Credo Call Memo by Judy Hsiao(中英雙語) (來源: [[20261011_182620_file.docx]])
**文件性質**：Word檔，前半為英文call memo(Key Outcomes / Decisions Made / 各主題要點，並於句尾以數字標註對應的發言來源序號)，後半為同內容之繁體中文會議紀錄；標題「202610.07 CREDO 會議紀錄 (Call Memo by Judy Hsiao)」。內容為Credo管理層對投資人之問答整理，屬**一手管理層說法**，與本頁其他以公開網路資料為主的段落不同可信度層級；惟memo為第三方整理、未附逐字稿，數字(US$5,000萬訂單、US$1億PIC目標)為管理層口頭說法。
**一、關鍵成果與重大決策**：管理層對AEC、光學(Optics)與重定時器(Retimer)產品線的多年成長表達強烈信心。①1.6T AEC營收將於**2027財年第四季(約4-5月)或2028財年初**開始，預計日曆年2027年中起顯著放量；多家超大型雲端客戶共同部署，非單一客戶；②ZeroFlap Optics因獨家遙測/診斷能力列為關鍵競爭優勢；③已取得Scale-Up銅纜Retimer**未來9至12個月高達US$5,000萬採購訂單**，為1.6T世代首個商業捷報；④BizLink非業績唯一指標：AEC採用多家代工製造商，BizLink僅為其中之一；⑤Micro-LED與Micro-VCSEL依應用情境並提，無特定偏好；⑥目標US$1億以上的PIC營收100%來自外售給其他光收發器廠商的Discrete PIC。
**二、AEC業務與產品路線圖**：AEC仍占營收絕大部分、預期FY27與FY28持續成長；單通道100G(800G，4×100G或8×100G)近期才躍升為AEC主要營收來源，25G/50G仍貢獻相當比重；絕大多數AEC纜線長度在3公尺以內，6-7公尺僅占個位數%營收。**1.6T AEC(單通道200G)**：成本增幅低於ASP提升幅度，毛利率優於前幾代；最長可達6公尺(800G為7公尺)；產品家族涵蓋光學(Scale-Out)、AEC(Scale-Out)、Retimer(Scale-Up)與PIC(Scale-Up)。
**三、Design Win轉化與ZeroFlap壁壘**：非所有design win都轉化為營收(半導體產業常態)，從取得到產生營收可從一季到數年不等，一旦部署具極高黏性。**ZeroFlap Optics**：唯一能在光收發器提供豐富診斷與即時鏈路健康數據的產品；根因識別涵蓋ESD損傷、系統整合時光纖未對準、光纖灰塵(灰塵使光子反射回彈，可由Credo專用DSP偵測)；傳統商品化光模組廠(旭創、易飛揚、AOI、Coherent/Lumentum)缺乏專用DSP/軟體/韌體。AEC遙測與ZeroFlap本質相似；僅買獨立PIC無法享有此功能。競爭壁壘：Marvell等理論上可開發，但會侵蝕既有DSP業務並損害與Inphi/Eoptolink等客戶關係，給Credo約一年先發優勢。**客戶價值**：商品化光模組叢集需4-6週建置，AEC/ZeroFlap可縮至1週；以每GPU每小時US$6(每週US$1,000)計，節省3-5週=每GPU多US$3,000-5,000租金收益；主動監測可在模組完全故障前關閉問題節點，提高叢集稼動。
**四、PIC、庫存策略與供應鏈**：獨立PIC已拿下兩家大型NPO客戶的design win，預計FY28貢獻營收；第一代ZeroFlap使用第三方PIC，收購之DustPhotonics PIC整合預計9個月內推出搭載自家PIC的ZeroFlap產品。近兩季原物料比例顯著增加，主因為ZeroFlap量產備料(雷射、DSP、PIC、時脈元件、微控制器)。交期最長者為台積電IC晶圓(約13-14週)；Credo採購晶圓後存於裸晶庫(die bank)，收到訂單後封裝約1週、組裝成AEC或ZeroFlap約1個月，約一個月內可交貨。Credo稱已多年佈局供應鏈，信心滿足財測目標與潛在超額需求；針對LNP產能緊張，兩年前即預先佈局鎖定產能，成長「潛力大但非無限」。
**五、客戶關係與待確認事項**：4家營收占比≥10%的超大型雲端客戶，另有第5家正在成長，細節因保密協議不公開；目前營收主要來自2-3年前開發的產品，當前開發將於未來1-2年落地；資料中心部署本質緩慢複雜。**活動**：次週OCP大會(Credo將展示並發布新聞稿)。**Action Items**：Credo IR團隊發布OCP展示新聞稿；營運團隊持續確保供應鏈供給；工程團隊9個月內完成DUST PIC整合進ZeroFlap。**待確認**：ZeroFlap與ALC合約製造商未揭露；1.6T AEC首批客戶明細未確認；自家PIC整合時程；LNP供應是否限制超出財測的成長。
**與本頁既有內容的關係**：本頁原有「FY27新增成長光學約占一半、AEC一半」「AEC成長是否放緩待驗證」「客戶集中度」「貿聯為Credo線材組裝」等；本memo補充1.6T AEC時程(FY27 Q4~FY28)、Retimer US$5,000萬單、ZeroFlap差異化與PIC外售定義，**但並未揭露AEC營收成長率**，故「AEC成長是否放緩」仍無定論；客戶集中度「4家>10%」與本頁「2家>10%」並列待核實。

---

## 📅 近期重大事件時間軸 (Recent Events Timeline)
- **2026-10-07**：Credo管理層call memo(Judy Hsiao整理)：1.6T AEC營收FY27 Q4或FY28初開始、Scale-Up銅纜Retimer取得未來9-12個月US$5,000萬採購單、兩個NPO PIC design win預計FY28貢獻營收、DUST PIC整合進ZeroFlap約9個月內(見上方「管理層/法人溝通紀要」)。
- **2026-10-13(預計)**：OCP大會，Credo展示新品並發布新聞稿(同週貿聯等供應鏈廠亦於OCP展出光互連方案)。
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
- `[[20261011_182620_file.docx]]` — 2026-10-07 Credo管理層Call Memo(Judy Hsiao，英文+繁中)：1.6T AEC時程、US$5,000萬Retimer訂單、ZeroFlap遙測差異化、PIC外售US$1億+、die bank庫存策略(**一手管理層說法**，與下列公開網路資料可信度層級不同)
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
