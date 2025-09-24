import { useEffect, useRef } from "react";

import { fetchTask } from "./api";
import { useProjectStore } from "./state";

const TERMINAL_STATUSES = new Set(["succeeded", "failed", "cancelled"]);

export function useTaskPolling(pollInterval = 2000) {
  const { tasks, refreshTask } = useProjectStore((state) => ({
    tasks: state.tasks,
    refreshTask: state.refreshTask,
  }));
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    const pendingIds = Object.values(tasks)
      .filter((task) => !TERMINAL_STATUSES.has(task.status))
      .map((task) => task.taskId);

    if (pendingIds.length === 0) {
      return () => {
        isMountedRef.current = false;
      };
    }

    const timer = setInterval(async () => {
      for (const taskId of pendingIds) {
        try {
          const task = await fetchTask(taskId);
          if (isMountedRef.current) {
            refreshTask(task);
          }
        } catch (err) {
          console.warn("轮询任务失败", err);
        }
      }
    }, pollInterval);

    return () => {
      isMountedRef.current = false;
      clearInterval(timer);
    };
  }, [tasks, pollInterval, refreshTask]);
}
