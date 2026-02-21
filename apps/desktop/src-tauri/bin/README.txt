Place lcai_api.exe here for bundling.

Build it on Windows with:
  powershell -ExecutionPolicy Bypass -File ..\..\..\BUILD_BACKEND_EXE_WINDOWS.ps1

This creates:
  services\local_api\dist\lcai_api.exe

Copy it to:
  apps\desktop\src-tauri\bin\lcai_api.exe
