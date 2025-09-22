#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;

use backend::{backend_status, start_backend, stop_backend, BackendManager};
use tauri::{AppHandle, Manager};
use tauri_plugin_log::{Builder as LogBuilder, LogTarget};

fn main() {
  tauri::Builder::default()
    .manage(BackendManager::default())
    .plugin(
      LogBuilder::new()
        .targets([LogTarget::Stdout, LogTarget::Webview])
        .build()
        .expect("初始化日志插件失败"),
    )
    .setup(|app| {
      let handle: AppHandle = app.handle();
      handle.emit_all("app://ready", ())?;
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![start_backend, stop_backend, backend_status])
    .run(tauri::generate_context!())
    .expect("运行 DreamCanvas 失败");
}
