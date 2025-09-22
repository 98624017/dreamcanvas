export const isTauriEnvironment = () => false;
export const onBackendStdout = () => Promise.resolve(() => {});
export const onBackendStderr = () => Promise.resolve(() => {});
export const onBackendStarted = () => Promise.resolve(() => {});
export const onBackendStopped = () => Promise.resolve(() => {});
export const startBackend = async () => {
  throw new Error("Tauri 未启用");
};
export const stopBackend = async () => {
  throw new Error("Tauri 未启用");
};
export const backendStatus = async () => ({ running: false, backendDir: "" });
