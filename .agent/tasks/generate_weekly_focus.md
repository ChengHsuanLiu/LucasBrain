# 任務工作流：生成週報 (Generate Weekly Focus)

> [!NOTE]
> 此工作流旨在生成週度投資建議與持股追蹤報告。

## 📋 執行程序 (Execution Steps)

1. **執行自動化腳本**：
   * 執行以下 Python 腳本來掃描所有個股並生成週報：
     ```powershell
     python .agent/scripts/generate_weekly_focus.py
     ```
   * *備註：腳本亦可接受指定日期參數，例如 `python .agent/scripts/generate_weekly_focus.py 20260705`。*

2. **確認檔案生成與路徑**：
   * 確認新生成的週報檔案位於 `30_Projects/Weekly_Focus/` 底下，檔名為 `{YYYYMMDD}_Weekly_Focus.md`。

3. **回報執行結果**：
   * 告知使用者週報已成功生成，並提供該報告的點擊連結與簡短摘要。
