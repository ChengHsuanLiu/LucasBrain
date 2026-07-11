---
type: industry
garden_type: industry
title: "運算晶片 GPU/CPU/SoC"
tier: "2_晶片層"
created: 2026-07-11
updated: 2026-07-11
review_by: 2026-10-11
tags: [industry/category, industry/asic]
---

# 運算晶片 GPU/CPU/SoC

## 🎯 產業投資點評與核心結論 (Summary & Insights)
* **產業 So What？（這為什麼重要）**：
  - 聯發科在 Google TPU 戰略地位大幅躍升：Google 取消 Broadcom 的 Pumafish 專案後，聯發科的 Humufish (A5922, 2nm+HBM4e) 成為 TPU 戰略核心，是台廠中少數具備自研運算晶片(而非純設計服務)地位的公司。
* **關鍵洞察**：
  - 聯發科（2454）2028 年自研 ASIC 營收貢獻上看 400-525 億美元，Google TPU 戰略核心地位確立後與 Broadcom 的競爭關係逆轉。

---

## 📊 市場規模與循環定位 (Market Size & Cycle Positioning)
* **市場規模與成長率**：[待補充，現有研究素材未提供此產業整體 TAM/SAM 量級數字]。可觀察的替代指標為聯發科單一公司之自研 ASIC 營收：2028 年上看 400（麥格里）至 525 億美元（高盛），占其總營收比重達 63-69%；台積電 CoWoS（含 WMCM）產能預估亦由 2027 年 250kwpm 上修至 280kwpm，顯示此環節需求急速擴張，惟缺乏產業總體量體的獨立估計。
* **結構性成長 vs 循環性成長**：偏向結構性成長。核心驅動力是雲端業者（Google）自研運算晶片以取代外購 GPU 的架構轉變（Google 已將 Broadcom 排除出 TPU v9 核心設計，改由聯發科的 Humufish 獨家供應 2nm+HBM4e），而非單純的庫存或規格年度更新循環；另據 SemiAnalysis 揭露，Nvidia Rubin Ultra 因 Kyber NVL144 中板 (midplane) 製造瓶頸延至 2028 年量產、且 4-die 版本遭取消，為 Google TPUv8i Broadfly 與 AMD MI500X 等自研/客製化運算晶片開啟了結構性的市場空窗期。
* **目前循環位置**：早期至中期（稼動率爬升期）。TPU v8 (Zebrafish) 預計 4Q26 才開始放量出貨（50 萬顆），2027 年出貨上修至 200-300 萬顆；2nm TPU v9 (Humufish) 則要到 4Q27/1Q28 才量產，2028 年出貨規模上看 240-280 萬顆為營收貢獻高峰。對應台積電 CoWoS 產能仍在 2026 年 2 萬片、2027 年 12 萬片晶圓的擴產爬坡期，尚未進入滿載或去化階段。

---

## 🏆 競爭格局與市占率 (Competitive Landscape & Market Share)
| 廠商 | 是否為追蹤個股 | 全球/該環節市占率 | 定位與競爭優勢 |
| :--- | :--- | :--- | :--- |
| `[[2454聯發科]]` | 是 | [待補充，現有研究素材未提供此資訊] | Google TPU v8 (Zebrafish) / v9 (Humufish) 主力暨獨家設計商，取代 Broadcom 成為 Google TPU 戰略核心，獨家供應 2nm+HBM4e 世代；2028 年自研 ASIC 營收占比上看 63-69% |
| Broadcom | 否 (僅供比較) | [待補充，現有研究素材未提供此資訊] | 原為 Google TPU v9 (Pumafish) 主力設計商，遭 Google 取消專案後角色降為 Whalefish（備援/互補），Google TPU 核心設計地位已被聯發科取代 |
| Nvidia | 否 (僅供比較) | [待補充，現有研究素材未提供此資訊] | GPU/AI 加速器現任市場龍頭，但 Rubin Ultra 因 Kyber NVL144 midplane 製造瓶頸延至 2028 年、4-die 版本遭取消（僅剩效能減半的 2-die 版本），縱向擴充 (scale-up) 世代出現空窗期 |
| AMD (MI500X) | 否 (僅供比較) | [待補充，現有研究素材未提供此資訊] | 與 Google TPUv8i Broadfly 同為受惠 Nvidia Rubin Ultra 延期之競爭者，有機會爭奪縱向擴充市場份額 |
| Intel | 否 (僅供比較) | [待補充，現有研究素材未提供此資訊] | 擔任聯發科 A5922 (Humufish) EMIB-T 先進封裝後道代工夥伴（前道晶圓仍由台積電負責），同時亦為 CPU/晶圓代工市場的長期競爭者 |

