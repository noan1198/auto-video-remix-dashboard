#!/usr/bin/env python3
"""Exercise local task creation in an isolated temporary project."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch


WEB_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = WEB_ROOT / "scripts" / "local_api_server.py"
SPEC = importlib.util.spec_from_file_location("local_api_server", MODULE_PATH)
assert SPEC and SPEC.loader
local_api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(local_api)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.project_root.expanduser().resolve()

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "assets").mkdir()
        (root / "work").mkdir()
        (root / "tools").mkdir()
        (root / "bin").mkdir()
        shutil.copy2(source_root / "tools" / "run_pipeline.py", root / "tools" / "run_pipeline.py")
        shutil.copy2(source_root / "tools" / "decompose_reference.py", root / "tools" / "decompose_reference.py")
        (root / "bin" / "ffmpeg").symlink_to(source_root / "bin" / "ffmpeg")

        incoming = root / "incoming.mp4"
        subprocess.run(
            [
                str(root / "bin" / "ffmpeg"),
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=640x360:rate=30",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=660:sample_rate=44100",
                "-t",
                "1.2",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                "-y",
                str(incoming),
            ],
            check=True,
        )

        with patch.object(local_api, "refresh_dashboard", return_value=None):
            result = local_api.create_task(root, incoming, "网页测试.mp4", "网页导入功能测试")

        task = root / "work" / result["folder"]
        task_record = json.loads((task / "dashboard_task.json").read_text(encoding="utf-8"))
        pipeline = json.loads((task / "pipeline_state.json").read_text(encoding="utf-8"))
        assert result["status"] == "waiting_for_script"
        assert result["shots"] >= 1
        assert task_record["reference_copy_authorized"] is False
        assert task_record["next_required_input"] == "formal_script"
        assert pipeline["stages"]["intake"]["status"] == "passed"
        assert pipeline["stages"]["dissect"]["status"] == "passed"
        assert "register_script" not in pipeline["stages"]
        assert list((task / "video_clips").glob("fragment*_keyframe.jpg"))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
