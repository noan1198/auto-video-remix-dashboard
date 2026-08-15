# Auto Video Remix Dashboard

一个以 Codex Skill 形式安装、在用户电脑上运行的爆款对标视频工作台。GitHub 只分发程序，素材、对标视频、配音、成片和使用台账保留在本机。

## 它能做什么

- 拖入 MP4、MOV 或 M4V 对标视频，在 `work/` 中建立独立日期任务。
- 拆解对标视频的镜头边界、时长、关键帧和参考音轨。
- 查看本机素材缩略图，并按场景、动作、产品和文件名搜索。
- 查看素材在已确认成片中的使用次数、接近复用上限和自动排除状态。
- 一屏对照对标爆款、本次选片审核图和生成成片。
- 查看文案、匹配、配音、渲染、视觉审核、使用审核和交付状态。
- 浏览历史任务，追回每条视频的对标、镜头数、选片和成片状态。

## 安装后到底能做到哪一步

| 当前电脑具备的内容 | 能做什么 |
| --- | --- |
| 只安装这个仓库 | 安装网页 Skill。仍需在兼容的视频项目中打开，不能独立生成成片。 |
| 项目有 `assets/` 和 `work/` | 查看素材库、历史任务、成片和已有生产状态。 |
| 再有 FFmpeg、`decompose_reference.py` 和 `run_pipeline.py` | 拖入新的对标视频并完成导入和镜头拆解。 |
| 再有完整生产脚本、素材库和配音配置 | Codex 可以继续进行素材匹配、整篇配音、渲染、审核和草稿生成。每条任务仍需正式文案授权和人工审核。 |

这个仓库目前是本机网页工作台和对标导入入口。单独安装后，不能自动剪出与作者本机项目相同的最终成片。

完整制作还需要以下环节：

1. 用户提供或确认正式文案。
2. 建立素材帧缓存并逐镜匹配本机素材。
3. 整篇文案只调用一次配音服务，生成连续配音。
4. 按真实配音时间生成画面、字幕和可编辑草稿。
5. 完成视觉近重复审核、素材使用次数审核和最终验收。
6. 用户确认成片后，才把素材使用次数写入台账。

## 安装

在 Codex 中发送：

```text
安装 https://github.com/noan1198/auto-video-remix-dashboard 这个 Skill
```

安装完成后，在兼容的 Auto Video Remix 项目中发送：

```text
打开爆款素材工作台
```

Skill 会读取当前项目、刷新本地数据并打开 `localhost` 网页。首次使用需要 Node.js 22.13 或更高版本，以及 pnpm 或 npm。

## 检查当前项目能用到哪一步

```bash
python3 scripts/check_project.py --project-root /path/to/video-project
```

检查结果会分别显示：

- 网页查看素材与历史任务是否可用。
- 对标视频导入和镜头拆解是否可用。
- 完整生产工具脚本是否存在。
- 每条成片仍需人工提供或确认的内容。

## 兼容项目结构

```text
video-project/
├── assets/
├── work/
├── final/
├── asset_usage_registry.json
├── bin/
│   └── ffmpeg
└── tools/
    ├── decompose_reference.py
    ├── run_pipeline.py
    ├── build_asset_frame_catalog.py
    ├── match_materials.py
    ├── content_provenance.py
    ├── generate_whole_voice_once.py
    ├── render_remix_and_draft.py
    ├── audit_selected_visual_duplicates.py
    ├── asset_usage_registry.py
    └── validate_project.py
```

只有查看网页时，不要求所有生产脚本都存在。新建对标任务至少需要 `bin/ffmpeg`、`tools/decompose_reference.py` 和 `tools/run_pipeline.py`。

## 对标视频的使用边界

拖入对标视频只代表允许分析镜头结构、节奏和画面关系。参考视频中的文案、原声、音乐和完整剪辑不会自动进入新成片。拆解完成后，新任务会停在“待提供正式文案”。

## 本机隐私

- 本机接口只监听 `127.0.0.1`。
- 公开仓库只保留 `public/dashboard-data.example.json` 演示数据。
- `public/dashboard-data.json` 和 `public/local-media/` 由每台电脑本机生成，已加入 Git 忽略规则。
- 程序不会把素材、对标视频、配音、成片、使用历史或绝对路径上传到云端。
- 素材库作为只读来源使用，新任务只会复制需要的素材，不移动原文件。

## 本地开发

```bash
pnpm install
python3 scripts/export_dashboard_data.py --project-root /path/to/video-project
python3 scripts/launch_dashboard.py --project-root /path/to/video-project
```
