#!/usr/bin/env python3
"""Local-only upload API for the auto-video-remix dashboard."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


SITE_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024 * 1024


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def project_id(project_root: Path) -> str:
    return hashlib.sha256(str(project_root.resolve()).encode("utf-8")).hexdigest()[:12]


def safe_label(value: str) -> str:
    label = Path(value.strip()).stem
    label = re.sub(r"[\\/:*?\"<>|=\x00-\x1f]", "-", label)
    label = re.sub(r"\s+", "-", label)
    label = re.sub(r"-+", "-", label).strip("-. ")
    return label[:48] or "新爆款"


def unique_work_dir(project_root: Path, requested_label: str, task_date: str) -> tuple[str, Path]:
    base = safe_label(requested_label)
    label = base
    index = 2
    while (project_root / "work" / f"{task_date}-{label}").exists():
        label = f"{base}-{index}"
        index += 1
    work_dir = (project_root / "work" / f"{task_date}-{label}").resolve()
    work_root = (project_root / "work").resolve()
    if work_root not in work_dir.parents:
        raise RuntimeError("任务文件夹超出了 work 目录")
    return label, work_dir


def run(command: list[str], cwd: Path, timeout: int = 3600) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    if result.returncode:
        message = result.stdout.strip().splitlines()
        raise RuntimeError(message[-1] if message else f"命令执行失败，状态码 {result.returncode}")
    return result


def probe_video(project_root: Path, video_path: Path) -> tuple[int, int]:
    ffmpeg = project_root / "bin" / "ffmpeg"
    if not ffmpeg.is_file():
        raise RuntimeError("项目中缺少 bin/ffmpeg，无法读取对标视频")
    result = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-i", str(video_path)],
        cwd=project_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    match = re.search(r"Video:.*?,\s*(\d+)x(\d+)", result.stdout, re.S)
    if not match:
        raise RuntimeError("无法读取视频画面，请确认文件没有损坏")
    return int(match.group(1)), int(match.group(2))


def normalize_to_mp4(project_root: Path, incoming: Path, destination: Path, extension: str) -> None:
    if extension == ".mp4":
        incoming.replace(destination)
        return

    ffmpeg = project_root / "bin" / "ffmpeg"
    copy_command = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(incoming),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        "-y",
        str(destination),
    ]
    copied = subprocess.run(copy_command, cwd=project_root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if copied.returncode:
        encode_command = [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(incoming),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-y",
            str(destination),
        ]
        encoded = subprocess.run(encode_command, cwd=project_root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if encoded.returncode:
            raise RuntimeError("MOV/M4V 转为 MP4 失败，请改用 MP4 文件")
    incoming.unlink(missing_ok=True)


def task_config(width: int, height: int) -> dict[str, Any]:
    landscape = width >= height
    return {
        "schema_version": 1,
        "canvas": {
            "orientation": "landscape" if landscape else "portrait",
            "width": 1920 if landscape else 1080,
            "height": 1080 if landscape else 1920,
            "fps": 60,
        },
        "voice": {
            "mode": "whole_script_single_request",
            "max_tts_requests": 1,
            "provider": "Doubao Seed-TTS 2.0",
            "emotion_instruction_allowed": True,
            "speaker_prompt": "zh_male_m191_uranus_bigtts",
            "speed_ratio": 1.2,
        },
        "captions": {"mode": "srt", "alignment": "continuous_voice"},
        "draft": {"target": "none", "mode": "pending_user_choice", "one_clip_per_shot": True},
    }


def refresh_dashboard(project_root: Path) -> None:
    run(
        [
            sys.executable,
            str(SITE_ROOT / "scripts" / "export_dashboard_data.py"),
            "--project-root",
            str(project_root),
            "--site-root",
            str(SITE_ROOT),
        ],
        cwd=SITE_ROOT,
    )


def create_task(project_root: Path, incoming: Path, original_name: str, requested_title: str) -> dict[str, Any]:
    task_date = date.today().isoformat()
    title = requested_title.strip() or Path(original_name).stem
    label, work_dir = unique_work_dir(project_root, title, task_date)
    work_dir.mkdir(parents=True)
    reference_path = work_dir / f"reference-{task_date}-{label}.mp4"
    task_record = {
        "schema_version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "title": title,
        "folder": work_dir.name,
        "source": "user_uploaded_reference",
        "reference_original_name": Path(original_name).name,
        "reference_copy_authorized": False,
        "status": "processing_reference",
        "next_required_input": "formal_script",
    }
    atomic_write_json(work_dir / "dashboard_task.json", task_record)

    extension = Path(original_name).suffix.lower()
    try:
        normalize_to_mp4(project_root, incoming, reference_path, extension)
        source_width, source_height = probe_video(project_root, reference_path)
        atomic_write_json(work_dir / "task_config.json", task_config(source_width, source_height))

        pipeline = project_root / "tools" / "run_pipeline.py"
        decompose = project_root / "tools" / "decompose_reference.py"
        if not pipeline.is_file() or not decompose.is_file():
            raise RuntimeError("项目缺少视频流水线脚本")

        run([sys.executable, str(pipeline), str(work_dir), "--stage", "intake"], cwd=project_root)
        decomposition = run(
            [
                sys.executable,
                str(decompose),
                "--date",
                task_date,
                f"{label}={reference_path}",
            ],
            cwd=project_root,
        )
        summary = json.loads(decomposition.stdout)[0]
        run([sys.executable, str(pipeline), str(work_dir), "--stage", "dissect"], cwd=project_root)

        task_record.update(
            {
                "status": "waiting_for_script",
                "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "shot_count": int(summary.get("shots") or 0),
                "duration": float(summary.get("duration") or 0),
            }
        )
        atomic_write_json(work_dir / "dashboard_task.json", task_record)
        refresh_dashboard(project_root)
        dashboard_id = hashlib.sha1(work_dir.name.encode("utf-8")).hexdigest()[:16]
        return {
            "ok": True,
            "projectId": dashboard_id,
            "folder": work_dir.name,
            "title": title,
            "shots": task_record["shot_count"],
            "duration": task_record["duration"],
            "status": "waiting_for_script",
        }
    except Exception as error:
        task_record.update(
            {
                "status": "failed",
                "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "error": str(error),
            }
        )
        atomic_write_json(work_dir / "dashboard_task.json", task_record)
        raise


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "AutoVideoRemixLocal/1.0"

    @property
    def project_root(self) -> Path:
        return self.server.project_root  # type: ignore[attr-defined]

    def allowed_origin(self) -> str | None:
        origin = self.headers.get("Origin")
        if not origin:
            return None
        if re.fullmatch(r"https?://(?:localhost|127\.0\.0\.1)(?::\d+)?", origin):
            return origin
        return ""

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        origin = self.allowed_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        if self.allowed_origin() == "":
            self.send_json(403, {"ok": False, "error": "不允许的网页来源"})
            return
        self.send_response(204)
        origin = self.allowed_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json(200, {"ok": True, "projectId": project_id(self.project_root)})
            return
        if parsed.path == "/api/refresh":
            try:
                refresh_dashboard(self.project_root)
                self.send_json(200, {"ok": True})
            except Exception as error:
                self.send_json(500, {"ok": False, "error": str(error)})
            return
        self.send_json(404, {"ok": False, "error": "接口不存在"})

    def do_POST(self) -> None:
        if self.allowed_origin() == "":
            self.send_json(403, {"ok": False, "error": "不允许的网页来源"})
            return
        parsed = urlparse(self.path)
        if parsed.path != "/api/tasks":
            self.send_json(404, {"ok": False, "error": "接口不存在"})
            return
        query = parse_qs(parsed.query)
        original_name = (query.get("filename") or [""])[0]
        title = (query.get("title") or [""])[0]
        extension = Path(original_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            self.send_json(400, {"ok": False, "error": "请选择 MP4、MOV 或 M4V 视频"})
            return
        try:
            content_length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            content_length = 0
        if content_length <= 0:
            self.send_json(411, {"ok": False, "error": "没有收到视频文件"})
            return
        if content_length > MAX_UPLOAD_BYTES:
            self.send_json(413, {"ok": False, "error": "视频超过 8GB，暂时无法从网页导入"})
            return

        incoming_root = self.project_root / "work" / ".dashboard-incoming"
        incoming_root.mkdir(parents=True, exist_ok=True)
        incoming = incoming_root / f"{time.time_ns()}{extension}"
        remaining = content_length
        try:
            with incoming.open("wb") as handle:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise RuntimeError("视频上传中断")
                    handle.write(chunk)
                    remaining -= len(chunk)
            result = create_task(self.project_root, incoming, original_name, title)
            self.send_json(201, result)
        except Exception as error:
            incoming.unlink(missing_ok=True)
            self.send_json(500, {"ok": False, "error": str(error)})

    def log_message(self, format: str, *args: object) -> None:
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")
        sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    project_root = args.project_root.expanduser().resolve()
    missing = [name for name in ("assets", "work", "tools") if not (project_root / name).is_dir()]
    if missing:
        raise RuntimeError(f"项目目录缺少: {', '.join(missing)}")
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    server.project_root = project_root  # type: ignore[attr-defined]
    print(f"Local API: http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as error:
        print(f"Local API failed: {error}", file=sys.stderr)
        raise SystemExit(1)
