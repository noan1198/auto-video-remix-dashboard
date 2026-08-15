---
name: auto-video-remix-dashboard
description: Open and operate a local browser dashboard for an auto-video-remix project. Use when the user asks to open a webpage-style local video workspace, check whether a project supports viewing, benchmark dissection, or the full production toolkit, drag in a new reference video, create and dissect a dated task, inspect asset thumbnails and confirmed reuse counts, compare the benchmark with selected shots and output, review production stages, or browse prior remix tasks without uploading private media.
---

# Auto Video Remix Dashboard

Open a local webpage that reads the current project's `assets/`, `work/`, `final/`, asset catalog, and usage registry. The webpage can receive a benchmark video and begin the project's local intake and shot-dissection stages when the required project tools exist. Keep all source videos and task data on the user's computer.

This skill is a dashboard and benchmark-intake entry point. Installing it alone does not supply a user's media library, matching pipeline, TTS credentials, render tools, editor integration, or approval decisions. Never describe installation alone as a complete automatic remix system.

## Check capabilities first

Run:

```bash
python3 <skill-root>/scripts/check_project.py --project-root <absolute-project-root>
```

Use the result as the operating boundary:

- `dashboard-only`: open and inspect existing local data. Do not offer benchmark upload.
- `reference-intake`: allow benchmark upload and shot dissection. Stop at formal-script registration.
- `production-toolkit`: the expected project scripts are present, but each task still requires an authorized formal script, working voice configuration, visual review, and user confirmation.
- `not-ready`: report the missing project structure. Do not create folders or install production tools without the user's request.

## Open the dashboard

1. Read the current project's `AGENTS.md` before using project data.
2. Resolve the project root. Require `assets/` and `work/`; use the current working directory when both exist.
3. Run the capability check. Continue only within the reported level.
4. Run the bundled launcher in a retained terminal session:

   ```bash
   python3 <skill-root>/scripts/launch_dashboard.py --project-root <absolute-project-root>
   ```

5. Wait for the printed `Local:` URL. Open that exact URL in the Codex browser and keep the launcher session running.
6. When the user asks to refresh the page, rerun the export step or restart the launcher. Do not publish the local snapshot.

If frontend dependencies are missing, the launcher prepares them on first use. Ask for network approval when installation requires downloading packages. Do not claim the dashboard opened until the local server reports a URL.

## Create a task from a benchmark video

1. Require `referenceReady=true` from the capability check. If false, show the missing relative paths and stop before accepting a file.
2. Use the left-side `新建爆款任务` entry and drag in an MP4, MOV, or M4V file.
3. The local API must save the upload under a new `work/YYYY-MM-DD-<title>/` folder and normalize the reference copy to MP4 when required.
4. Create `task_config.json`, then run the project pipeline's `intake` stage.
5. Use the project's `tools/decompose_reference.py` to generate `recipe.json`, reference keyframes, and analysis audio, then run the pipeline's `dissect` stage.
6. Record the task as `waiting_for_script`. Reference audio, OCR, and ASR remain analysis material. Do not run `register_script`, matching, voice, render, validation, packaging, or usage confirmation until an authorized formal script is registered.
7. Refresh the browser snapshot and select the newly created task.

## Continue toward a finished video

Do not treat the dashboard button as the complete production pipeline. When the capability check reports `production-toolkit`, continue through the host project's rules and unified pipeline. A finished deliverable requires all of the following:

1. Register an authorized formal script and bind its hash in `content_manifest.json`.
2. Build or refresh the asset frame catalog, match each shot with precise source in/out ranges, and expose missing or low-confidence shots.
3. Generate the whole formal script as one continuous TTS request when production voice is requested.
4. Render from the real voice duration and selected source ranges.
5. Complete visual duplicate review, usage audit, editable-draft checks, project validation, and packaging.
6. Update confirmed usage counts only after the user accepts the finished video.

If any production dependency, credential, formal script, manual review, or user acceptance is missing, report the exact stopping point. Do not call the result a completed remix.

The dashboard upload API listens only on `127.0.0.1`. It must reject requests from non-local browser origins and must not move or modify files in `assets/`.

## Data shown

- Display one thumbnail per local video when a cached review frame exists.
- Read confirmed reuse counts from `asset_usage_registry.json`; candidates and unconfirmed previews remain uncounted.
- Mark counts 4 to 5 as near the reuse limit and counts 6 or higher as excluded from automatic recommendation.
- Display the reference video, selected-shot review board, rendered output, missing-shot count, canvas settings, and pipeline stages for each task.
- Display whether the current project supports dashboard viewing, benchmark intake, and the expected production-toolkit scripts.
- Treat a stage marked `passed` with `invalidated_by` as stale and show that it requires rechecking.
- Use paths only to locate local files. Do not expose absolute paths in the browser data.

Read [references/data-contract.md](references/data-contract.md) when adapting the dashboard to a different project layout or changing the exported JSON fields.

## Privacy and delivery rules

- Keep `public/dashboard-data.json` and `public/local-media/` untracked. They are generated from each user's computer.
- Commit only `public/dashboard-data.example.json` as the public demonstration dataset.
- Never read or copy `.env` into the dashboard.
- Never upload source videos, voice files, rendered outputs, usage history, or local paths to hosting services.
- Do not use cloud site hosting for this skill. GitHub distributes the program; the webpage runs on localhost.
- Preserve the project's asset library as read-only source material.
- Do not treat dragging in a benchmark as authorization to copy its wording, narration, music, or finished edit.

## Refresh data without opening the webpage

Run:

```bash
python3 <skill-root>/scripts/export_dashboard_data.py \
  --project-root <absolute-project-root> \
  --site-root <skill-root>
```

Report the exported asset and task counts. The snapshot is a local viewing index and does not alter production state.
