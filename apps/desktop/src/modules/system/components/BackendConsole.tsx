"use client";

import React, { useEffect, useMemo, useState } from "react";

import {
  isTauriEnvironment,
  onBackendStdout,
  onBackendStderr
} from "@/modules/system/backendClient";

const MAX_LINES = 200;

type ConsoleLine = {
  type: "stdout" | "stderr";
  text: string;
};

function trimLines(list: ConsoleLine[]): ConsoleLine[] {
  if (list.length <= MAX_LINES) return list;
  return list.slice(list.length - MAX_LINES);
}

export function BackendConsole() {
  const [lines, setLines] = useState<ConsoleLine[]>([]);
  const [enabled, setEnabled] = useState<boolean>(false);

  useEffect(() => {
    if (!isTauriEnvironment()) {
      setEnabled(false);
      return;
    }

    setEnabled(true);
    let disposeStdout: (() => void) | null = null;
    let disposeStderr: (() => void) | null = null;

    onBackendStdout((payload) => {
      setLines((prev) =>
        trimLines([
          ...prev,
          {
            type: "stdout",
            text: payload
          }
        ])
      );
    }).then((unlisten) => {
      disposeStdout = unlisten;
    });

    onBackendStderr((payload) => {
      setLines((prev) =>
        trimLines([
          ...prev,
          {
            type: "stderr",
            text: payload
          }
        ])
      );
    }).then((unlisten) => {
      disposeStderr = unlisten;
    });

    return () => {
      if (disposeStdout) {
        disposeStdout();
      }
      if (disposeStderr) {
        disposeStderr();
      }
    };
  }, []);

  const formattedLines = useMemo(() => lines, [lines]);
  const hasLogs = formattedLines.length > 0;

  if (!enabled) {
    return (
      <div className="mt-4 rounded-md bg-slate-950/40 p-4 text-xs text-slate-400">
        桌面模式下将显示后端实时日志。当前环境未启用 Tauri。
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-md bg-slate-950/70 p-4 text-xs text-slate-200">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-medium text-slate-100">后端实时日志</span>
        <span className="text-[10px] text-slate-500">最新 {formattedLines.length} 行</span>
      </div>
      <pre className="max-h-52 overflow-y-auto whitespace-pre-wrap break-words">
        {hasLogs ? (
          formattedLines.map((line, index) => (
            <span
              key={`${line.type}-${index}`}
              className={line.type === "stderr" ? "text-red-300" : "text-slate-200"}
            >
              {line.type === "stderr" ? "[ERR]" : "[OUT]"} {line.text}
              {"\n"}
            </span>
          ))
        ) : (
          <span className="text-slate-500">暂无日志输出，等待后端运行...</span>
        )}
      </pre>
    </div>
  );
}
