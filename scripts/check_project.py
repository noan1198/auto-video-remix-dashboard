#!/usr/bin/env python3
"""Report which dashboard and remix capabilities exist in a local project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


VIEWER_REQUIREMENTS = ("assets", "work")
REFERENCE_REQUIREMENTS = (
    "bin/ffmpeg",
    "tools/decompose_reference.py",
    "tools/run_pipeline.py",
)
PRODUCTION_TOOLKIT_REQUIREMENTS = (
    "tools/build_asset_frame_catalog.py",
    "tools/match_materials.py",
    "tools/content_provenance.py",
    "tools/generate_whole_voice_once.py",
    "tools/render_remix_and_draft.py",
    "tools/audit_selected_visual_duplicates.py",
    "tools/asset_usage_registry.py",
    "tools/validate_project.py",
)
PER_TASK_REQUIREMENTS = (
    "用户提供或确认正式文案",
    "配置可用的整篇单次配音服务或本机声音模型",
    "人工确认选片和视觉近重复审核",
    "确认成片后再登记素材使用次数",
)
MEDIA_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}


def missing_paths(project_root: Path, requirements: tuple[str, ...]) -> list[str]:
    return [relative for relative in requirements if not (project_root / relative).exists()]


def count_assets(project_root: Path) -> int:
    assets = project_root / "assets"
    if not assets.is_dir():
        return 0
    return sum(1 for path in assets.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS)


def inspect_project(project_root: Path) -> dict[str, Any]:
    project_root = project_root.expanduser().resolve()
    viewer_missing = missing_paths(project_root, VIEWER_REQUIREMENTS)
    reference_missing = [*viewer_missing, *missing_paths(project_root, REFERENCE_REQUIREMENTS)]
    toolkit_missing = [*reference_missing, *missing_paths(project_root, PRODUCTION_TOOLKIT_REQUIREMENTS)]
    viewer_ready = not viewer_missing
    reference_ready = not reference_missing
    toolkit_present = not toolkit_missing
    if toolkit_present:
        mode = "production-toolkit"
    elif reference_ready:
        mode = "reference-intake"
    elif viewer_ready:
        mode = "dashboard-only"
    else:
        mode = "not-ready"
    return {
        "schemaVersion": 1,
        "mode": mode,
        "viewerReady": viewer_ready,
        "referenceReady": reference_ready,
        "productionToolkitPresent": toolkit_present,
        "assetCount": count_assets(project_root),
        "missing": {
            "viewer": viewer_missing,
            "reference": reference_missing,
            "productionToolkit": toolkit_missing,
        },
        "perTaskRequirements": list(PER_TASK_REQUIREMENTS),
    }


def status_mark(value: bool) -> str:
    return "已具备" if value else "缺少条件"


def print_human(report: dict[str, Any]) -> None:
    print("爆款素材工作台安装检查")
    print(f"网页查看素材和历史任务：{status_mark(report['viewerReady'])}")
    print(f"拖入并拆解对标视频：{status_mark(report['referenceReady'])}")
    print(f"完整生产工具脚本：{status_mark(report['productionToolkitPresent'])}")
    print(f"发现本地视频素材：{report['assetCount']} 条")
    missing = report["missing"]["productionToolkit"]
    if missing:
        print("当前缺少：")
        for item in missing:
            print(f"  - {item}")
    print("每条成片仍需：")
    for item in report["perTaskRequirements"]:
        print(f"  - {item}")
    if report["mode"] == "production-toolkit":
        print("结论：生产工具已经连接，但仍需按任务提供文案、配音配置并完成人工审核。")
    elif report["mode"] == "reference-intake":
        print("结论：可以查看网页、导入并拆解对标视频，不能仅靠当前安装自动生成最终成片。")
    elif report["mode"] == "dashboard-only":
        print("结论：只能查看已有本地数据，不能导入对标视频或运行剪辑流程。")
    else:
        print("结论：当前目录还不是兼容的视频项目。")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require", choices=("viewer", "reference", "production-toolkit"))
    args = parser.parse_args()
    report = inspect_project(args.project_root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    required_key = {
        "viewer": "viewerReady",
        "reference": "referenceReady",
        "production-toolkit": "productionToolkitPresent",
    }.get(args.require)
    return 0 if not required_key or report[required_key] else 1


if __name__ == "__main__":
    raise SystemExit(main())
