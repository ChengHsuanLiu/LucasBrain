---
type: industry
garden_type: industry
title: "ASIC 客製晶片"
tier: "2_晶片層"
created: 2026-07-10
updated: 2026-10-20
review_by: 2026-10-11
tags: [industry/category, industry/asic]
---

# ASIC 客製晶片

## 🎯 產業投資點評與核心結論 (Summary & Insights)
* **2026-10-22 新增：Lucas自建《AI晶片出貨量模型》，完整拆解NVIDIA/AMD/AWS/Google四大廠CoWoS投片量/晶片出貨量/機櫃出貨量，Google TPU晶片出貨量估2026F/27F/28F達520萬/900萬/1,370萬顆，為本頁TPU總量追蹤議題第五個獨立數據點**（來源：Lucas自建模型，與產業投片資訊及外部顧問核對後整理，2026-10-22；完整表格見`[[AI晶片出貨量模型]]`）：**模型結構**：橫跨CoWoS晶圓投片量(千片)、晶片出貨量(千顆)、整機櫃出貨量(台)三個層級，以「顆/片」「顆/櫃」換算係數串接，逐產品世代拆解(NVIDIA Hopper→Blackwell→Rubin→Rubin Ultra Kyber→Feynman；AMD MI300→MI375→MI455/MI450→MI500 Arcadia；AWS Trainium T2→T3→T4；Google TPU v7 Ironwood→v8 Sunfish/Zebrafish→v9 Humufish/Triggerfish(EMIB-T)→v10 Icefish(EMIB-T))。**四大廠晶片出貨量小計(千顆，2025/26F/27F/28F)**：NVIDIA GPU 5,840/7,800/8,000/10,600；AMD GPU 480/567/1,134/2,100；AWS Trainium 1,260/2,160/2,904/3,500；**Google TPU 1,100/5,200/9,000/13,700**。Total(non-EMIB-T，排除Intel EMIB-T封裝之v9 Humufish/Triggerfish/Axion CPU三列)晶片出貨量11,590/23,476/38,388/52,558千顆。**機櫃出貨量小計(台)**：NVIDIA 163,500/125,625/97,222/65,278(隨世代轉換、單櫃顆數提升而逐年遞減，VR Ultra Kyber單櫃達144顆、Feynman單櫃達576顆)；Google TPU機櫃17,188/81,250/140,625/214,063(四大廠中機櫃數成長最快)。**⚠️與頁面既有Google TPU追蹤數字之比較(第五個獨立數據點，並列存查不擇一採信)**：本模型Google TPU晶片出貨量(2026F/27F/28F 520萬/900萬/1,370萬顆) vs 既有ALETHEIA數字(2026E/27E/28E 360萬/850萬/1,200萬顆)——**2027/28年兩者相對接近(900萬vs850萬、1,370萬vs1,200萬)，但2025/2026年差異較大**(本模型2025僅110萬顆、2026F達520萬顆，爬升斜率比ALETHEIA更陡)；與10-16凱基專家訪談「Google TPU存量700萬+顆、明年維持600-700萬顆」相比，凱基口徑為**當年末存量**而非**當年新增出貨量**，兩者定義不同、無法直接比較；與08-23筆記「2027年ASIC/TPU總量15.262M顆」相比，該筆記為全市場ASIC/TPU總量(含Meta/Microsoft/中國CSP等)、非Google TPU單一廠商數字，範疇不同。**CoWoS投片量角度的TPU觀察**：Google TPU CoWoS投片量2025/26F/27F/28F為69/349/598/1,094千片，占四大廠CoWoS總投片量(697/1,587/2,685/3,674千片，non-EMIB-T)比重由2025年約10%逐年攀升至2028年約30%，顯示TPU在台積電CoWoS產能分配中的占比持續擴大，與頁面既有「Google TPU份額由20%提升至31%」等類似趨勢描述方向一致。
* **2026-10-20 新增：GS《Global Server: Raising both AI and General servers》全球伺服器TAM報告，2027/28E全球伺服器TAM上修31%/45%，AI晶片需求2026-28E達18m/29m/38m顆、全球ASIC滲透率2028年看60%**（來源：GS分析師Allen Chang/Verena Jeng/James Schneider/Michael Ng等，2026-10-18）：**TAM全面上修**——一般伺服器2027/28E價值上修17%/11%(出貨與ASP同步上修，2026-28E出貨YoY各+20%/12%/8%)；AI伺服器(NVL72機櫃，Nvidia+AMD)2027/28E出貨上修5%/1%至**11萬/16.4萬台**；AI伺服器(8-GPU等效，GPU+ASIC)2027/28E出貨上修10%/29%至**270萬/330萬台**。全球伺服器TAM 2026-28E成長0%/31%/45%(一般伺服器+47%/+15%/+8% YoY、AI伺服器+119%/+123%/+54% YoY)。**AI晶片需求與ASIC滲透率(本頁持續追蹤議題之第四個獨立數據點)**：新AI伺服器出貨預估隱含AI晶片需求2026-28E達**18M/29M/38M顆**，對應全球**ASIC滲透率2028年約60%**(global-tier約50%)——此為GS自身口徑之「ASIC滲透率」單一總量數字，**與頁面既有ALETHEIA(2026E 3.6M/2027E 8.5M/2028E 12.0M顆，含Anthropic經AVGO量)、08-23筆記截圖(2027年ASIC/TPU 15.262M顆)、10-16凱基專家訪談(Google TPU存量700萬顆+明年600-700萬顆)等多份數字口徑/定義範圍(總AI晶片vs純ASIC/TPU、出貨量vs存量)皆不相同，繼續並列存查、不擇一採信**。**AI伺服器機架出貨/供應鏈**：GS預估NV+AMD機架2026-28E出貨61k/97k/149k台(原估50k/92k/148k上修)，鴻海/FII續居ODM龍頭並持續擴大份額(受惠強勁研發/規模/美國與全球生產佈局)；AI伺服器機架TAM 2025-28E CAGR達163%、2028年將占全球伺服器TAM**63%**，上看US$1兆。**一般伺服器驅動力**：高記憶體成本+Intel Xeon 6+/Xeon 7 Diamond Rapids(Agentic AI/企業級工作負載優化)與AMD EPYC Venice(6代)規格升級同步帶動ASP與出貨成長。**CSP資本支出**：美系CSP(Amazon/Meta/Alphabet/Microsoft/Oracle)資本支出預估2026-28E YoY+84%/52%/13%(上修4%/17%/22%至2028年US$1.397兆)；中國CSP(Bytedance/Alibaba/Tencent/Baidu)預估2026-28E YoY+105%/21%/14%(上修14%/15%/11%)，中國CSP晶片支出因本地fabless供應商多元而在GPU/ASIC間更分散。**Microsoft Maia 300關鍵進度**：Maia系統將擴展至多GW部署規模、成為Microsoft產品/服務主要推論系統，傳將自2027年起啟動多GW部署，據報導**2027年可能部署逾100萬顆Maia 300晶片**(與另一份MS《2026 OCP Global Summit – MGX Upgrades Take Shape; Maia 300 on Display》報告為互相獨立來源，待讀取後交叉確認)。**AI伺服器生態系供應鏈曝險表(2026E，GS此份報告獨家完整揭露逐家公司對Nvidia GPU/AMD GPU/Google TPU/Amazon Trainium/Meta MTIA/中國GPU與ASIC/Oracle七大晶片平台之營收曝險%)**：本庫已追蹤個股中值得特別標註的ASIC平台曝險——`[[2383台光電]]`(Google TPU 15-20%、Amazon Trainium 10-15%、Meta MTIA 5-10%，CCL業務)、`[[2368金像電]]`(Amazon Trainium **30-35%**、Meta MTIA **20-25%**，PCB業務，與既有福邦YC筆記「AWS T4 HDI金像電40-50%市占」方向一致互證)、`[[3081聯亞]]`(Google TPU **30-35%**、Amazon Trainium 10-15%、Meta MTIA 10-15%，InP雷射二極體/磊晶片業務)、`[[3017奇鋐]]`(Amazon Trainium 15-20%、Meta MTIA 5-10%，液冷元件)、`[[6274台燿]]`(Amazon Trainium 10-15%，CCL業務)、`[[2455全新]]`(Google TPU 10-15%，InP磊晶片)、`[[3231緯創]]`(Amazon Trainium 5-15%、Oracle 5-10%，AI伺服器ODM)、`[[2317鴻海]]`(Google TPU 5-10%、Amazon Trainium 0%、Meta MTIA <5%、中國GPU/ASIC<10%)；其餘已追蹤個股(`[[8046南電]]`、`[[4958臻鼎-KY]]`、`[[3189景碩]]`、`[[3037欣興]]`、`[[2308台達電]]`、`[[2382廣達]]`、`[[2356英業達]]`、`[[2357華碩]]`、`[[2376技嘉]]`)對ASIC三大平台(Google/Amazon/Meta)曝險皆偏低(多為<10%)，主力仍集中於Nvidia/AMD GPU生態系，與頁面既有Nvidia機櫃為主要營收動能之敘事一致。**買進名單**：GS對AI伺服器供應鏈維持買進鴻海/FII(ODM)、緯穎/緯創(ODM)、中際旭創/Eoptolink(光模組)、生益科技(CCL)、Victory Giant(PCB)、FOCI/大立光(FAU)、聯亞/全新(矽光子)、奇鋐/富世達(液冷)、台積電(晶圓代工)、MPI(測試探針卡)、WinWay(測試socket)、Aspeed(無廠IC設計)。
* **⚠️ 2026-10-20 新增：凱基投顧【專家會議】AI軟硬體產業專家逐字稿——Google TPU總存量約700多萬顆、明年規模預估維持600-700萬顆、超過一半以上分配給Anthropic；DeepMind自身訓練用TPU僅60-70萬張，算力受擠壓導致Argon模型延後逾一個月發布**（來源：凱基投顧【專家會議】，2026-10-16；13題完整Q&A）：**此為TPU總量/分配的第三個獨立數據點，與頁面既有ALETHEIA(2026E 3.6M顆/2027E 8.5M顆/2028E 12.0M顆)、Morgan Stanley AVGO NDR(未揭露具體量)、本頁上方安聯/Alethia簡報(2026E 3.6/2027E 8.5/2028E 12.0，與ALETHEIA數字相同來源)相比，口徑與量級需並列存查，不擇一採信**：本次專家訪談稱「Google目前TPU總存量約700多萬顆(含v3/v4/v7等各世代)，另有約100萬顆GPU及部分外租GPU」、「明年TPU規模維持在600–700萬顆左右」、「明年大概700萬顆上下，超過一半以上都是分配給Anthropic」——此為**當前累積存量+明年規模**的口徑，與ALETHEIA/安聯簡報之「當年新增出貨量」(2026E 3.6M/2027E 8.5M顆)口徑明顯不同(存量 vs 增量)，數字差距可能主因定義範圍不同而非真實矛盾，惟目前無法直接換算比對，**待後續更明確數字出現再回頭釐清**。**算力分配結構性擠壓細節**：傳統搜廣推業務(YouTube/Search/廣告)占用約200萬顆中低端TPU(如v4)；外部客戶占用約300-350萬顆，其中Anthropic(Claude Fable)訓練+Serving消耗大量TPU v7；Gemini免費端用戶算力遭大幅削減(限制用Flash、改推Flash Lite)以挹注新模型Argon上線；DeepMind本身預訓練占用幾十萬張卡，外部客戶(如Ilya's SSI)因排隊等不到TPU而轉向NVIDIA GPU。**DeepMind自身算力受擠壓之具體後果**：GCP將大量TPU算力優先給Anthropic(**Anthropic獲取的TPU總數甚至超過DeepMind自用**)，加上TPU v8i交付延遲，直接導致Gemini新模型Argon延後逾一個月發布；DeepMind內部留用於訓練的TPU僅約60-70萬張(含v6/v7)。**算力緊張程度**：專家稱「Argon的算力緊張到從昨天下午開始，員工都不能再使用Argon，只能使用測試模型」；廠商透過動態降低思考等級(Thinking Level)服務更多用戶而非拒絕服務，消費端AI服務普遍處於虧損狀態，各大廠正打擊濫用行為(如共享帳戶轉售)。**ASIC晶片商機與風險**：初創晶片公司多聚焦ASIC推理晶片，若Transformer架構為最終解方，ASIC具極高ROI、將挑戰NVIDIA CUDA護城河；惟架構迭代風險存在(如Jeff Dean所在Discovery Lab研究之RSI架構)，若出現優於Transformer的新架構，專用型ASIC將面臨衝擊；非定型領域(World Model/文生視頻/Robotics/Multimodal)因模型架構未定型仍偏好GPU。**企業端落地瓶頸**：傳統企業無法準確估算Token費用、安全性疑慮重重、IT部門缺乏搭建Harness(LlamaIndex/CrewAI)經驗，極度依賴FDE(Forward Deployed Engineer)現場落地；模型每代升級單一任務Token消耗量暴增2-3倍，資料中心2年建設週期落後於Coding Agent爆發速度，電力與設備瓶頸致算力吃緊長期持續。
* **⚠️ 2026-10-20 新增：凱基投顧Radar Monthly《電子硬體產業》——VR、Trainium3、TPU v8多款新世代GPU/ASIC伺服器機櫃方案將於4Q26放量，受惠零組件供應商含緯穎/緯創/鴻海/奇鋐/富世達/健策/台達電/金像電/台光電/欣興**（來源：凱基投顧，2026-10-15）：Vera Rubin(VR)、Trainium3(T3)及TPU v8 AI伺服器預計3Q-4Q26進入放量階段。9月與3Q26營收好壞參半——GB300需求持續增溫，惟AWS T3伺服器出貨遞延，抑制整體成長動能。4Q26 AI伺服器營收可望維持強勁，受惠VR伺服器、MI455、T3液冷方案及TPU v8平台陸續放量；展望1Q27，成長動能預期將進一步增強。凱基維持對2026-27年伺服器需求樂觀看法，預估2026-27年需求分別年增**21%/25%**；惟同時下修智慧型手機出貨量預估(2026-27年各年減12%/2%)與PC出貨預測(同期各年減14%/12%)，反映資本支出排擠效應。
* **⚠️ 2026-10-14 新增：Marvell(MRVL，非追蹤個股)10/6投資者日全面上修中長期財測——FY2028營收US$200億元(+67%)、資料中心營收US$180億元(+80%，提前一年達標)、首度公開FY2031營收目標US$700–900億元(中值800億，市場共識425億)；客製化(XPU-Attach)FY29營收目標上修至逾US$120億元；長期EPS CAGR約64%**（來源：台新投顧《美股投資週報》2026-10-12第4頁 `[[20261013_142320_file.pdf]]`，二手整理)：**互連(Interconnect)與交換器**——光學DSP(1.6T/3.2T)與同調光模組(COLORZ)需求強勁；跨機櫃Scale-up光學(NPO/CPO)與首款單晶片100T交換器(Teralynx T100)預期FY28起挹注數億至數十億美元營收，為財測上修最大來源。**客製化AI**——除核心加速器(Trainium、Maia)外，與Google簽多年期協議，周邊矽晶片(XPU-Attach：推論加速器、CXL記憶體擴充、客製化網卡)即將放量；客戶NRE可抵減研發費用，高客製化比重無損長期44–46%營益率目標；毛利率守58%、FY28營益率朝40%+。**股價**：10/9收盤US$275.3，約32x CY2027 EPS，華爾街目標價US$350(隱含+27.1%)。**關注**：Scale-up光學(NPO/CPO)FY28是否達數億美元規模、毛利率能否守穩58%、FY31目標高度依賴前十大CSP資本支出。與頁面既有Marvell TIA/測試敘事(矽格6257、頎邦6147)及MS 10/8 CPO報告並列，口徑不同、不合併。
* **⚠️ 2026-10-13 新增：安聯投信10/2026簡報引用Alethia：GPU+ASIC全球出貨(百萬顆)2025/26E/27E/28E 12.9/15.0/24.0/34.4(2026E-28E CAGR約50%)；Google TPU 3.3/3.6/8.5/12.0(含Anthropic經AVGO量，v8i+t 2027年8.2、2028年10.5、v9 2028年1.5)；Nvidia 5.4/7.6/9.5/11.4(Rubin 2027年6.5、Rubin Ultra 2027年2.0)；AMD 1.9/1.6/2.0/3.0；Trainium 1.9/1.6/2.0/2.0；OpenAI 0/0.2/1.0/3.5；MTIA 0.2/0.2/0.7/2.0；Nvidia市占隨客戶自研ASIC下降，但GPU/CPU/LPU/storage/networking整合能力仍最強**（來源：`[[20261012_120421_file.pdf]]`第10頁，單位百萬顆(推測)、資料日期2026/10；與下方既有「外資伺服器CPU/GPU/ASIC出貨量」截圖(2026-08-23、09-15)口徑可能不同，並列存查不合併）：備註——AMD 2028年OAI與Anthropic近期上調訂單；Google TPU 2027年V8i&t各半、V9(Whalefish)HVM預計2028年中；OpenAI 2027/2028年1.3/5GW部署；CY27約1M顆GB300在產，CY28 Rubin Ultra占比(雙/四GPU與Feynman設計)待定。
* **產業 So What？（這為什麼重要）**：
  - Hyperscaler 與科技巨頭（Google、Tesla、Microsoft）自研 ASIC 晶片浪潮持續擴大，帶動專業 ASIC 設計服務商（創意/GUC）同步受惠；同時，先進封裝周邊的關鍵 IP/材料供應商（愛普的 Si-Cap）也隨自研晶片放量吃到訂單紅利。
