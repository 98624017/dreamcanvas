import { invoke } from "@tauri-apps/api/core";

import { isTauriEnvironment } from "@/modules/system/backendClient";

import type {
  AssetPayload,
  GenerationRecord,
  GenerationTask,
  ProjectManifest,
  ProjectPayload,
  ProjectSummary,
} from "./types";

const API_BASE_URL = "http://127.0.0.1:18500";
const STORAGE_KEY = "dreamcanvas.projects";

export interface CreateTaskPayload {
  prompt: string;
  model?: string;
  size?: string;
  batch?: number;
  projectId?: string;
}

async function fetchJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    ...(init ?? {}),
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`请求失败：${response.status} ${detail}`);
  }
  return response.json() as Promise<T>;
}

class BrowserProjectBridge {
  private readStore(): ProjectPayload[] {
    if (typeof window === "undefined") return [];
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      return JSON.parse(raw) as ProjectPayload[];
    } catch {
      return [];
    }
  }

  private writeStore(payloads: ProjectPayload[]) {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payloads));
  }

  async listProjects(): Promise<ProjectSummary[]> {
    const payloads = this.readStore();
    return payloads.map((payload) => ({
      manifest: payload.manifest,
      assets: payload.assets.length,
      history: payload.history.length,
    }));
  }

  async loadProject(projectId: string): Promise<ProjectPayload> {
    const payloads = this.readStore();
    const found = payloads.find((item) => item.manifest.id === projectId);
    if (!found) {
      throw new Error(`未找到项目 ${projectId}`);
    }
    return found;
  }

  async saveProject(payload: ProjectPayload): Promise<ProjectPayload> {
    const payloads = this.readStore();
    const index = payloads.findIndex((item) => item.manifest.id === payload.manifest.id);
    if (index >= 0) {
      payloads[index] = payload;
    } else {
      payloads.push(payload);
    }
    this.writeStore(payloads);
    return payload;
  }

  async createProject(name: string): Promise<ProjectPayload> {
    const now = Date.now();
    const id = typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `project-${now}`;
    const manifest: ProjectManifest = {
      id,
      name,
      createdAt: now,
      updatedAt: now,
      version: "1.0.0",
      canvasChecksum: "",
    };
    const payload: ProjectPayload = {
      manifest,
      canvas: null,
      assets: [],
      history: [],
    };
    return this.saveProject(payload);
  }
}

class TauriProjectBridge {
  async listProjects(): Promise<ProjectSummary[]> {
    return invoke<ProjectSummary[]>("list_projects");
  }

  async loadProject(projectId: string): Promise<ProjectPayload> {
    return invoke<ProjectPayload>("load_project", { projectId });
  }

  async saveProject(payload: ProjectPayload): Promise<ProjectPayload> {
    return invoke<ProjectPayload>("save_project", { payload });
  }

  async createProject(name: string): Promise<ProjectPayload> {
    return invoke<ProjectPayload>("create_project", { name });
  }
}

const projectBridge = isTauriEnvironment() ? new TauriProjectBridge() : new BrowserProjectBridge();

export function listProjects(): Promise<ProjectSummary[]> {
  return projectBridge.listProjects();
}

export function loadProject(projectId: string): Promise<ProjectPayload> {
  return projectBridge.loadProject(projectId);
}

export function saveProject(payload: ProjectPayload): Promise<ProjectPayload> {
  return projectBridge.saveProject(payload);
}

export function createProject(name: string): Promise<ProjectPayload> {
  return projectBridge.createProject(name);
}

export async function createGenerationTask(payload: CreateTaskPayload): Promise<GenerationTask> {
  const response = await fetchJson<{ task: GenerationTask }>(`${API_BASE_URL}/jimeng/tasks`, {
    method: "POST",
    body: JSON.stringify({
      prompt: payload.prompt,
      model: payload.model ?? "sdxl",
      size: payload.size ?? "1024x1024",
      batch: payload.batch ?? 1,
      projectId: payload.projectId,
    }),
  });
  return response.task;
}

export async function fetchTask(taskId: string): Promise<GenerationTask> {
  const response = await fetchJson<{ task: GenerationTask }>(
    `${API_BASE_URL}/jimeng/history?taskId=${encodeURIComponent(taskId)}`
  );
  return response.task;
}

export async function cancelTask(taskId: string): Promise<GenerationTask> {
  const response = await fetchJson<{ task: GenerationTask }>(
    `${API_BASE_URL}/jimeng/tasks/${taskId}/cancel`,
    {
      method: "POST",
    }
  );
  return response.task;
}

export function toAssetFromTask(
  projectId: string,
  task: GenerationTask
): AssetPayload | undefined {
  if (task.status !== "succeeded" || task.resultUris.length === 0) {
    return undefined;
  }
  const now = Date.now();
  const [first] = task.resultUris;
  return {
    id: `${task.taskId}-asset`,
    projectId,
    kind: "image",
    uri: first,
    metadata: {
      prompt: task.prompt,
      source: "jimeng",
      generatedAt: now,
    },
    createdAt: now,
    updatedAt: now,
  };
}

export function toHistoryRecord(task: GenerationTask): GenerationRecord {
  return {
    id: task.taskId,
    prompt: task.prompt,
    sessionId: "local",
    status: task.status,
    resultUris: task.resultUris,
    error: task.errorMessage,
    createdAt: task.createdAt,
    completedAt: task.status === "succeeded" || task.status === "failed" ? task.updatedAt : undefined,
  };
}
