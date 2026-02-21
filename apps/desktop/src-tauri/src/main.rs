use std::process::Command;
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let resource_dir = app
                .path_resolver()
                .resource_dir()
                .expect("failed to get resource dir");

            let backend_path = resource_dir.join("bin").join("lcai_api.exe");

            if backend_path.exists() {
                Command::new(backend_path)
                    .spawn()
                    .expect("failed to start backend");
            } else {
                println!("Backend exe not found at {:?}", backend_path);
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
