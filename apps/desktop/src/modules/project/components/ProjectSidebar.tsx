"use client";

import { useState } from "react";

import { useProjectStore } from "../state";

export function ProjectSidebar() {
  const { projects, currentProject, selectProject, createNewProject, isLoading } = useProjectStore(
    (state) => ({
      projects: state.projects,
      currentProject: state.currentProject,
      selectProject: state.selectProject,
      createNewProject: state.createNewProject,
      isLoading: state.isLoading,
    })
  );
  const [projectName, setProjectName] = useState("");

  const handleCreate = async () => {
    if (!projectName.trim()) return;
    await createNewProject(projectName.trim());
    setProjectName("");
  };

  return (
    <aside className="flex h-full w-64 flex-shrink-0 flex-col gap-4 border-r border-slate-200 bg-slate-50 p-4">
      <div>
        <h2 className="text-sm font-semibold text-slate-600">项目列表</h2>
        <p className="text-xs text-slate-400">选择或创建项目以开始创作</p>
      </div>

      <div className="space-y-2">
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm focus:border-slate-500 focus:outline-none"
            placeholder="新项目名称"
            value={projectName}
            onChange={(event) => setProjectName(event.target.value)}
          />
          <button
            type="button"
            className="rounded-md bg-slate-900 px-3 py-1 text-sm font-medium text-white disabled:bg-slate-400"
            onClick={handleCreate}
            disabled={isLoading || !projectName.trim()}
          >
            新建
          </button>
        </div>
        <ul className="space-y-1 overflow-y-auto pr-1">
          {projects.map((item) => {
            const active = currentProject?.manifest.id === item.manifest.id;
            return (
              <li key={item.manifest.id}>
                <button
                  type="button"
                  onClick={() => selectProject(item.manifest.id)}
                  className={`w-full rounded-md px-2 py-1 text-left text-sm ${
                    active
                      ? "bg-slate-900 text-white"
                      : "bg-white text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <div className="font-medium">{item.manifest.name}</div>
                  <div className="text-[10px] text-slate-400">
                    资产 {item.assets} · 任务 {item.history}
                  </div>
                </button>
              </li>
            );
          })}
          {projects.length === 0 ? (
            <li className="rounded-md border border-dashed border-slate-300 p-2 text-xs text-slate-400">
              暂无项目，请创建首个项目。
            </li>
          ) : null}
        </ul>
      </div>
    </aside>
  );
}
