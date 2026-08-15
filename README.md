# Auto Video Remix Dashboard

一个以 Codex skill 形式安装、在用户电脑上运行的视频素材工作台。GitHub 只分发程序，素材、对标视频、配音和成片不会上传到云端。

网页会显示素材缩略图、已确认的使用次数、复用上限、本次对标视频、选片审核图、成片和流程状态。左侧的“新建爆款任务”可以接收 MP4、MOV 或 M4V 视频，在本机建立新的日期任务并开始拆解镜头。

## 安装

在 Codex 中发送：

```text
安装 https://github.com/noan1198/auto-video-remix-dashboard 这个 Skill
```

这个仓库提供网页工作台，不包含作者的素材库和私人项目文件。当前版本适用于已有的 Auto Video Remix 项目，项目中需要存在 `assets/`、`work/`、`tools/run_pipeline.py`、`tools/decompose_reference.py` 和 `bin/ffmpeg`。

## 安装后使用

在 Codex 中安装这个仓库后，在一个包含 `assets/` 和 `work/` 的视频项目里说：

```text
打开爆款素材工作台
```

skill 会刷新本地数据并打开 `localhost` 网页。首次使用需要 Node.js 22.13 或更高版本，以及 pnpm 或 npm。Codex 桌面版在可用时会使用自带的 Node.js 运行环境。

拖入对标视频后，程序只完成导入和镜头拆解。参考视频中的文案、原声、音乐不会自动进入新成片，任务会等待用户提供或确认正式文案。

## 本地开发

```bash
pnpm install
python3 scripts/export_dashboard_data.py --project-root /path/to/video-project
python3 scripts/launch_dashboard.py --project-root /path/to/video-project
```

公开仓库中只保留 `public/dashboard-data.example.json`。`public/dashboard-data.json` 和 `public/local-media/` 由每个用户在本机生成，已加入 Git 忽略规则。
