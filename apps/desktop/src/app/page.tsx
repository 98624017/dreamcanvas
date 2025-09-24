"use client";

import { useEffect, useRef } from "react";

import { BackendConsole } from "@/modules/system/components/BackendConsole";
import { useBackendHealth } from "@/modules/system/useBackendHealth";
import { AssetLibrary } from "@/modules/project/components/AssetLibrary";
import { CanvasBoard } from "@/modules/project/components/CanvasBoard";
import { ProjectSidebar } from "@/modules/project/components/ProjectSidebar";
import { PromptComposer } from "@/modules/project/components/PromptComposer";
import { TaskPanel } from "@/modules/project/components/TaskPanel";
import { useTaskPolling } from "@/modules/project/hooks";
import { useProjectStore } from "@/modules/project/state";

export default function HomePage() {
  const { status } = useBackendHealth();
  const initialize = useProjectStore((state) => state.initialize);
  const isLoading = useProjectStore((state) => state.isLoading);
  const error = useProjectStore((state) => state.error);
  const currentProject = useProjectStore((state) => state.currentProject);
  const persist = useProjectStore((state) => state.persist);
  const lastSavedChecksum = useProjectStore((state) => state.lastSavedChecksum);

  useEffect(() => {
    initialize();
  }, [initialize]);

  useTaskPolling();

  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const canvasChecksum = currentProject?.manifest.canvasChecksum ?? null;
  const assetCount = currentProject?.assets.length ?? 0;
  const historyCount = currentProject?.history.length ?? 0;

  useEffect(() => {
    if (!currentProject) return;
    if (canvasChecksum === lastSavedChecksum) return;

    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
    }
    saveTimerRef.current = setTimeout(() => {
      persist().catch((err) => console.warn("自动保存失败", err));
    }, 2000);

    return () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
    };
  }, [canvasChecksum, assetCount, historyCount, persist, currentProject, lastSavedChecksum]);

  return (
    <main className="flex min-h-screen bg-slate-100">
      <ProjectSidebar />
      <section className="flex min-h-screen flex-1 flex-col gap-4 overflow-hidden p-6">
        <header className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-500">阶段 P1 · MVP Alpha</p>
              <h1 className="text-2xl font-semibold text-slate-900">
                {currentProject ? currentProject.manifest.name : "DreamCanvas 桌面端"}
              </h1>
            </div>
            <div className="text-right text-xs text-slate-500">
              <p>后端状态：{status ? `在线（${status.phase} - v${status.version}）` : "检测中"}</p>
              {currentProject ? (
                <p>
                  自动保存：
                  {canvasChecksum === lastSavedChecksum ? (
                    <span className="text-emerald-500"> 已同步</span>
                  ) : (
                    <span className="text-orange-500"> 待保存</span>
                  )}
                </p>
              ) : null}
            </div>
          </div>
          {error ? (
            <p className="rounded-md bg-red-100 px-3 py-2 text-xs text-red-600">{error}</p>
          ) : null}
        </header>

        <div className="grid flex-1 grid-cols-[minmax(0,1fr)_320px] gap-4 overflow-hidden">
          <div className="flex h-full flex-col gap-4 overflow-hidden">
            {isLoading && !currentProject ? (
              <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-slate-300 text-sm text-slate-400">
                项目加载中...
              </div>
            ) : (
              <CanvasBoard />
            )}
          </div>
          <div className="flex h-full flex-col gap-4 overflow-y-auto pb-6">
            <PromptComposer />
            <TaskPanel />
            <AssetLibrary />
          </div>
        </div>

        <BackendConsole />
      </section>
    </main>
  );
}
