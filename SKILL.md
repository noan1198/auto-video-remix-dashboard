---
name: auto-video-remix-dashboard
description: Split a local product or benchmark video into independent shots, keyframes, timing data, and a local HTML composition-grid report. Use when the user gives a video and asks to split, dissect, study, imitate, or inspect its shots, or when they ask to open the optional local Auto Video Remix dashboard. Keep all media local.
---

# 爆款视频镜头分割

默认使用对话式镜头分割。用户提供一条视频后，生成“原视频名镜头分割”文件夹，其中包含独立镜头、关键帧、分镜表和带构图九宫格的本地网页。不要要求用户先建立完整视频项目，也不要把简单分割请求扩大为素材匹配、配音或自动成片。

## 对话式镜头分割

1. 确认用户指定的视频路径真实存在，格式为 MP4、MOV、M4V、WEBM 或 MKV。
2. 默认把输出文件夹放在源视频旁边。用户指定了保存位置或当前权限无法写入源目录时，改用用户指定位置或当前工作区。
3. 运行：

   ```bash
   python3 <skill-root>/scripts/split_video.py <absolute-video-path> --output-root <absolute-output-root>
   ```

4. 如果脚本报告缺少本地视频组件，告知用户首次使用需要准备本地 FFmpeg 组件，然后运行：

   ```bash
   python3 <skill-root>/scripts/prepare_splitter.py
   ```

   准备完成后重新执行同一条分割命令。下载依赖需要网络权限时，先按当前运行环境请求授权。
5. 读取最后一行 `RESULT_JSON`，核对输出目录、镜头数、总时长和 `构图参考.html` 是否存在。至少抽查第一个、中间一个和最后一个镜头文件能够读取，再向用户报告完成。
6. 返回镜头数量以及“原视频名镜头分割”文件夹和 `构图参考.html` 的可点击本地链接。

默认输出结构：

```text
原视频名镜头分割/
  构图参考.html
  分镜表.csv
  分镜信息.json
  使用说明.txt
  镜头片段/镜头001.mp4 ...
  关键帧/镜头001.jpg ...
```

`构图参考.html` 是生成结果的一部分，直接用浏览器打开即可，不需要启动服务器。构图九宫格指叠在每个镜头画面上的两条横线和两条竖线，不代表每页显示九个镜头。

## 结果边界

- 镜头切换由 FFmpeg 画面变化检测完成，默认阈值为 0.25，最短镜头为 0.35 秒。转场、闪光或缓慢变化可能需要人工复核，不要称为完美分割。
- 只分析镜头边界、时长、关键帧和构图。参考视频的文案、原声、音乐和完整剪辑不能直接进入用户的新视频。
- 用户要模仿拍摄时，可以建议逐镜头对照机位、主体位置、景别和动作，同时使用自己的产品内容和表达。
- 同名输出已存在时，脚本会生成带序号的新文件夹，不覆盖原结果。

## 可选的 localhost 工作台

只有用户明确要求打开完整网页工作台时，才使用本模式。

1. 阅读当前项目的 `AGENTS.md`。
2. 要求项目根目录至少存在 `assets/` 和 `work/`。
3. 运行：

   ```bash
   python3 <skill-root>/scripts/check_project.py --project-root <absolute-project-root>
   python3 <skill-root>/scripts/launch_dashboard.py --project-root <absolute-project-root>
   ```

4. 等待启动器打印 `Local:` 地址后再打开网页。不要在服务器尚未响应时声称网页已经打开。

工作台和对话式分割都只在用户电脑上处理媒体。不要提交 `public/dashboard-data.json`、`public/local-media/`、`.splitter-runtime/`、源视频、镜头结果、素材、配音或成片。

当修改工作台数据字段时，读取 [references/data-contract.md](references/data-contract.md)。