* **⚠️ 2026-09-15 更新：巨有科技(8227)新增追蹤——台灣首家ASIC設計服務(Turnkey)公司，強力買進/TP230元**：華南投顧報告(2026-09-09)，2Q26營收創新高(YoY+121.7%)但毛利率17.1%不如預期(公司模型18.1%/市場共識22.3%)。12nm(SerDes/PCIe Extender)為2026年主力，受台積電晶圓配額限制而非需求不足；6nm鎖定中國網通「白名單」客戶(PCIe Retimer/SerDes)多項NRE專案，預期2027年才有實質量產貢獻(2027F營收YoY+41%)；CoWoS/OSAT已認證但佔比仍低於1%，隨台積電白名單OSAT寬限期2026年底到期，預期2027年起放量。與`[[3443創意]]`同屬台積電Design Center Alliance之ASIC設計服務商，但客戶結構(中國網通白名單+美系FPGA)與創意(Google/Tesla/Microsoft)明顯不同，可視為互補而非直接競爭關係。詳見`[[8227巨有科技]]`個股頁面。
* **⚠️ 2026-09-15 更新：外資伺服器CPU/GPU/ASIC出貨量表補上公司別拆分數字，填補08-23筆記「未附出處券商」缺口**：另一份截圖(單位：百萬顆)提供Nvidia/AMD/Google/AWS/MSFT/Meta逐家拆分數字，與既有08-23筆記之總量級大致吻合(2025年Nvidia+AMD＝565.7+90=655.7萬顆 vs 既有筆記AI GPU總量656.7萬顆，誤差<1%；2027年850+180=1,030萬顆 vs 既有1,068.9萬顆)，判斷為同一份原始報告之不同呈現方式，可互相佐證但仍未附券商/分析師署名。**Nvidia GPU**出貨量2025年565.7萬顆→2026年650萬顆(YoY+17%)→2027年850萬顆(YoY+34%)；**AMD**由2025年90萬顆→2026年120萬顆→2027年180萬顆。**ASIC總出貨量**2025年380萬顆→2026年725萬顆(YoY+91%)→2027年1,360萬顆(YoY+88%)，成長速度明顯高於GPU；公司別拆分：**Google**仍為最大ASIC使用者，2027年用量估達800萬顆；**AWS**增至320萬顆；Microsoft與Meta同步擴大部署(2027年分別350萬/700萬顆)。分析師觀點：資料中心電力逐漸成為算力擴張瓶頸下，CSP將更重視每瓦運算效能與整體運算成本，ASIC針對特定運算工作之效率優勢有望推升滲透率，惟GPU憑通用性與軟體生態系優勢仍將維持重要地位。仍未附券商/分析師出處，與既有08-23/08-25兩則筆記併列存查。
* **⚠️ 2026-08-23 更新：外資伺服器CPU/GPU/ASIC出貨量截圖(2023-2027年)，ASIC/TPU 2027年YoY+111%成長遠超AI GPU的+25%**：截圖數據(單位：百萬顆)——Server CPU：General/AI CPU總量2025年28.40M→2026年36.10M(YoY+27%)→2027年52.60M(YoY+46%)，其中AI Server CPU年增最快(2026+42%/2027+93%)；x86/ARM CPU拆分中ARM CPU成長最猛(2026 YoY+81%/2027 YoY+89%)，佔比由2025年19%快速提升至2027年35%。個別廠商中Nvidia Grace/Vera/Rosa 2026年YoY+124%最為突出，Google Axion 2026年YoY+117%/2027年YoY+208%。AI GPU：2025-2027年6.567M→8.539M→10.689M顆，YoY分別+31%/+30%/+25%，成長動能逐年放緩；Nvidia佔比由2026年49%降至2027年35%(份額被稀釋)。**ASIC/TPU：2025-2027年5.085M→7.238M→15.262M顆，YoY分別+42%/+111%(2027年成長率遠超AI GPU)**，其中Google TPU 2027年YoY+134%最猛，Meta/Msft/China CSP/Cambricon/Others合計2027年YoY+130%；AI GPU與ASIC/TPU合計佔比中，Google TPU由2025年20%提升至2027年31%，Nvidia則由51%降至35%——反映客製化ASIC/TPU相對merchant GPU的成長率優勢持續擴大，對`[[3443創意]]`等ASIC設計服務鏈為結構性利多訊號。此為外資研究截圖摘要，未附出處券商名稱，完整報告待後續取得補齊。
* **⚠️ 2026-08-25 更新：Morgan Stanley《AI Supply Chain: Google ASIC, who gets what for design services?》，完整拆解Google/AWS/Microsoft/Meta四大CSP ASIC設計服務分工**：Google TPU側：`[[2454聯發科]]`(MediaTek)仍為TPU v10(Icefish)主要整合商，職責含I/O die設計+封裝整合，2029年TPU營收估上看700億美元(佔聯發科總營收65%)；`[[3443創意]]`(GUC)協助Microsoft Maia 200/Cobalt 200且2027年需求估倍增以上，並有望取得Meta ASIC(MTIA 600)專案，MS上修創意TP至6,388元。AWS Trainium側：世芯電子(Alchip，3661，**未追蹤**)管理層表示Trainium4 TAM可能與Google TPU相當，MS估2028年Trainium4出貨至少250萬顆、營收貢獻80億美元(原估40億美元上修一倍)，MS上修Alchip目標價至5,888元(隱含上漲空間逾50%，並有機會拿下第二家CSP客戶)。TPU各世代出貨量預估(千顆)：v8i(Broadcom)2026年4,000/2027年2,500；v8t(MediaTek)2026年3,000/2027年1,000；v9(MediaTek)2027年3,000起量；v10(MediaTek)量尚未知。**⚠️與2026-10-04 ALETHEIA CAPITAL報告之GAP(兩份並列存查，不擇一採信)**：本筆記加總後TPU總量約2026年7.0M顆、2027年6.5M顆，但ALETHEIA同期報告估計為2026E 3.6M顆、2027E 8.5M顆、2028E 12.0M顆，量級與成長節奏都明顯不同。已與Lucas當面確認(2026-10-04)：目前無法判斷何者較準確(可能是TPU出貨量定義範圍不同，如是否含Anthropic經Broadcom代工之第三方量)，Lucas決定兩份數字先並列記錄保留，待未來更明確消息(如Google/Broadcom自結數字)出現後再回頭釐清，不要只取其一。完整ALETHEIA數字見`[[3_上游_CCL]]`頁面同日筆記。此報告完整揭露美系CSP自研晶片設計服務市場的三方分工全貌(MediaTek/GUC創意/Alchip世芯)，為觀察ASIC供應鏈的重要基準報告。
* **⚠️ 2026-10-04 新增：UBS與Broadcom(AVGO)管理層Virtual NDR Call紀要，確認TPU/XPU專案能見度至少看到2029年**（來源：UBS分析師Timothy Arcuri/Natalia Winkler/Seth Cho，2026-10-02）：UBS重申買進、PT維持US$470(17x EV/FCF於CY27E軟體FCF貢獻$31.2bn + 30x EV/FCF於CY27E半導體FCF貢獻$60.4bn)。管理層重點表態：(1) F2027 AI營收指引保守偏向上(至少YoY倍增)、F2028再倍增；(2) 旗艦TPU專案至少未來兩個世代(2028/2029年出貨)能見度非常強，市場過度聚焦供應鏈雜訊，未充分理解晶圓配額/封裝等細節；(3) AVGO晶片明年起導入4-die設計，未來路線圖規劃8-die、16-die，持續增加SRAM容量(因應HBM定價/供給限制)並整合ARM核心於XPU內——此舉可能把原本獨立的伺服器頭節點CPU內容「吸入」XPU設計，使ASIC競爭對手難以追趕(對`[[3443創意]]`/`[[8227巨有科技]]`等設計服務商而言，意味Broadcom在客製晶片整合度上持續墊高技術門檻)；(4) 機櫃層級算力支出框架：Nvidia完整機櫃約US$40bn/GW(不含powered shell)，客製ASIC約US$20-30bn/GW(含整機櫃fiber/金屬等，非僅XPU+交換)；(5) Networking目前佔AI營收約30%，管理層認為隨叢集規模擴大、XPU間連接需求增加，此比重可能上修——TPU側採3D Taurus做scale-up(銅/光混合連接)，Tomahawk系列做scale-out，次世代Tomahawk 7頻寬翻倍且ASP看升；(6) 融資澄清：AVGO對其最大前沿模型客戶**不直接提供融資**，僅協助媒合第三方資金方，並對部分tranche提供殘值擔保(佔整體融資結構小部分)；(7) Powered shell(電力/機殼)短期緊缺視為時程問題而非結構性限制，預期2028年後供給明顯改善。**與ALETHEIA CAPITAL同日TPU供應鏈報告對照**：兩份報告對TPU長期成長力道看法一致(多世代能見度強)，但AVGO本身未揭露具體TPU出貨量數字，無法直接比對ALETHEIA的3.6M(26E)/8.5M(27E)/12.0M(28E)顆估計，詳見`[[3_上游_CCL]]`頁面同日筆記。
* **⚠️ 2026-10-14 新增：Citi《Taiwan monthly tracker》確認GUC/Alchip 3Q26營收雙雙大幅超預期，MediaTek TPU將自4Q26開始貢獻**：Citi報告指出ASIC動能正在加速，受惠`[[3443創意]]`(GUC)ARM-based CPU與`[[3661世芯電子]]`(Alchip)Trainium 3專案同步放量。**創意(3443)**：9月營收71.45億元(YoY+98%、MoM+22%)，3Q26營收QoQ+35%(遠優於Citi原估+17%/共識+15%)，追蹤達Citi/共識3Q估的115%/117%；Citi預期此訂單動能延續至4Q26/2027。**世芯電子(3661)**：9月營收99.79億元(YoY+496%、MoM+14%)，3Q26營收QoQ+243%(優於Citi原估+156%/共識+239%)，追蹤達134%/101%；Citi預期Trainium晶片明年放量進度穩健(與既有筆記MS估2028年Trainium4出貨至少250萬顆方向一致)。**聯發科(MediaTek)**：9月營收優於公司guidance與市場共識，主因智慧型手機市占率提升；Citi預期**TPU將自4Q26開始正式貢獻營收**，並看好聯發科未來兩年AI ASIC業務機會持續擴大(受惠產品線佈局)。收盤價：創意8,100元、世芯電子4,395元。
* **關鍵洞察**：
  - 創意（3443）身兼 Tesla AI5（ADAS）與 Google Axion CPU 後端設計服務雙引擎，2H27 起 3nm 下一代 CPU 專案 ASP 將調漲 60-80%。
  - 愛普（6531）的 S-SiCap（矽電容）是先進封裝 ASIC（如聯發科 TPU）電磁雜訊與供電穩定的關鍵材料，隨 ASIC 放量同步受惠。

