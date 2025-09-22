import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BackendConsole } from "./BackendConsole";

describe("BackendConsole", () => {
  it("非 Tauri 环境展示提示", () => {
    render(<BackendConsole />);
    expect(
      screen.getByText("桌面模式下将显示后端实时日志。当前环境未启用 Tauri。")
    ).toBeInTheDocument();
  });
});
