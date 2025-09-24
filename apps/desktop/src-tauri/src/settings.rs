use std::fs::{self, File};
use std::io::BufReader;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use dirs::config_dir;
use serde::{Deserialize, Serialize};
use tauri::State;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AppSettings {
  #[serde(default)]
  pub web_app_url: Option<String>,
  #[serde(default)]
  pub auto_open: bool,
}

pub struct SettingsManager {
  path: PathBuf,
  inner: Mutex<AppSettings>,
}

impl SettingsManager {
  pub fn new() -> Self {
    let base_dir = config_dir()
      .unwrap_or_else(|| PathBuf::from("."))
      .join("DreamCanvas");
    let path = base_dir.join("ui-settings.json");
    let settings = Self::load_from_disk(&path).unwrap_or_default();

    Self {
      path,
      inner: Mutex::new(settings),
    }
  }

  fn load_from_disk(path: &Path) -> Result<AppSettings, String> {
    if !path.exists() {
      return Ok(AppSettings::default());
    }
    let file = File::open(path).map_err(|err| format!("读取设置文件失败: {err}"))?;
    let reader = BufReader::new(file);
    serde_json::from_reader(reader).map_err(|err| format!("解析设置文件失败: {err}"))
  }

  fn persist(&self, settings: &AppSettings) -> Result<(), String> {
    if let Some(parent) = self.path.parent() {
      fs::create_dir_all(parent).map_err(|err| format!("创建配置目录失败: {err}"))?;
    }
    let content = serde_json::to_string_pretty(settings)
      .map_err(|err| format!("序列化设置失败: {err}"))?;
    fs::write(&self.path, content).map_err(|err| format!("写入设置失败: {err}"))
  }

  pub fn current(&self) -> AppSettings {
    self.inner
      .lock()
      .expect("获取设置锁失败")
      .clone()
  }

  pub fn update(&self, mut settings: AppSettings) -> Result<(), String> {
    if let Some(url) = settings.web_app_url.as_ref() {
      let trimmed = url.trim();
      if trimmed.is_empty() {
        settings.web_app_url = None;
      } else {
        settings.web_app_url = Some(trimmed.to_string());
      }
    }

    {
      let mut guard = self.inner.lock().expect("获取设置锁失败");
      *guard = settings.clone();
    }

    self.persist(&settings)
  }

  pub fn open_web_app(&self) -> Result<(), String> {
    let settings = self.inner.lock().expect("获取设置锁失败");
    let url = settings
      .web_app_url
      .as_ref()
      .ok_or_else(|| "尚未配置 Web 应用地址".to_string())?
      .to_string();

    open::that(&url).map_err(|err| format!("无法在浏览器中打开 {url}: {err}"))
  }
}

#[tauri::command]
pub fn load_settings(state: State<SettingsManager>) -> AppSettings {
  state.current()
}

#[tauri::command]
pub fn save_settings(state: State<SettingsManager>, settings: AppSettings) -> Result<(), String> {
  state.update(settings)
}

#[tauri::command]
pub fn open_web_app(state: State<SettingsManager>) -> Result<(), String> {
  state.open_web_app()
}
