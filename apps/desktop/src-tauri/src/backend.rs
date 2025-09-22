use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{atomic::{AtomicBool, Ordering}, Arc, Mutex};
use std::time::Duration;

use serde::Serialize;
use tauri::AppHandle;

const SRC_PY_DIR: &str = "src-py";
const STDOUT_EVENT: &str = "backend://stdout";
const STDERR_EVENT: &str = "backend://stderr";
const STARTED_EVENT: &str = "backend://started";
const STOPPED_EVENT: &str = "backend://stopped";

pub struct BackendManager {
  backend_dir: PathBuf,
  process: Arc<Mutex<Option<Child>>>,
  manual_stop: Arc<AtomicBool>,
}

impl BackendManager {
  pub fn new() -> Self {
    let base = Path::new(env!("CARGO_MANIFEST_DIR"))
      .join("..")
      .join("..")
      .canonicalize()
      .unwrap_or_else(|_| Path::new(env!("CARGO_MANIFEST_DIR")).to_path_buf());
    let backend_dir = base.join(SRC_PY_DIR);
    Self {
      backend_dir,
      process: Arc::new(Mutex::new(None)),
      manual_stop: Arc::new(AtomicBool::new(false)),
    }
  }

  fn backend_dir_string(&self) -> String {
    self.backend_dir.to_string_lossy().to_string()
  }

  fn python_bin(&self) -> String {
    std::env::var("DC_PYTHON_BIN").unwrap_or_else(|_| "python".to_string())
  }

  fn ensure_process_slot(&self) {
    let mut guard = self.process.lock().expect("获取后端进程锁失败");
    if let Some(child) = guard.as_mut() {
      if let Ok(Some(_status)) = child.try_wait() {
        *guard = None;
      }
    }
  }

  fn spawn_monitor(&self, app: &AppHandle) {
    let process_ref = Arc::clone(&self.process);
    let manual_flag = Arc::clone(&self.manual_stop);
    let app_handle = app.clone();

    std::thread::spawn(move || loop {
      std::thread::sleep(Duration::from_millis(500));
      let mut guard = process_ref.lock().expect("获取后端进程锁失败");
      if let Some(child) = guard.as_mut() {
        if let Ok(Some(_status)) = child.try_wait() {
          *guard = None;
          drop(guard);
          if !manual_flag.load(Ordering::SeqCst) {
            let _ = app_handle.emit_all(
              STOPPED_EVENT,
              BackendStoppedEvent {
                reason: "exited".to_string(),
              },
            );
          }
          break;
        }
      } else {
        break;
      }
    });
  }

  pub fn spawn(&self, app: &AppHandle, reload: bool) -> Result<(), String> {
    self.ensure_process_slot();
    {
      let guard = self.process.lock().expect("获取后端进程锁失败");
      if guard.is_some() {
        return Ok(());
      }
    }

    self.manual_stop.store(false, Ordering::SeqCst);

    let python_bin = self.python_bin();
    let mut cmd = Command::new(python_bin);
    cmd.current_dir(&self.backend_dir)
      .arg("-m")
      .arg("poetry")
      .arg("run")
      .arg("uvicorn")
      .arg("dreamcanvas.app:app")
      .arg("--host")
      .arg("127.0.0.1")
      .arg("--port")
      .arg("18500")
      .stdout(Stdio::piped())
      .stderr(Stdio::piped());

    if reload {
      cmd.arg("--reload");
    }

    let mut child = cmd
      .spawn()
      .map_err(|err| format!("启动后端失败: {err}"))?;

    if let Some(stdout) = child.stdout.take() {
      let handle = app.clone();
      std::thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines().flatten() {
          let _ = handle.emit_all(STDOUT_EVENT, line);
        }
      });
    }

    if let Some(stderr) = child.stderr.take() {
      let handle = app.clone();
      std::thread::spawn(move || {
        let reader = BufReader::new(stderr);
        for line in reader.lines().flatten() {
          let _ = handle.emit_all(STDERR_EVENT, line);
        }
      });
    }

    let mut guard = self.process.lock().expect("获取后端进程锁失败");
    *guard = Some(child);
    drop(guard);

    self.spawn_monitor(app);
    Ok(())
  }

  pub fn stop(&self) -> Result<(), String> {
    self.manual_stop.store(true, Ordering::SeqCst);
    let mut guard = self.process.lock().expect("获取后端进程锁失败");
    if let Some(child) = guard.as_mut() {
      child
        .kill()
        .map_err(|err| format!("结束后端失败: {err}"))?;
      let _ = child.wait();
      *guard = None;
    }
    Ok(())
  }

  pub fn is_running(&self) -> bool {
    let mut guard = self.process.lock().expect("获取后端进程锁失败");
    if let Some(child) = guard.as_mut() {
      if let Ok(Some(_status)) = child.try_wait() {
        *guard = None;
        return false;
      }
      return true;
    }
    false
  }
}

impl Default for BackendManager {
  fn default() -> Self {
    BackendManager::new()
  }
}

#[derive(Serialize)]
pub struct BackendStatus {
  running: bool,
  backend_dir: String,
}

#[derive(Serialize)]
pub struct BackendStartedEvent {
  backend_dir: String,
}

#[derive(Serialize)]
pub struct BackendStoppedEvent {
  reason: String,
}

#[tauri::command]
pub fn start_backend(app: AppHandle, reload: Option<bool>) -> Result<(), String> {
  let state = app.state::<BackendManager>();
  state.spawn(&app, reload.unwrap_or(false))?;
  let _ = app.emit_all(
    STARTED_EVENT,
    BackendStartedEvent {
      backend_dir: state.backend_dir_string(),
    },
  );
  Ok(())
}

#[tauri::command]
pub fn stop_backend(app: AppHandle) -> Result<(), String> {
  let state = app.state::<BackendManager>();
  state.stop()?;
  let _ = app.emit_all(
    STOPPED_EVENT,
    BackendStoppedEvent {
      reason: "manual".to_string(),
    },
  );
  Ok(())
}

#[tauri::command]
pub fn backend_status(app: AppHandle) -> Result<BackendStatus, String> {
  let state = app.state::<BackendManager>();
  let running = state.is_running();
  Ok(BackendStatus {
    running,
    backend_dir: state.backend_dir_string(),
  })
}
