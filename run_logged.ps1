# Usage: run_logged.ps1 <action>   (install | echo | bot | app)
param([string]$action = "bot")
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"; $env:PYTHONUNBUFFERED = "1"
$env:Path = "$env:USERPROFILE\.local\bin;" + [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
$log = Join-Path $PSScriptRoot "$action.log"
"[$action] started $(Get-Date)" | Out-File $log -Encoding utf8
function Say($m) { Write-Host $m -ForegroundColor Cyan; $m | Out-File $log -Append -Encoding utf8 }
function Run($c) {
    Say "> $c"
    cmd /c "$c 2>&1" | ForEach-Object { Write-Host $_; $_ | Out-File $log -Append -Encoding utf8 }
    Say "exit code: $LASTEXITCODE"
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Say "ERROR: uv not found (run the CrewAI setup first or install uv)."; Read-Host "Enter to close"; exit 1 }

switch ($action) {
    "install" {
        Run "uv sync --python 3.12"
        Run "uv run python check_install.py"
        if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Say "Created .env - paste your Slack tokens into it." }
        Start-Process notepad.exe ".env"
    }
    "echo" { Run "uv run python step1_test_bot.py" }
    "bot"  { Run "uv run python bot.py" }
    "app"  { Run "uv run python gradio_app.py" }
}
Read-Host "`nPress Enter to close"
