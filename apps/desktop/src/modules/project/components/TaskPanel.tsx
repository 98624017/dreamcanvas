"use client";

import { useMemo, useState } from "react";

import { cancelTask, fetchTask } from "../api";
import { useProjectStore } from "../state";

const STATUS_TEXT: Record<string, string> = {
  queued: "排队中",
  running: "生成中",
  succeeded: "成功",
  failed: "失败",
  cancelled: "已取消",
};

export function TaskPanel() {
  const { tasks, refreshTask } = useProjectStore((state) => ({
    tasks: state.tasks,
    refreshTask: state.refreshTask,
  }));
  const [busyTask, setBusyTask] = useState<string | null>(null);

  const taskList = useMemo(() => {
    return Object.values(tasks).sort((a, b) => b.updatedAt - a.updatedAt);
  }, [tasks]);

  const handleRefresh = async (taskId: string) => {
    setBusyTask(taskId);
    try {
      const task = await fetchTask(taskId);
      refreshTask(task);
    } catch (err) {
      console.warn("刷新任务失败", err);
    } finally {
      setBusyTask(null);
    }
  };

  const handleCancel = async (taskId: string) => {
    setBusyTask(taskId);
    try {
      const task = await cancelTask(taskId);
      refreshTask(task);
    } catch (err) {
      console.warn("取消任务失败", err);
    } finally {
      setBusyTask(null);
    }
  };

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">任务面板</h3>
        <span className="text-xs text-slate-400">实时状态同步</span>
      </header>
      <ul className="mt-3 space-y-2 text-sm">
        {taskList.length === 0 ? (
          <li className="rounded-md border border-dashed border-slate-300 p-3 text-xs text-slate-400">
            暂无任务，可在左侧提交生成请求。
          </li>
        ) : null}
        {taskList.map((task) => {
          const status = STATUS_TEXT[task.status] ?? task.status;
          return (
            <li key={task.taskId} className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>{new Date(task.updatedAt).toLocaleTimeString()}</span>
                <span className="font-medium text-slate-600">{status}</span>
              </div>
              <p className="mt-1 text-sm text-slate-800">{task.prompt}</p>
              {task.errorMessage ? (
                <p className="mt-1 text-xs text-red-500">{task.errorMessage}</p>
              ) : null}
              <div className="mt-2 flex gap-2 text-xs">
                <button
                  type="button"
                  className="rounded bg-slate-900 px-2 py-1 text-white disabled:bg-slate-400"
                  onClick={() => handleRefresh(task.taskId)}
                  disabled={busyTask === task.taskId}
                >
                  刷新
                </button>
                {task.status === "queued" || task.status === "running" ? (
                  <button
                    type="button"
                    className="rounded border border-slate-400 px-2 py-1 text-slate-600 disabled:border-slate-200 disabled:text-slate-300"
                    onClick={() => handleCancel(task.taskId)}
                    disabled={busyTask === task.taskId}
                  >
                    取消
                  </button>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
