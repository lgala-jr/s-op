# Task Productivity Analysis - Verify Tasks with Auto Dispensed cut
# Run from project root: .\run_verify_task_productivity_auto_dispensed.ps1
# Prerequisites: BigQuery CLI (bq), Python

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$cloudSdkBin = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
$bqPath = "$cloudSdkBin\bq.cmd"
$env:Path = "$cloudSdkBin;$env:Path"
$env:CLOUDSDK_CONFIG = "$env:APPDATA\gcloud"

New-Item -ItemType Directory -Path "output" -Force | Out-Null

Write-Host "=== Task Productivity Analysis (Verify Tasks + Auto Dispensed) ===" -ForegroundColor Cyan

Write-Host "`n1. Exporting data from BigQuery..." -ForegroundColor Green
Write-Host "   (Large datasets may take 2-5 min; progress shown when complete)" -ForegroundColor Gray
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$query = Get-Content "sql\verify_task_productivity_auto_dispensed.sql" -Raw
$ErrorActionPreference = "Continue"
$result = $query | & $bqPath query --use_legacy_sql=false --format=csv --max_rows=10000000 2>$null
$ErrorActionPreference = "Stop"
$result | Out-File -FilePath "output\verify_task_productivity_auto_dispensed.csv" -Encoding utf8
$sw.Stop()
Write-Host "   Export completed in $([math]::Round($sw.Elapsed.TotalSeconds, 1))s" -ForegroundColor Gray

$firstLine = (Get-Content "output\verify_task_productivity_auto_dispensed.csv" -First 1 -ErrorAction SilentlyContinue) -join ""
if (-not $firstLine -or $firstLine -match "BigQuery error|Error retrieving auth") {
    Write-Host "ERROR: BigQuery export failed. Run: gcloud auth application-default login" -ForegroundColor Red
    exit 1
}

Write-Host "`n2. Running analysis and generating report..." -ForegroundColor Green
$sw2 = [System.Diagnostics.Stopwatch]::StartNew()
python verify_task_productivity_auto_dispensed_analysis.py
$sw2.Stop()
Write-Host "   Analysis completed in $([math]::Round($sw2.Elapsed.TotalSeconds, 1))s" -ForegroundColor Gray

Write-Host "`n=== Done ===" -ForegroundColor Cyan
Write-Host "Output: output\verify_task_productivity_auto_dispensed\ad_verify_task_productivity_report.docx"
[Console]::Beep(800, 200)
Read-Host "`nPress Enter to close"