---

## 📊 市場規模與循環定位 (Market Size & Cycle Positioning)
* **市場規模與成長率**：[待補充，現有研究素材未提供 ASIC 產業全球 TAM/SAM 或年成長率 (CAGR) 之明確數字]。可佐證成長動能的間接數據點：創意（3443）機構預估 EPS 由 2026E 49.27 元大幅跳升至 2027E 133.05 元、2028E 234.46 元（3nm 新一代 CPU 專案 ASP 調漲 60-80%）；台積電為滿足 AI CPU/GPU/ASIC 與光通訊網通晶片需求，已將 Fab 18 部分 3nm 產能改建為 2nm，隱含 2nm 產能規劃較一年前增加 60kwpm。
* **結構性成長 vs 循環性成長**：偏向結構性成長。創意同時綁定 Google（Axion CPU）、Tesla（AI5 ADAS）、Microsoft（第二代 CPU）三大 Hyperscaler 客戶，出貨能見度橫跨 2026-2030 年（Tesla 2027/2028 出貨 100 萬/200 萬顆，且高出貨量延續至 2030 年）；台積電同步規劃 2027/2028 年資本支出各達 750 億美元以應對多年期 AI/HPC 需求。此波成長並非單一規格週期帶動，而是 Hyperscaler 自研晶片浪潮的長期趨勢。
* **目前循環位置**：早期至中期（需求吃緊、產能爬升期）。創意產能受限於台積電產能配給，「Y2026 產能吃緊，Y2027 客戶需求超過 100%」；愛普 S-SiCap 產能規劃則由 2026 年底月投片量 1 萬片擴大至 2027 年底 2 萬片，同步反映供不應求、產能持續擴張的階段，尚未觀察到滿載後降價或庫存去化訊號。

