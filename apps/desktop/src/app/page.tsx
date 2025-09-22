"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";

import { BackendConsole } from "@/modules/system/components/BackendConsole";
import { useBackendHealth } from "@/modules/system/useBackendHealth";
import {
  isTauriEnvironment,
  onBackendStarted,
  onBackendStopped,
  startBackend
} from "@/modules/system/backendClient";

type ActionTone = "info" | "success" | "error";

export default function HomePage() {
  const { status, error, lastChecked } = useBackendHealth();
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionTone, setActionTone] = useState<ActionTone>("info");

  const backendLabel = useMemo(() => {
    if (status) {
      return `在线（阶段 ${status.phase} · 版本 ${status.version}）`;
    }
    if (error) {
      return `离线（${error}）`;
    }
    return "检测中...";
  }, [status, error]);

  const lastCheckedLabel = lastChecked
    ? lastChecked.toLocaleTimeString()
    : "未检查";

  const canControlBackend = isTauriEnvironment();

  useEffect(() => {
    if (!isTauriEnvironment()) {
      return;
    }

    let stopUnlisten: (() => void) | undefined;
    let startUnlisten: (() => void) | undefined;

    onBackendStarted(() => {
      setActionTone("success");
      setActionMessage("FastAPI 后端已启动。实时日志面板可查看最新输出。");
    })
      .then((unlisten) => {
        startUnlisten = unlisten;
      })
      .catch(() => {
        /* noop */
      });

    onBackendStopped((payload) => {
      const reason = payload?.reason ?? "unknown";
      if (reason === "manual") {
        setActionTone("info");
        setActionMessage("后端已手动停止，可点击重新启动。");
      } else {
        setActionTone("error");
        setActionMessage(
          `后端异常退出（原因：${reason}），请重新启动或查看日志。`
        );
      }
    })
      .then((unlisten) => {
        stopUnlisten = unlisten;
      })
      .catch(() => {
        /* noop */
      });

    return () => {
      startUnlisten?.();
      stopUnlisten?.();
    };
  }, []);

  const handleStartBackend = useCallback(async () => {
    try {
      await startBackend(true);
      setActionTone("info");
      setActionMessage("已请求启动 FastAPI 后端，实时日志中可查看输出。");
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setActionTone("error");
      setActionMessage(`启动失败：${message}`);
    }
  }, []);

  const toneClass: Record<ActionTone, string> = {
    info: "text-slate-400",
    success: "text-emerald-400",
    error: "text-red-300"
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-8 px-6 py-16">
      <header className="space-y-2">
        <p className="text-sm text-slate-500">阶段 P0 · 环境基线</p>
        <h1 className="text-3xl font-semibold">DreamCanvas 桌面端工作台</h1>
        <p className="text-slate-600">
          初版界面验证 Next.js + Tauri + FastAPI 架构，后续将接入画布、素材库与 AI 工作流。
        </p>
      </header>

      <section className="grid gap-6 md:grid-cols-2">
        <section className="rounded-lg border border-dashed border-slate-300 p-6">
          <h2 className="text-lg font-medium">下一步</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-600">
            <li>运行 <code>pnpm tauri</code> 启动桌面壳并验证 Python 服务心跳。</li>
            <li>在 <code>src/modules/</code> 下扩展画布、素材库及提示词上下文面板。</li>
            <li>根据 <code>docs/product_requirements.md</code> 更新阶段验收用例。</li>
          </ul>
        </section>

        <section className="rounded-lg border border-slate-300 bg-slate-900/20 p-6 text-slate-100">
          <h2 className="text-lg font-medium">后端运行状态</h2>
          <p className="mt-3 text-sm text-slate-300">后端状态：{backendLabel}</p>
          <p className="mt-1 text-xs text-slate-500">最近检查：{lastCheckedLabel}</p>
          <div className="mt-4 space-y-2">
            <button
              type="button"
              onClick={handleStartBackend}
              disabled={!canControlBackend}
              className="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-900 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              {canControlBackend ? "重新启动后端" : "Tauri 环境未启用"}
            </button>
            {actionMessage ? (
              <p className={`text-xs ${toneClass[actionTone]}`}>{actionMessage}</p>
            ) : null}
          </div>
          <p className="mt-4 text-xs text-slate-400">
            如未在线，请执行 <code>scripts/start-backend.ps1</code> 并确认 18500 端口监听。
          </p>
          <BackendConsole />
        </section>
      </section>
    </main>
  );
}
