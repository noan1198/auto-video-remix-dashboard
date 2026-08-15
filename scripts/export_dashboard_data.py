#!/usr/bin/env python3
"""Export a privacy-safe local dashboard snapshot from an auto-video-remix project."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


MEDIA_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
STAGE_ORDER = (
    "intake",
    "preflight",
    "dissect",
    "register_script",
    "match",
    "voice",
    "render",
    "audit_visual",
    "audit_usage",
    "build_draft",
    "validate",
    "package",
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def web_name(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def copy_image(source: Path, destination: Path) -> bool:
    if not source.is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or source.stat().st_mtime_ns > destination.stat().st_mtime_ns:
        shutil.copy2(source, destination)
    return True


def generate_video_poster(ffmpeg: Path, source: Path, destination: Path) -> bool:
    if not source.is_file() or not ffmpeg.is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_mtime_ns >= source.stat().st_mtime_ns:
        return True
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        "0.5",
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        "scale='min(960,iw)':-2",
        "-q:v",
        "3",
        "-y",
        str(destination),
    ]
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0 and destination.is_file()


def normalize_relative(project_root: Path, path: str) -> str:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(project_root.resolve()).as_posix()
        except ValueError:
            return candidate.name
    return candidate.as_posix().lstrip("./")


def load_frame_catalog(project_root: Path) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    cache_root = project_root / "work" / ".cache"
    for name in ("asset_frame_catalog_v1.json", "horizontal_asset_frame_catalog_v1.json"):
        payload = read_json(cache_root / name)
        entries = payload.get("entries") or {}
        if isinstance(entries, dict):
            for path, record in entries.items():
                if isinstance(record, dict):
                    merged[normalize_relative(project_root, str(path))] = record
    return merged


def load_catalog_metadata(project_root: Path) -> dict[str, dict[str, str]]:
    payload = read_json(project_root / "asset_library_catalog.json")
    result: dict[str, dict[str, str]] = {}
    collections = payload.get("collections") or []
    if not isinstance(collections, list):
        return result
    for collection in collections:
        if not isinstance(collection, dict):
            continue
        base = str(collection.get("path") or "assets")
        product = str(collection.get("product") or "")
        for item in collection.get("media") or []:
            if not isinstance(item, dict) or not item.get("file"):
                continue
            relative = (Path(base) / str(item["file"])).as_posix()
            result[relative] = {
                "product": product,
                "category": str(item.get("category") or "待分类"),
                "description": str(item.get("description") or ""),
            }
    return result


def load_usage(project_root: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(project_root / "asset_usage_registry.json")
    result: dict[str, dict[str, Any]] = {}
    assets = payload.get("assets") or {}
    if not isinstance(assets, dict):
        return result
    for fingerprint, record in assets.items():
        if not isinstance(record, dict):
            continue
        for path_key in ("canonical_path", "last_seen_path"):
            path = record.get(path_key)
            if path:
                result[normalize_relative(project_root, str(path))] = {
                    "fingerprint": fingerprint,
                    "count": int(record.get("confirmed_appearance_count") or 0),
                    "last_used_at": record.get("last_used_at"),
                }
    return result


def usage_status(count: int) -> str:
    if count >= 6:
        return "excluded"
    if count >= 4:
        return "near-limit"
    if count >= 1:
        return "used"
    return "unused"


def choose_sample(project_root: Path, record: dict[str, Any]) -> Path | None:
    samples = record.get("samples") or []
    if not isinstance(samples, list) or not samples:
        return None
    ordered = [samples[len(samples) // 2], *samples]
    seen: set[str] = set()
    for sample in ordered:
        if not isinstance(sample, dict) or not sample.get("path"):
            continue
        value = str(sample["path"])
        if value in seen:
            continue
        seen.add(value)
        candidate = Path(value)
        source = candidate if candidate.is_absolute() else project_root / candidate
        if source.is_file():
            return source
    return None


def export_assets(project_root: Path, site_root: Path, limit: int) -> list[dict[str, Any]]:
    frames = load_frame_catalog(project_root)
    metadata = load_catalog_metadata(project_root)
    usage = load_usage(project_root)
    media_files = sorted(
        path
        for path in (project_root / "assets").rglob("*")
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    )
    records: list[dict[str, Any]] = []
    for source in media_files[:limit]:
        relative = source.relative_to(project_root).as_posix()
        frame_record = frames.get(relative, {})
        catalog_record = metadata.get(relative, {})
        usage_record = usage.get(relative, {})
        thumb_url = None
        sample = choose_sample(project_root, frame_record)
        if sample:
            output_name = f"{web_name(relative)}.jpg"
            destination = site_root / "public" / "local-media" / "assets" / output_name
            if copy_image(sample, destination):
                thumb_url = f"/local-media/assets/{output_name}"
        count = int(usage_record.get("count") or 0)
        records.append(
            {
                "id": web_name(relative),
                "name": source.name,
                "relativePath": relative,
                "collection": source.parent.name,
                "product": catalog_record.get("product") or source.parent.parent.name,
                "category": catalog_record.get("category") or "待分类",
                "description": catalog_record.get("description") or "等待补充画面用途",
                "thumbnail": thumb_url,
                "usageCount": count,
                "usageStatus": usage_status(count),
                "lastUsedAt": usage_record.get("last_used_at"),
                "duration": round(float(frame_record.get("duration") or 0), 1),
                "width": int(frame_record.get("width") or 0),
                "height": int(frame_record.get("height") or 0),
            }
        )
    records.sort(key=lambda item: (-item["usageCount"], item["collection"], item["name"]))
    return records


def stage_status(entry: dict[str, Any]) -> str:
    if entry.get("status") == "passed" and entry.get("invalidated_by"):
        return "stale"
    return str(entry.get("status") or "pending")


def project_title(folder: Path) -> str:
    parts = folder.name.split("-", 3)
    return parts[3] if len(parts) == 4 else folder.name


def export_projects(project_root: Path, site_root: Path, ffmpeg: Path) -> list[dict[str, Any]]:
    work_root = project_root / "work"
    folders = sorted(
        [path for path in work_root.iterdir() if path.is_dir() and not path.name.startswith(".")],
        key=lambda path: path.name,
        reverse=True,
    )
    records: list[dict[str, Any]] = []
    for folder in folders:
        references = sorted(folder.glob("reference-*.mp4"))
        fragment_plan = read_json(folder / "fragment_plan.json")
        fragments = fragment_plan.get("fragments") or []
        recipe = read_json(folder / "recipe.json")
        recipe_shots = recipe.get("shots") or []
        if not references and not fragments and not (folder / "remix.mp4").is_file():
            continue

        project_id = web_name(folder.name)
        media_root = site_root / "public" / "local-media" / "projects" / project_id
        reference_poster_url = None
        reference_keyframes = sorted((folder / "video_clips").glob("fragment*_keyframe.*"))
        if reference_keyframes:
            destination = media_root / "reference.jpg"
            if copy_image(reference_keyframes[0], destination):
                reference_poster_url = f"/local-media/projects/{project_id}/reference.jpg"

        output = folder / "remix.mp4"
        output_poster_url = None
        if output.is_file():
            destination = media_root / "output.jpg"
            if generate_video_poster(ffmpeg, output, destination):
                output_poster_url = f"/local-media/projects/{project_id}/output.jpg"

        audit = read_json(folder / "visual_duplicate_audit.json")
        contact_sheet_value = audit.get("contact_sheet")
        contact_sheet = None
        if contact_sheet_value:
            candidate = Path(str(contact_sheet_value))
            contact_sheet = candidate if candidate.is_absolute() else folder / candidate
        if not contact_sheet or not contact_sheet.is_file():
            fallback = folder / "video_clips" / "selected_fragments_visual_audit.jpg"
            contact_sheet = fallback if fallback.is_file() else None
        review_board_url = None
        if contact_sheet:
            destination = media_root / "review-board.jpg"
            if copy_image(contact_sheet, destination):
                review_board_url = f"/local-media/projects/{project_id}/review-board.jpg"

        config = read_json(folder / "task_config.json")
        canvas = config.get("canvas") or {}
        dashboard_task = read_json(folder / "dashboard_task.json")
        inferred_statuses = {
            "intake": "completed" if references and config else "pending",
            "preflight": "completed" if output.is_file() and (folder / "content_manifest.json").is_file() else "pending",
            "dissect": "completed" if recipe and reference_keyframes else "pending",
            "register_script": "completed" if (folder / "content_manifest.json").is_file() else "pending",
            "match": "completed" if fragment_plan and (folder / "matches.json").is_file() else "pending",
            "voice": "completed" if (folder / "voice" / "synthesis_manifest.json").is_file() else "pending",
            "render": "completed" if output.is_file() else "pending",
            "audit_visual": "completed" if audit.get("review_status") == "completed" else "pending",
            "audit_usage": "completed" if (folder / "asset_usage_audit.json").is_file() else "pending",
            "build_draft": "completed" if output.is_file() and any(folder.glob("*_draft")) else "pending",
            "validate": "completed" if (folder / "final_render_summary.json").is_file() else "pending",
            "package": "completed" if (folder / "package_manifest.json").is_file() else "pending",
        }
        state = read_json(folder / "pipeline_state.json")
        stages_payload = state.get("stages") or {}
        stages = []
        if not isinstance(stages_payload, dict):
            stages_payload = {}
        for name in STAGE_ORDER:
            entry = stages_payload.get(name) or {}
            if name == "audit_visual" and not entry:
                entry = stages_payload.get("audit_review") or {}
            stages.append(
                {
                    "name": name,
                    "status": stage_status(entry) if entry else inferred_statuses[name],
                    "updatedAt": entry.get("updated_at") if isinstance(entry, dict) else None,
                }
            )

        matched_count = sum(1 for item in fragments if isinstance(item, dict) and item.get("status") == "matched")
        shot_count = len(fragments) or len(recipe_shots)
        declared_missing = fragment_plan.get("missing_fragments") or []
        missing_count = len(declared_missing) if fragment_plan else max(0, shot_count - matched_count)
        records.append(
            {
                "id": project_id,
                "folder": folder.name,
                "title": str(dashboard_task.get("title") or project_title(folder)),
                "date": folder.name[:10],
                "taskStatus": str(dashboard_task.get("status") or "legacy"),
                "reference": {
                    "name": references[0].name if references else "待导入对标视频",
                    "poster": reference_poster_url,
                },
                "output": {
                    "exists": output.is_file(),
                    "name": output.name if output.is_file() else "待生成成片",
                    "poster": output_poster_url,
                },
                "reviewBoard": review_board_url,
                "shotCount": shot_count,
                "matchedCount": matched_count,
                "missingCount": missing_count,
                "auditStatus": str(audit.get("review_status") or "pending"),
                "auditDecision": str(audit.get("decision") or "pending"),
                "packageStatus": str((read_json(folder / "package_manifest.json").get("status") or "pending")),
                "canvas": {
                    "orientation": canvas.get("orientation"),
                    "width": canvas.get("width"),
                    "height": canvas.get("height"),
                    "fps": canvas.get("fps"),
                },
                "stages": stages,
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    script_path = Path(__file__).resolve()
    parser.add_argument("--project-root", type=Path, default=script_path.parents[2])
    parser.add_argument("--site-root", type=Path, default=script_path.parents[1])
    parser.add_argument("--asset-limit", type=int, default=500)
    args = parser.parse_args()

    project_root = args.project_root.expanduser().resolve()
    site_root = args.site_root.expanduser().resolve()
    ffmpeg = project_root / "bin" / "ffmpeg"
    assets = export_assets(project_root, site_root, args.asset_limit)
    projects = export_projects(project_root, site_root, ffmpeg)

    payload = {
        "schemaVersion": 1,
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "local-project",
        "summary": {
            "assetTotal": len(assets),
            "usedAssetTotal": sum(1 for item in assets if item["usageCount"] > 0),
            "nearLimitTotal": sum(1 for item in assets if item["usageStatus"] == "near-limit"),
            "excludedTotal": sum(1 for item in assets if item["usageStatus"] == "excluded"),
            "projectTotal": len(projects),
            "outputTotal": sum(1 for item in projects if item["output"]["exists"]),
        },
        "assets": assets,
        "projects": projects,
    }
    destination = site_root / "public" / "dashboard-data.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已导出 {len(assets)} 条素材、{len(projects)} 个任务：{destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
