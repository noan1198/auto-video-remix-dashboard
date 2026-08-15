import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "爆款素材工作台",
  description: "从对标视频、自有素材匹配到可审核成片的本地视频生产工作台。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
