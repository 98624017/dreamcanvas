"use client";

import { FormEvent, useState } from "react";

import { useProjectStore } from "../state";

const MODELS = [
  { value: "sdxl", label: "SDXL" },
  { value: "turbo", label: "Turbo" },
  { value: "anime", label: "Anime" },
];

export function PromptComposer() {
  const { currentProject, dispatchTask } = useProjectStore((state) => ({
    currentProject: state.currentProject,
    dispatchTask: state.dispatchTask,
  }));
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("sdxl");
  const [isSubmitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  if (!currentProject) {
    return (
      <div className="rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-400">
        请选择一个项目以提交生成任务。
      </div>
    );
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!prompt.trim()) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const task = await dispatchTask({ prompt: prompt.trim(), model, projectId: currentProject.manifest.id });
      setPrompt("");
      setMessage(`任务已提交：${task.taskId}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "提交任务失败，请稍后再试。");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-md border border-slate-200 bg-white p-4 shadow-sm">
      <div>
        <label className="text-sm font-medium text-slate-700">生成提示词</label>
        <textarea
          className="mt-1 h-24 w-full resize-none rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          placeholder="描述你想要的画面、风格、灯光..."
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
        />
      </div>
      <div className="flex gap-3 text-sm">
        <label className="flex items-center gap-2">
          <span className="text-slate-500">模型</span>
          <select
            className="rounded-md border border-slate-300 px-2 py-1 focus:border-slate-500 focus:outline-none"
            value={model}
            onChange={(event) => setModel(event.target.value)}
          >
            {MODELS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <div className="flex-1 text-right text-xs text-slate-400">
          支持自动重试 1015/1016/1003 错误。
        </div>
      </div>
      <div className="flex items-center justify-between">
        <button
          type="submit"
          className="rounded-md bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white disabled:bg-emerald-300"
          disabled={isSubmitting || !prompt.trim()}
        >
          {isSubmitting ? "提交中..." : "提交生成"}
        </button>
        {message ? <p className="text-xs text-slate-500">{message}</p> : null}
      </div>
    </form>
  );
}