---

## 🏆 競爭格局與市占率 (Competitive Landscape & Market Share)
| 廠商 | 是否為追蹤個股 | 全球/該環節市占率 | 定位與競爭優勢 |
| :--- | :--- | :--- | :--- |
| `[[3443創意]]` | 是（本產業核心追蹤個股） | [待補充，現有研究素材未提供具體百分比] | Hyperscaler ASIC 設計服務（Design House）龍頭，獨家綁定 Google Axion CPU、Tesla AI5 ADAS、Microsoft 第二代 CPU 三大專案後端設計，專屬與台積電 CoWoS/3D 封裝合作，採 NRE+Turnkey 模式收費 |
| `[[6531愛普]]` | 是（本產業核心追蹤個股） | [待補充，現有研究素材未提供具體百分比；筆記顯示為北美客戶首家通過驗證的 Embedded IPD 供應商，暗示先發優勢] | 先進封裝 S-SiCap（矽電容）關鍵材料/IP 供應商，供應聯發科 TPU、Broadcom 平台、Nvidia Feynman、AWS T4、Intel EMIB 等客戶 |
| `[[8227巨有科技]]` | 是（2026-09-15新增） | [待補充，現有研究素材未提供具體百分比] | 台灣首家ASIC設計服務(Turnkey)公司，台積電Design Center Alliance成員；12nm主攻SerDes/PCIe Extender，6nm鎖定中國網通白名單客戶，客戶結構與創意(Google/Tesla/MSFT)互補而非直接競爭 |
| `[[2330台積電]]` | 是（追蹤個股，但屬代工角色，非本產業分類 FPE 估值成員） | [待補充] | 創意與愛普唯一先進製程（3nm/2nm）與 CoWoS/SoIC 先進封裝供應商，具獨佔性議價權 |
| `[[2303聯電]]` | 是（追蹤個股，但屬代工協力角色，非本產業分類 FPE 估值成員） | [待補充] | 協力代工愛普 S-SiCap 矽電容晶圓，分散台積電產能風險 |
| Broadcom | 否（非追蹤個股，僅供比較） | [待補充，現有研究素材未提供具體百分比] | TPU 競爭方案「Whalefish」研發商，與創意/GUC 所服務之 Google/Tesla/Microsoft ASIC 設計服務業務形成潛在客戶爭奪關係 |

