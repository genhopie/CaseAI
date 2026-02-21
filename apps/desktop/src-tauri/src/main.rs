#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Child};
use std::path::PathBuf;
use tauri::{AppHandle, Manager};

fn backend_exe_path(app: &AppHandle) -> PathBuf {
    let resource_dir = app.path().resource_dir().expect("resource_dir");
    resource_dir.join("bin").join("lcai_api.exe")
}

fn spawn_backend(app: &AppHandle) -> Option<Child> {
    let exe = backend_exe_path(app);
    if !exe.exists() {
        eprintln!("Backend exe not found at: {:?}", exe);
        return None;
    }

    // Bind only to localhost. Port is fixed for MVP (8787).
    // In later phases we can randomize a free port and pass via env var.
    let mut cmd = Command::new(exe);
    cmd.env("LCAI_PORT", "8787");
    cmd.env("LCAI_JWT_SECRET", "CHANGE_ME_DEV_ONLY");
    cmd.spawn().ok()
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Start backend
            let handle = app.handle().clone();
            let child = spawn_backend(&handle);

            // Store child handle for shutdown
            app.manage(BackendChild(child));
            Ok(())
        })
        .on_window_event(|window, event| {
            // No-op; could add behavior later.
            let _ = (window, event);
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

struct BackendChild(Option<Child>);

impl Drop for BackendChild {
    fn drop(&mut self) {
        if let Some(child) = &mut self.0 {
            let _ = child.kill();
        }
    }
}
