param (
    [ValidateSet("login", "scan-posts", "easy-apply", "pipeline", "referral", "email", "inbox")]
    [string]$Mode = "easy-apply"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$ScriptDir\vedant-job-agent"

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Running LinkedIn Agent: Mode = $Mode" -ForegroundColor Green
Write-Host " Working Directory: $PWD" -ForegroundColor DarkGray
Write-Host "=================================================" -ForegroundColor Cyan

python scripts\pi_linkedin_agent.py --mode $Mode $args
