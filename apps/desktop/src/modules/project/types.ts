import type { TLStoreSnapshot } from "tldraw";

export type TaskStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface ProjectManifest {
  id: string;
  name: string;
  createdAt: number;
  updatedAt: number;
  version: string;
  canvasChecksum: string;
}

export type CanvasSnapshot = TLStoreSnapshot | null;

export type AssetKind = "image" | "text_prompt" | "generated_component";

export interface AssetMetadata {
  [key: string]: unknown;
}

export interface AssetPayload {
  id: string;
  projectId: string;
  kind: AssetKind;
  uri: string;
  metadata: AssetMetadata;
  createdAt: number;
  updatedAt: number;
}

export interface GenerationRecord {
  id: string;
  prompt: string;
  sessionId: string;
  status: TaskStatus;
  resultUris: string[];
  error?: string;
  createdAt: number;
  completedAt?: number;
}

export interface ProjectPayload {
  manifest: ProjectManifest;
  canvas: CanvasSnapshot | Record<string, unknown>;
  assets: AssetPayload[];
  history: GenerationRecord[];
}

export interface ProjectSummary {
  manifest: ProjectManifest;
  assets: number;
  history: number;
}

export interface GenerationTask {
  taskId: string;
  prompt: string;
  status: TaskStatus;
  metadata: Record<string, unknown>;
  resultUris: string[];
  errorCode?: string;
  errorMessage?: string;
  createdAt: number;
  updatedAt: number;
}