* **份額趨勢**：創意持續拿下 Google Axion CPU、Tesla AI5、Microsoft 第二代 CPU 等新一代設計標案，且 3nm 下一代 CPU 專案 ASP 大幅調漲 60-80%，反映其在 Hyperscaler ASIC 設計服務市場的議價力與客戶黏著度同步擴大；惟現有研究素材未提供具體的全球市占率變化百分比，無法量化「份額擴大」的實際幅度。

---

## ⚠️ 風險與總體敏感度 (Risks & Macro Sensitivity)
* **政策/地緣政治風險**：本產業高度集中於單一晶圓代工/封裝供應商（台積電，全部產能位於台灣）與美系 Hyperscaler 客戶（Google、Tesla、Microsoft），供應鏈與客戶集中度風險偏高；若中美科技管制加嚴或台海地緣政治風險升高，可能直接衝擊創意與愛普的量產排程與客戶信心。[現有研究素材未提供具體出口管制條文或政策細節，僅能由客戶/產能集中度推論風險存在]。
* **替代技術/顛覆風險**：Broadcom 的 TPU 競爭方案「Whalefish」可能與創意/GUC 爭奪同一批 Hyperscaler 客戶的設計服務訂單；先進封裝技術路線本身也在演進，台積電下一世代封裝技術 CoPoS 預計 2029 年後接棒 CoWoS 與 SoIC，屆時需留意創意/愛普現有 CoWoS/矽電容技術是否能順利銜接（花旗報告同時指出玻璃載板對 CoWoS 屬互補而非取代關係，短中期風險相對可控）。
* **總經敏感度**：[待補充，現有研究素材未提供利率、匯率或原物料成本對本產業影響程度之具體資訊]。

