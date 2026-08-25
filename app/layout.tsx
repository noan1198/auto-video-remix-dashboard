import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "爆款视频拆镜头",
  description: "把完整视频自动拆成带时间信息的分镜九宫格。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
