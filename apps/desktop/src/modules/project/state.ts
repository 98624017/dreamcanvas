import { create } from "zustand";

import {
  createGenerationTask,
  createProject,
  listProjects,
  loadProject,
  saveProject,
  toAssetFromTask,
  toHistoryRecord,
  type CreateTaskPayload,
} from "./api";
import type {
  CanvasSnapshot,
  GenerationTask,
  ProjectPayload,
  ProjectSummary,
} from "./types";

function computeSnapshotChecksum(snapshot: CanvasSnapshot): string {
  const json = snapshot ? JSON.stringify(snapshot) : "{}";
  let hash = 0;
  for (let index = 0; index < json.length; index += 1) {
    const char = json.charCodeAt(index);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }
  return `front-${Math.abs(hash)}`;
}

interface ProjectStoreState {
  projects: ProjectSummary[];
  currentProject: ProjectPayload | null;
  tasks: Record<string, GenerationTask>;
  isLoading: boolean;
  error: string | null;
  lastSavedChecksum: string | null;
  initialize(): Promise<void>;
  selectProject(projectId: string): Promise<void>;
  createNewProject(name: string): Promise<void>;
  updateCanvas(snapshot: CanvasSnapshot): void;
  persist(): Promise<void>;
  dispatchTask(payload: CreateTaskPayload): Promise<GenerationTask>;
  refreshTask(task: GenerationTask): void;
}

export const useProjectStore = create<ProjectStoreState>((set, get) => ({
  projects: [],
  currentProject: null,
  tasks: {},
  isLoading: false,
  error: null,
  lastSavedChecksum: null,
  async initialize() {
    set({ isLoading: true, error: null });
    try {
      const projects = await listProjects();
      set({ projects });
      if (projects.length > 0) {
        await get().selectProject(projects[0].manifest.id);
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    } finally {
      set({ isLoading: false });
    }
  },
  async selectProject(projectId: string) {
    set({ isLoading: true, error: null });
    try {
      const payload = await loadProject(projectId);
      set({ currentProject: payload, lastSavedChecksum: payload.manifest.canvasChecksum });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    } finally {
      set({ isLoading: false });
    }
  },
  async createNewProject(name: string) {
    set({ isLoading: true, error: null });
    try {
      const payload = await createProject(name);
      const projects = await listProjects();
      set({
        currentProject: payload,
        projects,
        lastSavedChecksum: payload.manifest.canvasChecksum,
      });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    } finally {
      set({ isLoading: false });
    }
  },
  updateCanvas(snapshot: CanvasSnapshot) {
    const state = get();
    if (!state.currentProject) return;
    const current = state.currentProject;
    const checksum = computeSnapshotChecksum(snapshot);
    set({
      currentProject: {
        ...current,
        canvas: snapshot ?? {},
        manifest: {
          ...current.manifest,
          updatedAt: Date.now(),
          canvasChecksum: checksum,
        },
      },
    });
  },
  async persist() {
    const state = get();
    if (!state.currentProject) return;
    try {
      const persisted = await saveProject(state.currentProject);
      const exists = state.projects.some((summary) => summary.manifest.id === persisted.manifest.id);
      const nextProjects = exists
        ? state.projects.map((summary) =>
            summary.manifest.id === persisted.manifest.id
              ? {
                  ...summary,
                  manifest: persisted.manifest,
                  assets: persisted.assets.length,
                  history: persisted.history.length,
                }
              : summary
          )
        : [
            {
              manifest: persisted.manifest,
              assets: persisted.assets.length,
              history: persisted.history.length,
            },
            ...state.projects,
          ];
      set({ currentProject: persisted, projects: nextProjects, lastSavedChecksum: persisted.manifest.canvasChecksum });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },
  async dispatchTask(payload: CreateTaskPayload) {
    const task = await createGenerationTask(payload);
    set((state) => ({
      tasks: {
        ...state.tasks,
        [task.taskId]: task,
      },
    }));
    return task;
  },
  refreshTask(task: GenerationTask) {
    const state = get();
    const project = state.currentProject;
    if (!project) return;
    const history = [...project.history];
    const existingIndex = history.findIndex((item) => item.id === task.taskId);
    const record = toHistoryRecord(task);
    if (existingIndex >= 0) {
      history[existingIndex] = record;
    } else {
      history.unshift(record);
    }

    const maybeAsset = toAssetFromTask(project.manifest.id, task);
    let nextAssets = project.assets;
    if (maybeAsset) {
      const exists = nextAssets.some((asset) => asset.id === maybeAsset.id);
      if (!exists) {
        nextAssets = [maybeAsset, ...project.assets];
      }
    }

    set({
      currentProject: {
        ...project,
        assets: nextAssets,
        history,
        manifest: {
          ...project.manifest,
          updatedAt: Date.now(),
        },
      },
      tasks: {
        ...state.tasks,
        [task.taskId]: task,
      },
    });
  },
}));
