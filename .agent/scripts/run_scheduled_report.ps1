# Wrapper invoked by Windows Task Scheduler instead of calling python directly.
# Handles: switching to the correct working directory, and writing output to a
# timestamped log file (Task Scheduler runs headless, no console to inspect on failure).
# Comments kept in English on purpose: legacy powershell.exe (5.1, invoked by
# Task Scheduler) can misparse non-ASCII characters in a BOM-less UTF-8 script file.
param(
    [Parameter(Mandatory = $true)][string]$ScriptName
)

$ScriptDir = "C:\Users\User\Desktop\LucasBrain\.agent\scripts"
$LogDir = "C:\Users\User\Desktop\LucasBrain\.agent\scheduled_logs"

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
"[$(Get-Date -Format 'yyyyMMdd_HHmmss')] Finished $ScriptName (exit code $LASTEXITCODE)" | Out-File -FilePath $LogFile -Encoding utf8 -Append

# Keep only the most recent 30 log files per script, to avoid unbounded growth.
Get-ChildItem -Path $LogDir -Filter "$BaseName`_*.log" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 30 |
    Remove-Item -Force -ErrorAction SilentlyContinue
