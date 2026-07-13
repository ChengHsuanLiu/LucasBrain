# Wrapper invoked by Windows Task Scheduler instead of calling python directly.
# Handles: switching to the correct working directory, and writing output to a
# timestamped log file (Task Scheduler runs headless, no console to inspect on failure).
# Comments kept in English on purpose: legacy powershell.exe (5.1, invoked by
# Task Scheduler) can misparse non-ASCII characters in a BOM-less UTF-8 script file.
param(
    [Parameter(Mandatory = $true)][string]$ScriptName
)

$RepoRoot = "C:\Users\User\Desktop\LucasBrain"
$ScriptDir = "$RepoRoot\.agent\scripts"
$LogDir = "$RepoRoot\.agent\scheduled_logs"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BaseName = $ScriptName -replace '\.py$', ''
$LogFile = Join-Path $LogDir "$BaseName`_$Timestamp.log"

Set-Location $ScriptDir
$PythonExe = "C:\Users\User\AppData\Local\Microsoft\WindowsApps\python.exe"

"[$Timestamp] Starting $ScriptName" | Out-File -FilePath $LogFile -Encoding utf8
& $PythonExe $ScriptName 2>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append
$ExitCode = $LASTEXITCODE
"[$(Get-Date -Format 'yyyyMMdd_HHmmss')] Finished $ScriptName (exit code $ExitCode)" | Out-File -FilePath $LogFile -Encoding utf8 -Append

# Keep only the most recent 30 log files per script, to avoid unbounded growth.
Get-ChildItem -Path $LogDir -Filter "$BaseName`_*.log" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 30 |
    Remove-Item -Force -ErrorAction SilentlyContinue

# Auto-commit and push the report files this run generated. Scoped to today's dated
# output files in this script's own output dir (never `git add -A`), so any unrelated
# work-in-progress edits sitting elsewhere in the repo are never swept into this commit.
# Output dir names are ASCII on purpose (see file-header note on legacy powershell.exe
# misparsing non-ASCII in a BOM-less UTF-8 script); the date-glob below avoids needing
# the (non-ASCII) report filename stem at all.
$ReportOutputDirs = @{
    "generate_daily_report.py" = "30_Projects\Daily_Report"
    "scan_momentum_score.py"   = "30_Projects\Momentum_Screen"
}

if ($ExitCode -eq 0 -and $ReportOutputDirs.ContainsKey($ScriptName)) {
    $DateStem = Get-Date -Format "yyyyMMdd"
    $OutputDir = Join-Path $RepoRoot $ReportOutputDirs[$ScriptName]
    $Files = Get-ChildItem -Path $OutputDir -Filter "$DateStem`_*" -ErrorAction SilentlyContinue

    Set-Location $RepoRoot

    if ($Files) {
        "[$(Get-Date -Format 'yyyyMMdd_HHmmss')] Staging report files: $($Files.Name -join ', ')" | Out-File -FilePath $LogFile -Encoding utf8 -Append
        & git add -- $Files.FullName 2>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append

        $StagedDiff = & git diff --cached --name-only -- $Files.FullName
        if ($StagedDiff) {
            $CommitMsg = "chore: auto-generate $BaseName report ($(Get-Date -Format 'yyyy-MM-dd'))"
            & git commit -m $CommitMsg 2>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append
            & git push 2>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append
            "[$(Get-Date -Format 'yyyyMMdd_HHmmss')] Commit and push complete" | Out-File -FilePath $LogFile -Encoding utf8 -Append
        } else {
            "[$(Get-Date -Format 'yyyyMMdd_HHmmss')] No changes vs. last commit, skipping commit/push" | Out-File -FilePath $LogFile -Encoding utf8 -Append
        }
    } else {
        "[$(Get-Date -Format 'yyyyMMdd_HHmmss')] No output files found matching $DateStem`_* in $OutputDir, skipping commit" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    }
} elseif ($ExitCode -ne 0) {
    "[$(Get-Date -Format 'yyyyMMdd_HHmmss')] Script failed (exit $ExitCode), skipping commit/push" | Out-File -FilePath $LogFile -Encoding utf8 -Append
}
