$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Virtual environment not found at .venv"
    Write-Host "Create it with: python -m venv .venv"
    Write-Host "Then install dependencies with: .\.venv\Scripts\python.exe -m pip install -e ."
    exit 1
}

Set-Location $repoRoot
& $python -m streamlit run aero_lab/streamlit_app.py
