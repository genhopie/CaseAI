Write-Host "Building standalone API EXE using PyInstaller..."

cd services\local_api

if (-not (Test-Path .venv)) {
    py -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --onefile --name lcai_api app\main.py

Write-Host ""
Write-Host "EXE created in services\local_api\dist\lcai_api.exe"
Write-Host "You still need Node build for UI separately."
