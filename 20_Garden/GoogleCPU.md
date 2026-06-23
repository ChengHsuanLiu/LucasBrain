---
type: industry
title: "GoogleCPU"
created: 2026-06-22
updated: 2026-06-22
review_by: 2026-09-22
tags: [investment/target, googlecpu]
source_type: manual_note
source_asset: Various
aliases: [Google CPU, Axion, TPU]
---

# GoogleCPU

## 摘要 (Summary)
- **ARM 架構與 TPU 自研晶片**：Google 自研的伺服器 CPU (如 Google Axion) 與張量處理器 (TPU，用於加速 AI 機器學習運算)。
- **晶片技術與封裝規格升級**：
  - **Axion CPU**：當前採用 3nm 製程搭配高規格 FCBGA 封裝，需要大量的 Serdes 連接。
  - **TPU v9**：技術路徑出現重大分水嶺，分為博通的 Whalefish 平台（維持在 3nm 製程與 HBM3e 記憶體）與**聯發科的 Humufish 平台（A5922，升級至 2nm 製程並搭載 HBM4e 記憶體）**。
  - **先進封裝良率突破**：2nm TPU 透過 embedding/TGV（Through Glass Via）技術以及高規格 Si-Cap 矽電容，使 EMIB 封裝良率成功突破 90% 以上。

## 核心發現 (Core Findings)

## 關鍵洞察 (Key Insights)

## 第二層思考 (Second-Level Thinking)

## 第一性原理分析 (First Principles Analysis)

## 近期的產業未來趨勢與重要時間軸 (例如: 產品換代、材料升級及其時間軸)
- **大廠去博通化 (De-Broadcomization) 與路線更迭**：
  - Google 於近期取消了博通原始的 TPU v9 專案 Pumafish，取而代之的是 Whalefish（Sunfish Ultra，由兩顆 TPU 8i 堆疊）。這反映 Google 戰略核心往聯發科 2nm 專案 Humufish (A5922) 傾斜，博通退為輔助。
  - 設計服務與特化封裝材料（如矽電容）本土化：雲端巨頭尋求日、美系以外的 Second Source 以規避產能限制。

## 產業主要上中下游廠商 (各公司分別負責什麼部分，預估今明年 EPS 多少?)
- **上游/晶片設計服務、IP 與材料**：
  - `[[3443創意]]` (3443)：負責 Google Axion CPU 的後端設計服務與量產 Turnkey。預期 2H26 營收受惠其放量而季增。預估 2026/2027 EPS 分別為 `90-125 / 200 元`。
  - `[[2454聯發科]]` (2454)：作為 Google TPU 新世代的核心合作對象，負責 2nm v9 Humufish (A5922) 與未來 v10 (Icefish) 的設計研發。預估 2027/2028 EPS 分別為 `133.7-133.89 / 279.4-280.6 元`。
  - `[[6531愛普]]` (6531)：提供先進封裝必備之高規格 Si-Cap 矽電容。預估 2026-2028 EPS 分別為 `20 / 50 / 100 元`。
  - `[[Broadcom]]` (博通)：負責 Whalefish 平台，地位轉為互補。
- **中游/晶圓代工與封裝**：
  - `[[TSMC]]`：先進製程製造與 3D/CoWoS/EMIB 先進封裝。
  - `[[2303聯電]]`：協助代工愛普的 Si-Cap 矽電容晶圓。
- **下游/系統品牌**：
  - Google (谷歌)：自研並部署於資料中心伺服器集群。

## 產業主要用途以及客戶有誰?
- Google 雲端資料中心伺服器群。

## 相關概念連結 (Related Concepts)

## 原始文件及連結 (Original Document)
- `[[20260525_003204_text.md]]` - 聯發科 A5922 測試版供應鏈
- `[[20260525_004331_text.md]]` - 里昂證券 (CLSA) 聯發科 TPU 完整分析
- `[[20260526_124223_text.md]]` - 美系大行聯發科出貨上調與封裝分析
- `[[20260601_000014_text.md]]` - 愛普 Si-Cap 產能規劃與聯電代工詳情
- `[[20260620_213639_text.md]]` - 創意 3443 專案營收與毛利分析
- `[[20260622_145237_text.md]]` - 創意 GUC 法說 Q&A 與 CPU 設計
