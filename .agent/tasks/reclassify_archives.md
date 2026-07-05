# 任務工作流：重新分類封存檔案 (Reclassify Archives)

> [!NOTE]
> 此工作流旨在對 `98_Archives/` 目錄下的所有子資料夾（包括已分類的）與檔案進行完整重組，以契合最新的五維度封存定義。

## 📋 執行程序 (Execution Steps)

1. **環境與路徑確認**：
   * 確保工作路徑為專案根目錄。
   * 檔案庫包含 `98_Archives/Expert_Meetings`、`98_Archives/Research_Report`、`98_Archives/Stock_Memo`、`98_Archives/Fund_Company_Memo` 與 `98_Archives/Others`。

2. **執行自動化腳本**：
   * 執行以下 Python 腳本來重新掃描並歸類所有歷史檔案：
     ```powershell
     python .agent/scripts/classify_archives_v2.py
     ```

3. **手動核對與分類結果報告**：
   * 檢視腳本輸出之分類統計數據。
   * 向使用者報告遷移檔案的數量。
