#!/usr/bin/env python3
"""Refresh project data and launch the local auto-video-remix dashboard."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


SITE_ROOT = Path(__file__).resolve().parents[1]


def find_executable(name: str, extra: list[Path]) -> Path | None:
    discovered = shutil.which(name)
    if discovered:
        return Path(discovered)
    for candidate in extra:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def runtime_paths() -> tuple[Path | None, Path | None, Path | None]:
    codex_runtime = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies"
    node = find_executable("node", [codex_runtime / "node" / "bin" / "node"])
    pnpm = find_executable("pnpm", [codex_runtime / "bin" / "fallback" / "pnpm"])
    npm = find_executable("npm", [])
    return node, pnpm, npm


def build_env(node: Path | None, package_manager: Path) -> dict[str, str]:
    env = os.environ.copy()
    additions = [str(package_manager.parent)]
    if node:
        additions.insert(0, str(node.parent))
    env["PATH"] = os.pathsep.join([*additions, env.get("PATH", "")])
    return env


def prepare_dependencies(node: Path | None, pnpm: Path | None, npm: Path | None) -> tuple[Path, str, dict[str, str]]:
    if not node:
        raise RuntimeError("Need Node.js 22.13 or newer to open the dashboard.")
    if pnpm:
        manager = pnpm
        command = [str(pnpm), "install", "--frozen-lockfile", "--ignore-scripts"]
        mode = "pnpm"
    elif npm:
        manager = npm
        command = [str(npm), "ci", "--ignore-scripts", "--no-audit", "--no-fund"]
        mode = "npm"
    else:
        raise RuntimeError("Need pnpm or npm to prepare the dashboard on first use.")

    env = build_env(node, manager)
    if not (SITE_ROOT / "node_modules").is_dir():
        print("Preparing the local dashboard for first use...", flush=True)
        subprocess.run(command, cwd=SITE_ROOT, env=env, check=True)
    return manager, mode, env


def export_data(project_root: Path) -> None:
    command = [
        sys.executable,
        str(SITE_ROOT / "scripts" / "export_dashboard_data.py"),
        "--project-root",
        str(project_root),
        "--site-root",
        str(SITE_ROOT),
    ]
    subprocess.run(command, cwd=SITE_ROOT, check=True)


def local_project_id(project_root: Path) -> str:
    import hashlib

    return hashlib.sha256(str(project_root.resolve()).encode("utf-8")).hexdigest()[:12]


def active_api_project(port: int) -> str | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload.get("projectId") or "") if payload.get("ok") else None
    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
        return None


def start_local_api(project_root: Path, port: int) -> subprocess.Popen[str] | None:
    active_project = active_api_project(port)
    expected_project = local_project_id(project_root)
    if active_project:
        if active_project != expected_project:
            raise RuntimeError(f"本机接口端口 {port} 已被另一个视频项目使用")
        return None

    process = subprocess.Popen(
        [
            sys.executable,
            str(SITE_ROOT / "scripts" / "local_api_server.py"),
            "--project-root",
            str(project_root),
            "--port",
            str(port),
        ],
        cwd=SITE_ROOT,
        text=True,
    )
    for _ in range(50):
        if process.poll() is not None:
            raise RuntimeError("本机视频接口启动失败")
        if active_api_project(port) == expected_project:
            return process
        time.sleep(0.1)
    process.terminate()
    raise RuntimeError("本机视频接口没有按时启动")


def stop_process(process: subprocess.Popen[str] | None) -> None:
    if not process or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def existing_server_url() -> str | None:
    lock_path = SITE_ROOT / ".vinext" / "dev" / "lock.json"
    if not lock_path.is_file():
        return None
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        pid = int(lock.get("pid"))
        port = int(lock.get("port"))
        hostname = str(lock.get("hostname") or "localhost")
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return None
        except PermissionError:
            pass
        return str(lock.get("appUrl") or f"http://{hostname}:{port}")
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--api-port", type=int, default=8765)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.expanduser().resolve()
    missing = [name for name in ("assets", "work") if not (project_root / name).is_dir()]
    if missing:
        raise RuntimeError(f"Project root is missing: {', '.join(missing)}")

    export_data(project_root)
    node, pnpm, npm = runtime_paths()
    manager, mode, env = prepare_dependencies(node, pnpm, npm)
    if args.prepare_only:
        print("Dashboard preparation complete.")
        return 0

    api_process = start_local_api(project_root, args.api_port)
    env["NEXT_PUBLIC_LOCAL_API_URL"] = f"http://127.0.0.1:{args.api_port}"
    try:
        active_url = existing_server_url()
        if active_url:
            print(f"Local: {active_url}/", flush=True)
            if api_process:
                return api_process.wait()
            return 0

        if mode == "pnpm":
            command = [str(manager), "run", "dev", "--", "--port", str(args.port)]
        else:
            command = [str(manager), "run", "dev", "--", "--port", str(args.port)]
        return subprocess.call(command, cwd=SITE_ROOT, env=env)
    finally:
        stop_process(api_process)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as error:
        print(f"Dashboard launch failed: {error}", file=sys.stderr)
        raise SystemExit(1)
