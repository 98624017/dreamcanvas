#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;
mod project;
mod settings;

use backend::{backend_status, start_backend, stop_backend, BackendManager};
use project::{create_project, list_projects, load_project, save_project, ProjectManager};
use settings::{load_settings, open_web_app, save_settings, SettingsManager};
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_log::{Builder as LogBuilder, Target, TargetKind};

fn main() {
  tauri::Builder::default()
    .manage(BackendManager::default())
    .manage(ProjectManager::default())
    .manage(SettingsManager::new())
    .plugin(
      LogBuilder::new()
        .targets([
          Target::new(TargetKind::Stdout),
          Target::new(TargetKind::Webview),
        ])
        .build(),
    )
    .setup(|app| {
      let handle: AppHandle = app.handle().clone();
      let settings_state = app.state::<SettingsManager>();
      let current_settings = settings_state.current();

      if current_settings.auto_open {
        if let Err(err) = settings_state.open_web_app() {
          eprintln!("自动打开浏览器失败：{err}");
        }
      }

      handle.emit("app://ready", ())?;
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
      start_backend,
      stop_backend,
      backend_status,
      list_projects,
      load_project,
      save_project,
      create_project,
      load_settings,
      save_settings,
      open_web_app
    ])
    .run(tauri::generate_context!())
    .expect("运行 DreamCanvas 失败");
}
