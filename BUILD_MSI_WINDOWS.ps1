Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "== Build Windows MSI (Tauri) =="

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# 1) Build backend exe if missing
$backend = "apps\desktop\src-tauri\bin\lcai_api.exe"
if (-not (Test-Path $backend)) {
  Write-Host "Backend EXE missing. Building it now..."
  powershell -ExecutionPolicy Bypass -File .\BUILD_BACKEND_EXE_WINDOWS.ps1
}

# 2) Install UI deps
Set-Location apps\desktop
npm install

# 3) Build MSI
npm run tauri:build

Write-Host ""
Write-Host "MSI output is under:"
Write-Host "  apps\desktop\src-tauri\target\release\bundle\msi\"
