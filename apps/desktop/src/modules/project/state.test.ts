import { beforeEach, describe, expect, it, vi } from "vitest";

import { useProjectStore } from "./state";
import type { GenerationTask, ProjectPayload } from "./types";

vi.mock("./api", async () => {
  const actual = await vi.importActual<{ toAssetFromTask: any; toHistoryRecord: any }>("./api");
  return {
    createGenerationTask: vi.fn().mockResolvedValue(mockTask()),
    createProject: vi.fn().mockResolvedValue(mockProjectPayload()),
    listProjects: vi.fn().mockResolvedValue([]),
    loadProject: vi.fn().mockResolvedValue(mockProjectPayload()),
    saveProject: vi.fn().mockImplementation(async (payload: ProjectPayload) => payload),
    toAssetFromTask: actual.toAssetFromTask,
    toHistoryRecord: actual.toHistoryRecord,
  };
});

function mockTask(status: GenerationTask["status"] = "queued"): GenerationTask {
  const now = Date.now();
  return {
    taskId: `task-${now}`,
    prompt: "测试",
    status,
    metadata: {},
    resultUris: status === "succeeded" ? ["data:image/png;base64,AAA"] : [],
    createdAt: now,
    updatedAt: now,
  };
}

function mockProjectPayload(): ProjectPayload {
  const now = Date.now();
  return {
    manifest: {
      id: "project-1",
      name: "项目一号",
      createdAt: now,
      updatedAt: now,
      version: "1.0.0",
      canvasChecksum: "0",
    },
    canvas: null,
    assets: [],
    history: [],
  };
}

beforeEach(() => {
  const initialState = useProjectStore.getState();
  useProjectStore.setState({
    projects: [],
    currentProject: mockProjectPayload(),
    tasks: {},
    isLoading: false,
    error: null,
    lastSavedChecksum: "0",
    initialize: initialState.initialize,
    selectProject: initialState.selectProject,
    createNewProject: initialState.createNewProject,
    updateCanvas: initialState.updateCanvas,
    persist: initialState.persist,
    dispatchTask: initialState.dispatchTask,
    refreshTask: initialState.refreshTask,
  });
});

describe("project store", () => {
  it("updates canvas snapshot并打脏标记", () => {
    const snapshot = { document: { schema: "test" } } as any;
    useProjectStore.getState().updateCanvas(snapshot);
    const state = useProjectStore.getState();
    expect(state.currentProject?.canvas).toEqual(snapshot);
    expect(state.currentProject?.manifest.canvasChecksum.startsWith("front-")).toBe(true);
  });

  it("合并任务结果到历史与素材", () => {
    const succeeded = mockTask("succeeded");
    useProjectStore.getState().refreshTask(succeeded);
    const state = useProjectStore.getState();
    expect(state.currentProject?.history[0]?.id).toBe(succeeded.taskId);
    expect(state.currentProject?.assets[0]?.id).toBe(`${succeeded.taskId}-asset`);
  });

  it("自动保存时更新最后同步校验值", async () => {
    const store = useProjectStore.getState();
    store.updateCanvas({} as any);
    await store.persist();
    expect(useProjectStore.getState().lastSavedChecksum).toBe(
      useProjectStore.getState().currentProject?.manifest.canvasChecksum
    );
  });
});
