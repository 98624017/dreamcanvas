use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use dirs::data_dir;
use hex::encode as hex_encode;
use serde::{de::DeserializeOwned, Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use tauri::State;
use uuid::Uuid;

const PROJECT_FOLDER: &str = "DreamCanvas";
const PROJECT_SUBDIR: &str = "projects";

#[derive(Clone)]
pub struct ProjectManager {
  root: PathBuf,
}

impl ProjectManager {
  pub fn new() -> Self {
    let base = data_dir().unwrap_or_else(|| PathBuf::from("."));
    let root = base.join(PROJECT_FOLDER).join(PROJECT_SUBDIR);
    if let Err(err) = fs::create_dir_all(&root) {
      eprintln!("Failed to create project directory at {:?}: {}", root, err);
    }
    Self { root }
  }

  pub fn root(&self) -> PathBuf {
    self.root.clone()
  }

  fn project_dir(&self, project_id: &str) -> PathBuf {
    self.root.join(project_id)
  }

  fn manifest_path(&self, project_id: &str) -> PathBuf {
    self.project_dir(project_id).join("manifest.json")
  }

  fn canvas_path(&self, project_id: &str) -> PathBuf {
    self.project_dir(project_id).join("canvas.json")
  }

  fn assets_path(&self, project_id: &str) -> PathBuf {
    self.project_dir(project_id).join("assets.json")
  }

  fn history_path(&self, project_id: &str) -> PathBuf {
    self.project_dir(project_id).join("history.json")
  }

  pub fn list(&self) -> Result<Vec<ProjectSummary>, String> {
    let mut result = Vec::new();
    let entries = fs::read_dir(&self.root).map_err(|err| err.to_string())?;
    for entry in entries.flatten() {
      let project_dir = entry.path();
      if !project_dir.is_dir() {
        continue;
      }
      let manifest_path = project_dir.join("manifest.json");
      if !manifest_path.exists() {
        continue;
      }
      match read_json::<ProjectManifest>(&manifest_path) {
        Ok(manifest) => {
          let project_id = manifest.id.clone();
          let assets = read_json::<Vec<Value>>(&self.assets_path(&project_id)).unwrap_or_default();
          let history = read_json::<Vec<Value>>(&self.history_path(&project_id)).unwrap_or_default();
          result.push(ProjectSummary {
            manifest,
            assets: assets.len() as u64,
            history: history.len() as u64,
          });
        }
        Err(_) => continue,
      }
    }
    result.sort_by_key(|summary| summary.manifest.updated_at);
    result.reverse();
    Ok(result)
  }

  pub fn create(&self, name: String) -> Result<ProjectPayload, String> {
    let id = Uuid::new_v4().simple().to_string();
    let now = now_ms();
    let manifest = ProjectManifest {
      id: id.clone(),
      name,
      created_at: now,
      updated_at: now,
      version: "1.0.0".to_string(),
      canvas_checksum: String::new(),
    };
    let payload = ProjectPayload {
      manifest: manifest.clone(),
      canvas: json!({}),
      assets: Vec::new(),
      history: Vec::new(),
    };
    self.save(&payload)
  }

  pub fn load(&self, project_id: &str) -> Result<ProjectPayload, String> {
    let manifest = read_json::<ProjectManifest>(&self.manifest_path(project_id))?;
    let canvas = read_json::<Value>(&self.canvas_path(project_id)).unwrap_or_else(|_| json!({}));
    let assets = read_json::<Vec<AssetPayload>>(&self.assets_path(project_id)).unwrap_or_default();
    let history = read_json::<Vec<GenerationRecord>>(&self.history_path(project_id)).unwrap_or_default();
    Ok(ProjectPayload { manifest, canvas, assets, history })
  }

  pub fn save(&self, payload: &ProjectPayload) -> Result<ProjectPayload, String> {
    let project_id = &payload.manifest.id;
    if project_id.is_empty() {
      return Err("project id 不能为空".to_string());
    }
    let project_dir = self.project_dir(project_id);
    fs::create_dir_all(&project_dir).map_err(|err| err.to_string())?;

    let now = now_ms();
    let checksum = compute_checksum(&payload.canvas);
    let manifest = ProjectManifest {
      updated_at: now,
      canvas_checksum: checksum,
      ..payload.manifest.clone()
    };

    write_json(&self.manifest_path(project_id), &manifest)?;
    write_json(&self.canvas_path(project_id), &payload.canvas)?;
    write_json(&self.assets_path(project_id), &payload.assets)?;
    write_json(&self.history_path(project_id), &payload.history)?;

    Ok(ProjectPayload {
      manifest,
      canvas: payload.canvas.clone(),
      assets: payload.assets.clone(),
      history: payload.history.clone(),
    })
  }
}

impl Default for ProjectManager {
  fn default() -> Self {
    Self::new()
  }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ProjectManifest {
  pub id: String,
  pub name: String,
  pub created_at: u64,
  pub updated_at: u64,
  pub version: String,
  pub canvas_checksum: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct AssetPayload {
  pub id: String,
  pub project_id: String,
  pub kind: String,
  pub uri: String,
  pub metadata: Value,
  pub created_at: u64,
  pub updated_at: u64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct GenerationRecord {
  pub id: String,
  pub prompt: String,
  pub session_id: String,
  pub status: String,
  pub result_uris: Vec<String>,
  pub error: Option<String>,
  pub created_at: u64,
  pub completed_at: Option<u64>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ProjectPayload {
  pub manifest: ProjectManifest,
  #[serde(default)]
  pub canvas: Value,
  #[serde(default)]
  pub assets: Vec<AssetPayload>,
  #[serde(default)]
  pub history: Vec<GenerationRecord>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ProjectSummary {
  pub manifest: ProjectManifest,
  pub assets: u64,
  pub history: u64,
}

fn now_ms() -> u64 {
  SystemTime::now()
    .duration_since(UNIX_EPOCH)
    .map(|duration| duration.as_millis() as u64)
    .unwrap_or(0)
}

fn compute_checksum(value: &Value) -> String {
  let json_bytes = serde_json::to_vec(value).unwrap_or_default();
  let mut hasher = Sha256::new();
  hasher.update(json_bytes);
  hex_encode(hasher.finalize())
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), String> {
  if let Some(parent) = path.parent() {
    fs::create_dir_all(parent).map_err(|err| err.to_string())?;
  }
  let tmp_path = path.with_extension("tmp");
  let payload = serde_json::to_vec_pretty(value).map_err(|err| err.to_string())?;
  let mut file = File::create(&tmp_path).map_err(|err| err.to_string())?;
  file.write_all(&payload).map_err(|err| err.to_string())?;
  file.sync_all().map_err(|err| err.to_string())?;
  fs::rename(&tmp_path, path).map_err(|err| err.to_string())?;
  Ok(())
}

fn read_json<T: DeserializeOwned>(path: &Path) -> Result<T, String> {
  let content = fs::read_to_string(path).map_err(|err| err.to_string())?;
  serde_json::from_str(&content).map_err(|err| err.to_string())
}

#[tauri::command]
pub fn list_projects(manager: State<ProjectManager>) -> Result<Vec<ProjectSummary>, String> {
  manager.list()
}

#[tauri::command]
pub fn load_project(
  manager: State<ProjectManager>,
  project_id: String,
) -> Result<ProjectPayload, String> {
  manager.load(&project_id)
}

#[tauri::command]
pub fn save_project(
  manager: State<ProjectManager>,
  payload: ProjectPayload,
) -> Result<ProjectPayload, String> {
  manager.save(&payload)
}

#[tauri::command]
pub fn create_project(
  manager: State<ProjectManager>,
  name: String,
) -> Result<ProjectPayload, String> {
  manager.create(name)
}
