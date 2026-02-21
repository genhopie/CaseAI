Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "[1/2] Starting API..."
Push-Location services\local_api
py -m venv .venv | Out-Null
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Start-Process -NoNewWindow -FilePath "py" -ArgumentList "-m app.main"
Pop-Location

Write-Host "[2/2] Starting UI..."
Push-Location apps\desktop
npm install
npm run dev
Pop-Location