---

## 🧠 產業深層結構與底層物理 (First Principles)
* **ASIC 設計服務（Design Service）模式**（護城河類型：客戶認證週期）：Hyperscaler 自研晶片不具備完整後端設計團隊，需委託創意等 Design House 提供 NRE（委託設計）與 Turnkey（量產代工整合）服務，設計服務商藉由客戶自研晶片放量分潤成長，且不需承擔晶圓代工資本支出。
* **自研 ASIC 對先進封裝與電源穩定性的高要求**（護城河類型：製程Know-how）：高階 ASIC（如 Google TPU、Tesla AI5）多採用 3nm/2nm 先進製程搭配 CoWoS/EMIB 等先進封裝，功耗與雜訊控管要求高，因此矽電容（S-SiCap）等被動材料成為封裝內建的標配元件，而非傳統板上分立元件。

---

## 🗺️ 產業鏈地圖與廠商財務比對 (Supply Chain & Financials)
| 產業位置 | 推薦個股 | 主要角色與供應材料 | 2026E EPS | 2027E EPS | 關鍵合作 / 代工與競爭格局 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| ASIC 設計服務 | `[[3443創意]]` | Tesla AI5（ADAS）後端設計、Google Axion CPU 設計服務、Microsoft 第二代 CPU 代工設計 | 49.27 元 | 133.05 元 | 3nm 下一代 CPU 專案 ASP 調漲 60-80%，2H27 小量出貨 |
| 先進封裝關鍵材料/IP | `[[6531愛普]]` | S-SiCap（矽電容）供應聯發科 TPU 等 ASIC 封裝，Embedded IPD 北美客戶首家驗證通過 | 待補充 | 待補充 | 與 `[[2303聯電]]` 合作代工矽電容，確保量產能見度 |

