"use client";

import { useEffect, useMemo, useRef, useState } from "react";

export type BackendStatus = {
  phase: string;
  version: string;
  status: string;
};

export type BackendHealthState = {
  status: BackendStatus | null;
  lastChecked: Date | null;
  error: string | null;
};

const DEFAULT_STATE: BackendHealthState = {
  status: null,
  lastChecked: null,
  error: null
};

/**
 * 轮询 FastAPI 健康状态，供前端展示与后续故障自检使用。
 */
export function useBackendHealth(pollingMs = 5000): BackendHealthState {
  const [state, setState] = useState<BackendHealthState>(DEFAULT_STATE);
  const timerRef = useRef<number | null>(null);

  const endpoint = useMemo(() => "http://127.0.0.1:18500/healthz", []);

  useEffect(() => {
    let disposed = false;

    async function probe() {
      try {
        const response = await fetch(endpoint, {
          method: "GET",
          cache: "no-store"
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const payload = (await response.json()) as BackendStatus;
        if (disposed) return;
        setState({
          status: payload,
          lastChecked: new Date(),
          error: null
        });
      } catch (error) {
        if (disposed) return;
        setState({
          status: null,
          lastChecked: new Date(),
          error: error instanceof Error ? error.message : "无法连接"
        });
      }
    }

    probe();
    timerRef.current = window.setInterval(probe, pollingMs);

    return () => {
      disposed = true;
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
    };
  }, [endpoint, pollingMs]);

  return state;
}
