"use client";

import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

export type BackendLogListener = (payload: string) => void;
export type BackendStartedPayload = { backendDir?: string };
export type BackendStoppedPayload = { reason?: string };
export type BackendLifecycleListener<TPayload> = (payload: TPayload) => void;

const STDOUT_EVENT = "backend://stdout";
const STDERR_EVENT = "backend://stderr";
const STARTED_EVENT = "backend://started";
const STOPPED_EVENT = "backend://stopped";

export function isTauriEnvironment(): boolean {
  return typeof window !== "undefined" && Boolean((window as any).__TAURI__);
}

function ensureTauri() {
  if (!isTauriEnvironment()) {
    throw new Error("当前环境未集成 Tauri");
  }
}

export async function startBackend(reload = false): Promise<void> {
  ensureTauri();
  await invoke("start_backend", { reload });
}

export async function stopBackend(): Promise<void> {
  ensureTauri();
  await invoke("stop_backend");
}

export async function backendStatus(): Promise<{ running: boolean; backendDir: string }> {
  ensureTauri();
  return invoke("backend_status");
}

export async function onBackendStdout(callback: BackendLogListener) {
  ensureTauri();
  return listen<string>(STDOUT_EVENT, (event) => callback(event.payload));
}

export async function onBackendStderr(callback: BackendLogListener) {
  ensureTauri();
  return listen<string>(STDERR_EVENT, (event) => callback(event.payload));
}

export async function onBackendStarted(
  callback: BackendLifecycleListener<BackendStartedPayload>
) {
  ensureTauri();
  return listen<BackendStartedPayload>(STARTED_EVENT, (event) => callback(event.payload ?? {}));
}

export async function onBackendStopped(
  callback: BackendLifecycleListener<BackendStoppedPayload>
) {
  ensureTauri();
  return listen<BackendStoppedPayload>(STOPPED_EVENT, (event) => callback(event.payload ?? {}));
}