> [!NOTE]
> `[[2330台積電]]`（晶圓代工/CoWoS 封裝）、`[[2303聯電]]`（矽電容代工協力）、Broadcom（TPU 競爭方案 Whalefish）在此產業中屬於代工/競爭方角色，非本分類 FPE 估值成員。聯發科(2454)自研 ASIC 定位已改分類至 `[[2_晶片層_運算晶片GPU_CPU_SoC]]`。

---

## 💼 終端應用與核心客戶 (Applications & Customers)
* **車用 ADAS**（Tesla AI5）：2027H2 開始量產，2027/2028 出貨 100 萬/200 萬顆，2028 年 Tesla 有望超越 Google 成為創意第一大客戶。
* **雲端自研 CPU**（Google Axion）：Google 自研運算晶片，創意負責 Axion CPU 後端設計。
* **雲端第二代自研 CPU**（Microsoft）：由創意提供設計服務，預計 2027H2 量產。

---

## 📅 產業趨勢與產品迭代時間軸 (Timeline)
* **2026-04** `Tape-out` Tesla AI5 晶片於台積電完成 Tape-out。
* **2026-06-30** `評等/目標價上修` CLSA/SinoPac 調升創意目標價至 7,500 元，3nm 下一代 CPU 專案 ASP 上修 60-80%。
* **2027H2** `量產放量` Tesla AI5 與 Microsoft 第二代 CPU 同步進入量產。
* **2028** `營收貢獻高峰` Tesla 有望超越 Google CPU 成為創意第一大客戶。

