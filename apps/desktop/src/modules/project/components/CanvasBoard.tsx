"use client";

import { useEffect, useRef } from "react";
import { Editor, Tldraw } from "tldraw";

import type { CanvasSnapshot } from "../types";
import { useProjectStore } from "../state";

export function CanvasBoard() {
  const editorRef = useRef<Editor | null>(null);
  const loadedProjectId = useRef<string | null>(null);
  const pristineSnapshotRef = useRef<CanvasSnapshot | null>(null);
  const { currentProject, updateCanvas } = useProjectStore((state) => ({
    currentProject: state.currentProject,
    updateCanvas: state.updateCanvas,
  }));

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    if (!pristineSnapshotRef.current) {
      pristineSnapshotRef.current = editor.store.getSnapshot() as CanvasSnapshot;
    }
  }, []);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor || !currentProject) return;
    if (loadedProjectId.current === currentProject.manifest.id) return;

    const snapshot = currentProject.canvas as CanvasSnapshot;
    if (snapshot && Object.keys(snapshot).length > 0) {
      try {
        editor.store.loadSnapshot(snapshot as any);
      } catch (error) {
        console.warn("加载画布快照失败，使用初始状态", error);
        if (pristineSnapshotRef.current) {
          editor.store.loadSnapshot(pristineSnapshotRef.current as any);
        }
      }
    } else if (pristineSnapshotRef.current) {
      editor.store.loadSnapshot(pristineSnapshotRef.current as any);
    }

    loadedProjectId.current = currentProject.manifest.id;
  }, [currentProject]);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    let frame: number | null = null;

    const cleanup = editor.store.listen(
      () => {
        if (frame) return;
        frame = requestAnimationFrame(() => {
          frame = null;
          const snapshot = editor.store.getSnapshot() as CanvasSnapshot;
          updateCanvas(snapshot);
        });
      },
      { source: "user", scope: "document" }
    );

    return () => {
      if (frame) cancelAnimationFrame(frame);
      cleanup();
    };
  }, [updateCanvas]);

  return (
    <div className="h-full rounded-lg border border-slate-200 bg-white shadow-sm">
      <Tldraw
        className="h-full"
        onMount={(editor) => {
          editorRef.current = editor;
          if (!pristineSnapshotRef.current) {
            pristineSnapshotRef.current = editor.store.getSnapshot() as CanvasSnapshot;
          }
          if (currentProject?.canvas) {
            editor.store.loadSnapshot(currentProject.canvas as any);
            loadedProjectId.current = currentProject.manifest.id;
          }
        }}
      />
    </div>
  );
}
