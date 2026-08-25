#!/usr/bin/env python3
"""Split one reference video into shots and generate a local composition report."""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = SKILL_ROOT / ".splitter-runtime"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}


def runtime_python(runtime: Path = DEFAULT_RUNTIME) -> Path:
    if sys.platform == "win32":
        return runtime / "Scripts" / "python.exe"
    return runtime / "bin" / "python"


def executable_candidate(value: str | Path | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if path.is_file() and os.access(path, os.X_OK):
        return path.resolve()
    discovered = shutil.which(str(value))
    return Path(discovered).resolve() if discovered else None


def resolve_ffmpeg(explicit: str | None = None) -> Path:
    candidates = [
        explicit,
        os.environ.get("FFMPEG_BINARY"),
        "ffmpeg",
        Path.cwd() / "bin" / "ffmpeg",
        SKILL_ROOT / "bin" / "ffmpeg",
    ]
    for candidate in candidates:
        resolved = executable_candidate(candidate)
        if resolved:
            return resolved

    try:
        import imageio_ffmpeg

        return Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
    except (ImportError, RuntimeError):
        prepared_python = runtime_python()
        if prepared_python.is_file() and Path(sys.executable).absolute() != prepared_python.absolute():
            os.execv(str(prepared_python), [str(prepared_python), str(Path(__file__).resolve()), *sys.argv[1:]])
        raise RuntimeError(
            "缺少本地视频组件。请先运行 scripts/prepare_splitter.py，完成后重新执行本命令。"
        )


def run(command: list[str | Path], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(item) for item in command],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "视频处理失败"
        raise RuntimeError(detail)
    return result


def safe_stem(value: str) -> str:
    name = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "-", value).strip(" .-")
    name = re.sub(r"\s+", " ", name)
    return name[:80] or "爆款视频"


def unique_output_dir(output_root: Path, stem: str) -> Path:
    base = output_root / f"{stem}镜头分割"
    if not base.exists():
        return base
    index = 2
    while (output_root / f"{stem}镜头分割-{index}").exists():
        index += 1
    return output_root / f"{stem}镜头分割-{index}"


def probe_video(ffmpeg: Path, source: Path) -> dict[str, object]:
    result = run([ffmpeg, "-hide_banner", "-i", source], check=False)
    raw = result.stdout + result.stderr
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", raw)
    if not duration_match:
        raise RuntimeError("无法读取视频时长")
    hours, minutes, seconds = duration_match.groups()
    duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    video_match = re.search(r"Video:.*?,\s*(\d+)x(\d+).*?,\s*([\d.]+)\s*fps", raw, re.S)
    return {
        "duration": duration,
        "width": int(video_match.group(1)) if video_match else None,
        "height": int(video_match.group(2)) if video_match else None,
        "fps": float(video_match.group(3)) if video_match else None,
    }


def detect_scene_changes(ffmpeg: Path, source: Path, threshold: float) -> list[float]:
    result = run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            source,
            "-filter:v",
            f"select='gt(scene,{threshold})',showinfo",
            "-f",
            "null",
            "-",
        ],
        check=False,
    )
    raw = result.stdout + result.stderr
    points: list[float] = []
    for match in re.finditer(r"pts_time:([0-9]+(?:\.[0-9]+)?)", raw):
        point = float(match.group(1))
        if not points or abs(point - points[-1]) > 0.15:
            points.append(point)
    return points


def merge_short_segments(points: list[float], duration: float, minimum: float) -> list[float]:
    boundaries = [0.0]
    for point in sorted(set(round(value, 3) for value in points if 0 < value < duration)):
        if point - boundaries[-1] >= minimum:
            boundaries.append(point)
    if duration - boundaries[-1] < minimum and len(boundaries) > 1:
        boundaries.pop()
    boundaries.append(duration)
    return boundaries


def extract_clip(ffmpeg: Path, source: Path, start: float, duration: float, output: Path) -> None:
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{start:.3f}",
            "-i",
            source,
            "-t",
            f"{duration:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-avoid_negative_ts",
            "make_zero",
            output,
        ]
    )


def extract_keyframe(ffmpeg: Path, source: Path, timestamp: float, output: Path) -> None:
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            source,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            output,
        ]
    )