---

## 🔗 相關概念與個股連結 (Related Concepts)
* **關聯個股 (Stocks)**：`[[2330台積電]]`、`[[2303聯電]]`、`[[8227巨有科技]]`
* **關聯產業 (Garden)**：`[[2_晶片層_封裝測試]]`、`[[CoPoS與玻璃基板]]`（題材）、`[[3_上游_測試與探針卡]]`

---

## 📄 原始文件與連結 (Original Documents)
* `[[AI晶片出貨量模型]]` - Lucas自建模型：NVIDIA/AMD/AWS/Google四大廠CoWoS/Chip/Rack出貨量完整拆解(2025-2028F) (2026-10-22)
* `[[20261020_200523_file.pdf]]` - GS《Global Server: Raising both AI and General servers》：全球伺服器TAM上修31%/45%(2027/28E)、AI晶片需求18M/29M/38M顆、AI伺服器生態系供應鏈曝險表 (2026-10-18)
* `[[20261016_081527_text.md]]` - 凱基投顧【專家會議】AI軟硬體產業專家：Google TPU總存量700萬+顆、明年過半分配給Anthropic (2026-10-16)
* `[[20261016_081019_text.md]]` - 凱基投顧Radar Monthly《電子硬體產業》：VR/T3/TPU v8伺服器機櫃4Q26放量 (2026-10-15)
* `[[20261014_073353_file.pdf]]` - Citi《Taiwan monthly tracker and what's new in AI》：創意/世芯電子3Q26營收大幅超預期，MediaTek TPU 4Q26起貢獻 (2026-10-12)
* `[[20261013_142320_file.pdf]]` - 台新投顧《美股投資週報》(2026-10-12)：Marvell 10/6投資者日、FY28/FY31財測 (2026-10-12)
* `[[20261012_120421_file.pdf]]` - 安聯投信《台股展望報告》(2026/10)：GPU/ASIC出貨預估(Alethia)、PCB/CCL規格對照、TrendForce缺貨表 (2026-10)
* `[[20261004_154432_file.pdf]]` - UBS《Broadcom Inc.: Highlights From Virtual NDR Call With Mgmt》：確認TPU/XPU專案能見度至2029年，4-die→8-die→16-die晶片路線圖 (2026-10-02)
* `[[20260915_111246_file.pdf]]` - 華南投顧《巨有科技(8227)》：強力買進，TP230元，台灣首家ASIC設計服務Turnkey公司 (2026-09-09)
* `[[20260914_234858_image.jpeg]]` - 外資伺服器CPU/GPU/ASIC出貨量表：Nvidia/AMD/Google/AWS/MSFT/Meta公司別拆分數字 (未附券商出處)
* `[[20260825_161144_file.pdf]]` - Morgan Stanley《AI Supply Chain: Google ASIC》：Google/AWS/Microsoft/Meta四大CSP設計服務分工全貌 (2026-08-25)
* `[[20260823_145544_image.jpeg]]`、`[[20260823_145547_image.jpeg]]` - 外資伺服器CPU/GPU/ASIC出貨量截圖(2023-2027年)：ASIC/TPU成長率遠超AI GPU (2026-08-23)
* `[[20260525_004344_text.md]]`、`[[20260620_213639_text.md]]`、`[[20260701_004426_image.jpeg]]`、`[[20260615_150136_text.md]]` - 創意 (3443) Tesla AI5/Google CPU 相關研究
* `[[20260601_000014_text.md]]`、`[[20260525_003700_text (1).md]]` - 愛普 (6531) Si-Cap 產能與法說會備忘錄
