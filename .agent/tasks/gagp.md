# 任務工作流：Git Add, Commit and Push (gagp)

> [!NOTE]
> 此工作流旨在快速將工作區的所有變更進行暫存、提交並推送到遠端 Git 倉庫。

## 📋 執行程序 (Execution Steps)

1. **偵測與確認變更**：
   * 執行 `git status` 確認當前的工作區狀態，檢視有哪些檔案被修改、新增或刪除。

2. **暫存所有檔案**：
   * 執行以下命令暫存所有變更：
     ```powershell
     git add -A
     ```

3. **自動生成或使用指定的 Commit 訊息**：
   * 如果前續步驟有建議的 Commit 訊息（例如 `ingest: 20260704_232844_text...`），則優先採用。
   * 若無，則根據修改的檔案類型與檔名自動生成簡短描述。

4. **執行提交**：
   * 執行以下命令提交變更：
     ```powershell
     git commit -m "Your Commit Message"
     ```

5. **執行推送**：
   * 執行以下命令將變更推送到遠端：
     ```powershell
     git push
     ```

6. **回報執行結果**：
   * 告知使用者 Git 提交與推送成功，並列出提交的 Commit Hash 與訊息。
