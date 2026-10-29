param (
    [ValidateSet("login", "refresh-profile", "search-apply", "inbox", "email")]
    [string]$Mode = "search-apply"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$ScriptDir\vedant-naukri-agent"

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Running Naukri Agent: Mode = $Mode" -ForegroundColor Green
Write-Host " Working Directory: $PWD" -ForegroundColor DarkGray
Write-Host "=================================================" -ForegroundColor Cyan

python scripts\pi_naukri_agent.py --mode $Mode $args
