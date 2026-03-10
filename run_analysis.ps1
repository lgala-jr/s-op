# Dispense Method Analysis - Full Pipeline
# Prerequisites: Python with pip, BigQuery CLI (bq) for real data
# Run from project root: .\run_analysis.ps1

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
Set-Location $projectRoot

# Full path to bq and Cloud SDK bin (bq needs gcloud on PATH for auth)
$cloudSdkBin = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
$bqPath = "$cloudSdkBin\bq.cmd"
$env:Path = "$cloudSdkBin;$env:Path"

# Ensure Cloud SDK finds credentials
$env:CLOUDSDK_CONFIG = "$env:APPDATA\gcloud"

# Create output dir
New-Item -ItemType Directory -Path "output" -Force | Out-Null

Write-Host "=== Dispense Method Analysis ===" -ForegroundColor Cyan

if (-not (Test-Path $bqPath)) {
    Write-Host "ERROR: BigQuery CLI (bq) not found at $bqPath." -ForegroundColor Red
    Write-Host "Install Google Cloud SDK and ensure bq is on PATH. This process requires real data." -ForegroundColor Red
    exit 1
}

Write-Host "`n1. Exporting base data from BigQuery..." -ForegroundColor Green
$query = Get-Content "sql\01_base_data.sql" -Raw
# Suppress stderr (bq writes progress to stderr; PowerShell treats it as error with $ErrorActionPreference = "Stop")
$result = $query | & $bqPath query --use_legacy_sql=false --format=csv --max_rows=1000000 2>$null
$result | Out-File -FilePath "output\base_data.csv" -Encoding utf8

$firstLine = (Get-Content "output\base_data.csv" -First 1 -ErrorAction SilentlyContinue) -join ""
if (-not $firstLine -or $firstLine -match "BigQuery error|Error retrieving auth") {
    Write-Host "ERROR: BigQuery export failed. Run: gcloud auth application-default login" -ForegroundColor Red
    Write-Host "This process requires real data from BigQuery." -ForegroundColor Red
    exit 1
}

Write-Host "`n2. Running feature selection..." -ForegroundColor Green
python feature_selection.py output/base_data.csv

Write-Host "`n3. Generating summary stats and distributions..." -ForegroundColor Green
python run_analysis_from_base.py

Write-Host "`n4. Generating Word report..." -ForegroundColor Green
python generate_report.py

Write-Host "`n5. Building dispense ratio lookup (for forecast allocation)..." -ForegroundColor Green
python build_dispense_ratios.py

Write-Host "`n=== Done ===" -ForegroundColor Cyan
Write-Host "Reports: output\Dispense_Method_Analysis_Report.docx"
Write-Host "Ratio lookup: output\dispense_ratio_lookup.csv (apply to forecast volume)"
