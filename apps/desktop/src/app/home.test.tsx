import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import HomePage from "./page";

describe("HomePage", () => {
  beforeEach(() => {
    Object.defineProperty(window, "__TAURI__", {
      value: undefined,
      writable: true,
      configurable: true
    });

    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok", phase: "P0", version: "0.1.0" })
    } as unknown as Response);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("渲染阶段提示与后端状态", async () => {
    render(<HomePage />);

    expect(screen.getByText("阶段 P0 · 环境基线")).toBeInTheDocument();
    await waitFor(async () => {
      expect(await screen.findByText(/后端状态：在线/)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Tauri 环境未启用" })).toBeDisabled();
    expect(
      screen.getByText("桌面模式下将显示后端实时日志。当前环境未启用 Tauri。")
    ).toBeInTheDocument();
  });
});