* **份額趨勢**：聯發科在 Google TPU 設計服務中的份額明顯擴大——從原本的次要/備援角色躍升為戰略核心，直接取代 Broadcom 在 2nm+HBM4e 世代的地位；驅動因素包括 Google 主動的路線圖變更，以及 Nvidia Rubin Ultra 延期為客製化 ASIC（TPU、MI500X）創造的市場空窗期。[各廠商精確市占率百分比現有研究素材未提供]

---

## ⚠️ 風險與總體敏感度 (Risks & Macro Sensitivity)
* **政策/地緣政治風險**：聯發科的 Google TPU 專案高度仰賴台積電先進製程與 CoWoS 封裝產能（2027 年 CoWoS 佔用量達 12 萬片晶圓），且 2nm Humufish 後道封裝委由美系 Intel（EMIB-T）執行，供應鏈高度集中於台灣（晶圓製造）與美國（封裝夥伴/終端客戶 Google）兩地；若台美關係生變或美國對 AI 晶片相關出口管制政策調整，可能直接衝擊出貨排程與良率認證進度。[具體關稅稅率或出口管制條文現有研究素材未提供]
* **替代技術/顛覆風險**：最大不確定性在於 Nvidia GPU（Rubin Ultra）平台的量產進度——若 Nvidia 解決 Kyber NVL144 midplane 製造瓶頸並如期於 2028 年量產，可能重新壓縮 ASIC（TPU/MI500X）陣營的市場空窗期；反之若延遲持續，將強化雲端業者轉向自研運算晶片的結構性趨勢，對聯發科更為有利。此外 Google TPU 路線圖本身亦存在設計夥伴更替風險，如 2026 年 Broadcom Pumafish 專案遭取消、改由聯發科 Humufish 取代之先例，顯示雲端業者可能隨時更換 ASIC 設計夥伴，聯發科亦可能面臨同樣命運。
* **總經敏感度**：聯發科因晶圓代工與封裝等原物料成本上升，預期於 3Q26 全線調漲產品售價 5%，顯示晶片成本對上游代工/封裝報價變動較為敏感。[利率、匯率對此產業之具體影響程度，現有研究素材未提供]

---

## 🗺️ 產業鏈地圖與廠商財務比對 (Supply Chain & Financials)
| 產業位置 | 推薦個股 | 主要角色與供應材料 | 2026E EPS | 2027E EPS | 關鍵合作 / 代工與競爭格局 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| IC 設計（自研 ASIC/SoC） | `[[2454聯發科]]` | Google TPU v8 (Zebrafish)/v9 (Humufish) 主力設計商，2nm+HBM4e 獨家供應 | 54.70 - 64.30 元 | 115.20 - 181.92 元 | Google TPU 戰略核心，取代 Broadcom Pumafish 專案地位 |

---

## 💼 終端應用與核心客戶 (Applications & Customers)
* **雲端自研 TPU**（Google TPU v8/v9）：聯發科獨家設計 TPU v9 (Humufish)。

---

## 📅 產業趨勢與產品迭代時間軸 (Timeline)
* **2026-06** `TPU 路線變更` Google 取消 Broadcom 的 Pumafish (v9) 專案，聯發科 Humufish (A5922) 確立為 TPU 戰略核心。
* **2026-07-01** `目標價上修` 高盛調升聯發科目標價至 6,800 元，2027 年自研 ASIC 營收看至 203 億美元。
* **2028** `營收貢獻高峰` 聯發科 Humufish 2nm TPU 出貨上看 240-280 萬顆，貢獻營收占比 63-68%。

---

## 🔗 相關概念與個股連結 (Related Concepts)
* **關聯個股 (Stocks)**：`[[2330台積電]]`
* **關聯產業 (Garden)**：`[[2_晶片層_ASIC客製晶片]]`、`[[3_上游_測試與探針卡]]`

---

## 📄 原始文件與連結 (Original Documents)
* `[[20260702_143957_file.pdf]]`、`[[20260702_144121_file.pdf]]`、`[[20260525_004631_file.pdf.txt]]`、`[[20260710_002418_file.pdf]]` - 聯發科 (2454) Google TPU 相關研究報告
