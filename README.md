# Local Case AI MVP (Baseline)
Local-first baseline: React (Vite) UI + FastAPI local API. Cross-platform (Windows/Mac) dev run supported.

## What this baseline includes (M0)
- Local API (FastAPI) with:
  - Local auth (single user, password stored as salted hash)
  - Case CRUD
  - Document upload per case (stores original files under ./data/storage)
  - Journal (append-only)
- Desktop UI (React/Vite) with:
  - Login
  - Case list + create
  - Document upload + list

## What this baseline does NOT include yet
- OCR / PDF text extraction
- Search, embeddings, RAG, timeline, tasks, graph
These are added in next modules.

## Prereqs
- Python 3.10+
- Node.js 18+

## Run (Mac/Linux)
1) API
   cd services/local_api
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python -m app.main

2) UI
   cd apps/desktop
   npm install
   npm run dev

Open the UI shown in the terminal (usually http://localhost:5173)

## Run (Windows PowerShell)
1) API
   cd services\local_api
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   py -m app.main

2) UI
   cd apps\desktop
   npm install
   npm run dev

## Default user
On first run, API will create an admin user:
- username: admin
- password: admin1234
Change it immediately in Settings (next module). For now, change by deleting ./data/db.sqlite and restarting.

## Security note (Mode S)
This baseline is local-only. Do NOT expose it to the internet as-is.
Remote access will be added later via Tailscale/Cloudflare Tunnel + MFA + rate limits.


------------------------------------------------------------
WINDOWS ONE-CLICK START
------------------------------------------------------------

You can run the entire system with:

INSTALL_AND_START_WINDOWS.bat

This will:
1. Create Python virtual environment
2. Install API dependencies
3. Start API server
4. Install UI dependencies
5. Start UI server

------------------------------------------------------------
BUILD STANDALONE API EXE (OPTIONAL)
------------------------------------------------------------

Run in PowerShell:

BUILD_API_EXE_WINDOWS.ps1

This creates:
services\local_api\dist\lcai_api.exe

Note:
UI still requires Node unless later bundled with Electron.


============================================================
WINDOWS FIRST: REAL DESKTOP INSTALLER (MSI) - NO DEV FLOW
============================================================

Goal:
- One MSI installer
- No browser usage
- App starts its own local backend internally

What you do on Windows (once):
1) Install Node.js 18+
2) Install Rust (rustup)
3) Open PowerShell in the project root

Build MSI:
  powershell -ExecutionPolicy Bypass -File .\BUILD_MSI_WINDOWS.ps1

This will:
- Build backend EXE (PyInstaller)
- Copy lcai_api.exe into Tauri resources
- Build a Windows MSI

Output:
  apps\desktop\src-tauri\target\release\bundle\msi\

Install the MSI. Then launch "Local Case AI".

Note:
This is Mode S (safe). Backend binds only to 127.0.0.1.
Do not expose ports to internet.
