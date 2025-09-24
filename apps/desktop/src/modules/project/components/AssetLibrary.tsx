"use client";

/* eslint-disable @next/next/no-img-element */

import { useMemo } from "react";

import { useProjectStore } from "../state";

function isImageResource(uri: string): boolean {
  return uri.startsWith("data:image") || uri.startsWith("http") || uri.endsWith(".png");
}

export function AssetLibrary() {
  const assets = useProjectStore((state) => state.currentProject?.assets ?? []);

  const list = useMemo(() => assets.sort((a, b) => b.updatedAt - a.updatedAt), [assets]);

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">素材库</h3>
        <span className="text-xs text-slate-400">{list.length} 项</span>
      </header>
      <div className="mt-3 grid gap-3">
        {list.length === 0 ? (
          <p className="rounded-md border border-dashed border-slate-300 p-3 text-xs text-slate-400">
            生成成功的图片、提示词等素材会显示在此处，可随时拖拽回画布。
          </p>
        ) : null}
        {list.map((asset) => {
          const promptValue = asset.metadata?.prompt;
          const promptText =
            typeof promptValue === "string" && promptValue.trim().length > 0 ? promptValue : "未命名素材";

          return (
            <article key={asset.id} className="flex gap-3 rounded-md border border-slate-100 bg-slate-50 p-3">
              <div className="h-16 w-16 flex-shrink-0 overflow-hidden rounded-md border border-slate-200 bg-white">
                {isImageResource(asset.uri) ? (
                  <img src={asset.uri} alt={promptText} className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-[10px] text-slate-400">
                    无预览
                  </div>
                )}
              </div>
              <div className="flex-1 text-xs text-slate-600">
                <div className="font-medium text-slate-700">{promptText}</div>
                <div className="mt-1 text-[10px] text-slate-400">
                  {new Date(asset.updatedAt).toLocaleString()} · {asset.kind}
                </div>
                <div className="mt-1 truncate text-[10px] text-slate-400">{asset.uri}</div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
