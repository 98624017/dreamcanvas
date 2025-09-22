import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "DreamCanvas 桌面端",
  description: "AI 创作项目工作台"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
