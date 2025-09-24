import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/modules/system/useBackendHealth", () => ({
  useBackendHealth: () => ({
    status: { status: "ok", phase: "P1", version: "0.2.0" },
    lastChecked: new Date("2025-01-01T00:00:00Z"),
    error: null,
  }),
}));

const { initialize, persist } = vi.hoisted(() => ({
  initialize: vi.fn(),
  persist: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/modules/project/state", () => {
  const state = {
    projects: [],
    currentProject: {
      manifest: {
        id: "project-1",
        name: "测试项目",
        createdAt: Date.now(),
        updatedAt: Date.now(),
        version: "1.0.0",
        canvasChecksum: "front-1",
      },
      canvas: null,
      assets: [],
      history: [],
    },
    tasks: {},
    isLoading: false,
    error: null,
    lastSavedChecksum: "front-1",
    initialize,
    selectProject: vi.fn(),
    createNewProject: vi.fn(),
    updateCanvas: vi.fn(),
    persist,
    dispatchTask: vi.fn(),
    refreshTask: vi.fn(),
  };
  const hook = (selector: (state: typeof state) => unknown) => selector(state);
  Object.assign(hook, {
    getState: () => state,
    setState: vi.fn(),
  });
  return { useProjectStore: hook };
});

vi.mock("@/modules/project/components/ProjectSidebar", () => ({
  ProjectSidebar: () => <div data-testid="sidebar" />,
}));
vi.mock("@/modules/project/components/CanvasBoard", () => ({
  CanvasBoard: () => <div data-testid="canvas" />,
}));
vi.mock("@/modules/project/components/PromptComposer", () => ({
  PromptComposer: () => <div data-testid="prompt" />,
}));
vi.mock("@/modules/project/components/TaskPanel", () => ({
  TaskPanel: () => <div data-testid="tasks" />,
}));
vi.mock("@/modules/project/components/AssetLibrary", () => ({
  AssetLibrary: () => <div data-testid="assets" />,
}));
vi.mock("@/modules/project/hooks", () => ({
  useTaskPolling: () => undefined,
}));

import HomePage from "./page";

describe("HomePage", () => {
  it("显示 P1 阶段信息与自动保存状态", () => {
    render(<HomePage />);

    expect(initialize).toHaveBeenCalled();
    expect(screen.getByText("阶段 P1 · MVP Alpha")).toBeInTheDocument();
    expect(screen.getByText(/自动保存：/)).toHaveTextContent("已同步");
    expect(screen.getByText(/后端状态：在线/)).toBeInTheDocument();
    expect(screen.getByTestId("canvas")).toBeInTheDocument();
  });
});