def seconds_label(value: float) -> str:
    minutes = int(value // 60)
    seconds = value - minutes * 60
    return f"{minutes:02d}:{seconds:05.2f}"


def write_csv(output: Path, shots: list[dict[str, object]]) -> None:
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["镜头", "开始时间", "结束时间", "持续时间", "片段文件", "关键帧文件"])
        for shot in shots:
            writer.writerow(
                [
                    shot["index"],
                    shot["start"],
                    shot["end"],
                    shot["duration"],
                    shot["clip"],
                    shot["keyframe"],
                ]
            )


def write_report(output: Path, title: str, metadata: dict[str, object], shots: list[dict[str, object]]) -> None:
    cards = []
    for shot in shots:
        clip = quote(str(shot["clip"]).replace(os.sep, "/"))
        index = int(shot["index"])
        cards.append(
            f"""
            <article class="shot">
              <div class="stage">
                <video controls preload="metadata" src="{clip}"></video>
                <div class="composition-grid" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
                <b>{index:02d}</b>
              </div>
              <div class="meta">
                <strong>镜头 {index:02d}</strong>
                <span>{seconds_label(float(shot['start']))} 到 {seconds_label(float(shot['end']))}</span>
                <em>{float(shot['duration']):.2f} 秒</em>
              </div>
            </article>
            """
        )

    safe_title = html.escape(title)
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{safe_title}镜头分割</title>
  <style>
    :root {{ color-scheme: dark; font-family: -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #080a0d; color: #f7f7f2; }}
    header {{ position: sticky; top: 0; z-index: 5; display: flex; gap: 18px; align-items: center; justify-content: space-between; padding: 18px 24px; background: rgba(8,10,13,.92); border-bottom: 1px solid #282b31; backdrop-filter: blur(18px); }}
    h1 {{ margin: 0; font-size: clamp(20px,3vw,34px); }}
    header p {{ margin: 5px 0 0; color: #aeb3bc; }}
    button {{ border: 1px solid #ffe100; border-radius: 999px; padding: 10px 16px; background: #ffe100; color: #111; font-weight: 800; cursor: pointer; }}
    main {{ display: grid; grid-template-columns: repeat(auto-fill,minmax(280px,1fr)); gap: 18px; padding: 24px; }}
    .shot {{ overflow: hidden; border: 1px solid #282b31; border-radius: 18px; background: #111419; }}
    .stage {{ position: relative; aspect-ratio: {metadata.get('width') or 16}/{metadata.get('height') or 9}; background: #000; }}
    video {{ width: 100%; height: 100%; display: block; object-fit: contain; }}
    .stage b {{ position: absolute; left: 10px; top: 10px; padding: 5px 8px; border-radius: 8px; background: #ffe100; color: #111; font-size: 13px; }}
    .composition-grid {{ position: absolute; inset: 0; pointer-events: none; opacity: .8; transition: opacity .2s; }}
    .composition-grid i {{ position: absolute; display: block; background: rgba(255,225,0,.95); box-shadow: 0 0 0 1px rgba(0,0,0,.35); }}
    .composition-grid i:nth-child(1),.composition-grid i:nth-child(2) {{ top: 0; bottom: 0; width: 1px; }}
    .composition-grid i:nth-child(1) {{ left: 33.333%; }} .composition-grid i:nth-child(2) {{ left: 66.666%; }}
    .composition-grid i:nth-child(3),.composition-grid i:nth-child(4) {{ left: 0; right: 0; height: 1px; }}
    .composition-grid i:nth-child(3) {{ top: 33.333%; }} .composition-grid i:nth-child(4) {{ top: 66.666%; }}
    body.grid-off .composition-grid {{ opacity: 0; }}
    .meta {{ display: grid; grid-template-columns: 1fr auto; gap: 6px 12px; padding: 14px 16px 16px; }}
    .meta strong {{ font-size: 17px; }} .meta span {{ grid-column: 1; color: #aeb3bc; font-variant-numeric: tabular-nums; }} .meta em {{ grid-column: 2; grid-row: 1 / span 2; align-self: center; color: #ffe100; font-style: normal; }}
    @media (max-width: 620px) {{ header {{ align-items: flex-start; padding: 14px; }} main {{ grid-template-columns: 1fr; padding: 14px; }} button {{ padding: 8px 12px; }} }}
  </style>
</head>
<body>
  <header>
    <div><h1>{safe_title}镜头分割</h1><p>{len(shots)} 个镜头，总时长 {float(metadata['duration']):.2f} 秒</p></div>
    <button id="grid-toggle" type="button">构图九宫格：开</button>
  </header>
  <main>{''.join(cards)}</main>
  <script>
    const button = document.querySelector('#grid-toggle');
    button.addEventListener('click', () => {{
      document.body.classList.toggle('grid-off');
      button.textContent = document.body.classList.contains('grid-off') ? '构图九宫格：关' : '构图九宫格：开';
    }});
  </script>
</body>
</html>
"""
    output.write_text(document, encoding="utf-8")


def split_video(source: Path, output_root: Path, title: str, ffmpeg: Path, threshold: float, minimum: float) -> dict[str, object]:
    metadata = probe_video(ffmpeg, source)
    points = detect_scene_changes(ffmpeg, source, threshold)
    boundaries = merge_short_segments(points, float(metadata["duration"]), minimum)
    final_dir = unique_output_dir(output_root, title)
    temporary_dir = output_root / f".{final_dir.name}.处理中-{int(time.time())}"
    clips_dir = temporary_dir / "镜头片段"
    keyframes_dir = temporary_dir / "关键帧"
    clips_dir.mkdir(parents=True)
    keyframes_dir.mkdir(parents=True)

    shots: list[dict[str, object]] = []
    try:
        total = len(boundaries) - 1
        for offset in range(total):
            index = offset + 1
            start = boundaries[offset]
            end = boundaries[offset + 1]
            duration = end - start
            clip_relative = Path("镜头片段") / f"镜头{index:03d}.mp4"
            keyframe_relative = Path("关键帧") / f"镜头{index:03d}.jpg"
            print(f"正在生成镜头 {index}/{total}", flush=True)
            extract_clip(ffmpeg, source, start, duration, temporary_dir / clip_relative)
            extract_keyframe(ffmpeg, source, start + duration / 2, temporary_dir / keyframe_relative)
            shots.append(
                {
                    "index": index,
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "duration": round(duration, 3),
                    "clip": str(clip_relative),
                    "keyframe": str(keyframe_relative),
                }
            )

        payload = {
            "source": source.name,
            "title": title,
            "video": metadata,
            "scene_detection": {
                "method": "ffmpeg scene change",
                "threshold": threshold,
                "minimum_shot_duration": minimum,
                "raw_cut_points": [round(point, 3) for point in points],
            },
            "shots": shots,
        }
        (temporary_dir / "分镜信息.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        write_csv(temporary_dir / "分镜表.csv", shots)
        write_report(temporary_dir / "构图参考.html", title, metadata, shots)
        (temporary_dir / "使用说明.txt").write_text(
            "双击“构图参考.html”查看所有镜头。\n"
            "每个镜头都可以单独播放，构图九宫格默认开启。\n"
            "拍摄时打开手机或相机的九宫格，按照主体位置、景别和动作逐镜头对照。\n",
            encoding="utf-8",
        )
        temporary_dir.rename(final_dir)
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise

    return {
        "ok": True,
        "output": str(final_dir),
        "report": str(final_dir / "构图参考.html"),
        "shots": len(shots),
        "duration": round(float(metadata["duration"]), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--name")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--threshold", type=float, default=0.25)
    parser.add_argument("--min-duration", type=float, default=0.35)
    args = parser.parse_args()

    source = args.video.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() not in VIDEO_EXTENSIONS:
        raise RuntimeError("请选择 MP4、MOV、M4V、WEBM 或 MKV 视频")
    output_root = (args.output_root.expanduser().resolve() if args.output_root else source.parent)
    output_root.mkdir(parents=True, exist_ok=True)
    title = safe_stem(args.name or source.stem)
    result = split_video(
        source,
        output_root,
        title,
        resolve_ffmpeg(args.ffmpeg),
        args.threshold,
        args.min_duration,
    )
    print("RESULT_JSON=" + json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as error:
        print(f"镜头分割失败：{error}", file=sys.stderr)
        raise SystemExit(1)
