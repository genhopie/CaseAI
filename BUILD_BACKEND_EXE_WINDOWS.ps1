Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "== Build backend EXE (FastAPI) and copy into Tauri resources =="

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Set-Location services\local_api

if (-not (Test-Path .venv)) {
  py -m venv .venv | Out-Null
}

& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller

# Build onefile exe. Note: reload disabled in packaged mode by env flag.
pyinstaller --onefile --name lcai_api app\main.py

$exe = Join-Path (Get-Location) "dist\lcai_api.exe"
if (-not (Test-Path $exe)) {
  throw "EXE not found: $exe"
}

Set-Location $root
$dst = "apps\desktop\src-tauri\bin\lcai_api.exe"
Copy-Item -Force $exe $dst

Write-Host ""
Write-Host "OK: Copied to $dst"
