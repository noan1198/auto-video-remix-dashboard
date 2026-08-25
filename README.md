# 爆款视频镜头分割 Skill

把一条参考视频交给 Codex，自动识别镜头切换，并生成一个以原视频命名的镜头分割文件夹。视频只在用户电脑上处理，不会上传到这个 GitHub 仓库。

## 安装

在 Codex 中发送：

```text
安装 https://github.com/noan1198/auto-video-remix-dashboard 这个 Skill
```

安装完成后的下一条对话，把视频拖入 Codex，然后发送：

```text
把这个视频拆成镜头
```

第一次处理视频时，如果电脑没有 FFmpeg，Codex 会请求下载一次本地视频组件。准备完成后，后续视频不需要重复下载。

直接下载 GitHub ZIP 只会得到程序文件，不会自动运行。普通用户使用 Codex 的 GitHub Skill 安装方式最简单。

## 得到什么

假设原视频名是 `爆款视频一.mp4`，默认生成：

```text
爆款视频一镜头分割/
├── 构图参考.html
├── 分镜表.csv
├── 分镜信息.json
├── 使用说明.txt
├── 镜头片段/
│   ├── 镜头001.mp4
│   ├── 镜头002.mp4
│   └── ...
└── 关键帧/
    ├── 镜头001.jpg
    ├── 镜头002.jpg
    └── ...
```

双击 `构图参考.html`，每个镜头都可以独立播放。两条横线和两条竖线会叠在画面上，作为拍摄时的构图九宫格，并且可以随时关闭。

## 能力范围

- 支持 MP4、MOV、M4V、WEBM 和 MKV。
- 自动标出每个镜头的开始时间、结束时间和持续时间。
- 自动生成独立镜头视频、关键帧、CSV 分镜表和本地构图网页。
- 镜头识别使用画面变化检测。转场、闪光、非常缓慢的镜头变化可能需要人工检查。
- 只分析镜头结构和构图。参考视频中的文案、原声、音乐不会被提取后用于新视频。

## 手动运行

电脑已有 FFmpeg 时：

```bash
python3 scripts/split_video.py /path/to/video.mp4
```

电脑没有 FFmpeg 时：

```bash
python3 scripts/prepare_splitter.py
python3 scripts/split_video.py /path/to/video.mp4
```

使用 `--output-root` 可以指定镜头分割文件夹保存位置，使用 `--name` 可以修改输出名称。

## 本机网页工作台

仓库仍然保留适用于完整 Auto Video Remix 项目的 localhost 工作台。项目中存在 `assets/`、`work/` 和相应生产工具时，可以运行：

```bash
python3 scripts/launch_dashboard.py --project-root /path/to/video-project
```

GitHub 只分发程序。`dashboard-data.json`、本机视频、素材、配音、成片和绝对路径均已排除，不会提交到公开仓库。
