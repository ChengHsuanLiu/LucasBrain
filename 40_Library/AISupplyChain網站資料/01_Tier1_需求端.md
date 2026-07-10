---
type: library_reference
title: "Tier 1：需求端（AI 實驗室／雲端／軟體平台）"
created: 2026-07-10
updated: 2026-07-10
tags: [library, external-source, ai-supply-chain]
source_type: web_capture
source_url: "https://supply-chain-map.pages.dev/learn"
---

# Tier 1：需求端

> 回索引：[[00_總覽與快速入門]]

這一層是整條供應鏈資金的起點：AI 實驗室訓練/推論模型消耗運算資源，雲端平台把運算資源租給客戶，並持續加碼資本支出擴建資料中心，資金再往下傳導到晶片、伺服器、記憶體供應商。

## 環節重點（改寫整理）
- AI 實驗室透過與雲端/GPU 供應商簽訂的長期大額合約鎖定運算資源，把需求傳導到上游。
- 雲端平台（CSP）扮演中游角色：一邊承接 AI 實驗室需求，一邊利用既有企業客戶關係與雲生態圈把 AI 產品內嵌進去；部分 CSP 自研晶片（TPU、Trainium）強化中游議價力。
- 訓練 vs. 推論的採購策略不同；商業化路徑分歧明顯（OpenAI 以消費端訂閱為主 vs. Anthropic 以企業/API 為主）；Meta 走開源 Llama 路線的策略仍具不確定性。
- 護城河：資本規模直接決定能否持續參與軍備競賽；生態圈綁定（如 Microsoft Azure + M365 + OpenAI）；專屬資料飛輪（Google/Meta 自有資料 vs. OpenAI/Anthropic/xAI 依賴公開網路資料）。

## AI Labs / Models（AI 實驗室與模型公司）

- **OpenAI**（未上市）：ChatGPT 消費訂閱 + API 雙軌營收模式；2026年3月完成122億美元募資，投後估值852億美元；2026年6月8日向SEC遞交IPO S-1草案；與Microsoft、Oracle、CoreWeave簽訂大型算力合約。
- **Anthropic**（未上市）：以 Claude API 與企業合約為核心營收；2026年5月完成H輪募資650億美元，估值達965億美元；與AWS、Google Cloud有大型算力合作。
- **xAI**（未上市）：Grok 模型整合進 Tesla 與 X 平台；2026年1月E輪募資約200億美元，估值2,300億美元；2026年2月SpaceX以全股票方式收購約2,500億美元；未揭露ARR/營收數字。
- **SoftBank Group (9984)**：由電信控股公司轉型為AI資本掮客角色；截至2026年2月對OpenAI累計投資644億美元；持有Arm股權並以65億美元收購Ampere Computing強化AI晶片架構與伺服器CPU設計能力；2026年3月推出Arm AGI CPU；FY2025 OpenAI未實現收益約450億日圓（約3.02億美元）。

## 雲端／軟體平台

- **Microsoft (MSFT)**：Azure AI營收年化跑率FY26 Q3超過370億美元（年增123%）；雲端商用RPO年增99%達6,270億美元；與OpenAI技術整合最深的CSP之一。
- **Alphabet/Google (GOOGL)**：唯一同時擁有自研AI晶片(TPU)、雲端服務、前沿模型(Gemini)三位一體的公司；Google Cloud FY26 Q1營收年增63%；Ironwood TPU於2025年11月正式推出。
- **Amazon (AMZN)**：全球最大雲端業者AWS母公司；自研Trainium晶片+對Anthropic策略性投資(累計上限330億美元)強化中游地位；2026 Q1 AWS營收376億美元，年增28%。
- **Meta (META)**：唯一拒絕對外出租雲端算力的巨額資本支出玩家；FY26資本支出指引上修至1,250-1,450億美元，全數用於自用AI基礎建設與Llama開源生態；開放vs封閉模型路線仍存在策略矛盾。
- **Oracle (ORCL)**：由傳統資料庫廠商轉型AI雲端基礎建設；FY26 Q4 RPO達6,380億美元(年增363%)，主要由OpenAI大型合約驅動(具體條款未經管理層電話會議正式證實)。
- **CoreWeave (CRWV)**：專營Nvidia GPU雲端出租；透過OpenAI(合約上限224億美元)與Microsoft長約擴大規模；訂單積壓從2025年底668億美元增至2026 Q1的994億美元；客戶集中度為核心風險。
- **Palantir (PLTR)**：AIP平台把大模型能力嵌入企業/政府決策流程；2026 Q1營收16.33億美元，年增85%；同時服務國防與商業客戶。
- **Fujitsu (6702)**：日系IT服務與伺服器製造商；Uvance為主要AI品牌，官方財報未單獨拆分AI營收；FY2025合併營收3兆5,029億日圓，Uvance營收7,093億日圓，年增46.9%。

## 這一層要追蹤的指標方向
募資輪次與估值變化、RPO（未來營收保證）、四大CSP資本支出年度指引與實際執行落差、Nvidia資料中心營收 vs. CSP資本支出的擷取率、Token使用率／推論吞吐量。四大CSP 2025全年資本支出合計約4,100億美元，2026展望上修至約7,250億美元（年增77%）；Microsoft FY26資本支出上修至約1,900億美元（其中約250億美元歸因於記憶體/零組件通膨）；Alphabet FY25實際支出914億美元，FY26展望1,800-1,900億美元；Amazon FY25約1,318億美元，FY26展望約2,000億美元（年增約52%）。
