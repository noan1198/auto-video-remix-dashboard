---
name: auto-video-remix-dashboard
description: Open and operate a local browser dashboard for an auto-video-remix project. Use when the user asks to open a webpage-style skill for local video production, drag in a new reference or benchmark video, create and dissect a dated remix task, inspect asset thumbnails and confirmed reuse counts, compare the benchmark with selected shots and the rendered output, review project stages, or browse prior remix tasks without uploading private media to a cloud service.
---

# Auto Video Remix Dashboard

Open a local webpage that reads the current project's `assets/`, `work/`, `final/`, asset catalog, and usage registry. The webpage can also receive a benchmark video and begin the project's local intake and shot-dissection stages. Keep all source videos and task data on the user's computer.

## Open the dashboard

1. Read the current project's `AGENTS.md` before using project data.
2. Resolve the project root. Require `assets/` and `work/`; use the current working directory when both exist.
3. Run the bundled launcher in a retained terminal session:

   ```bash
   python3 <skill-root>/scripts/launch_dashboard.py --project-root <absolute-project-root>
   ```

4. Wait for the printed `Local:` URL. Open that exact URL in the Codex browser and keep the launcher session running.
5. When the user asks to refresh the page, rerun the export step or restart the launcher. Do not publish the local snapshot.

If frontend dependencies are missing, the launcher prepares them on first use. Ask for network approval when installation requires downloading packages. Do not claim the dashboard opened until the local server reports a URL.

## Create a task from a benchmark video

1. Use the left-side `新建爆款任务` entry and drag in an MP4, MOV, or M4V file.
2. The local API must save the upload under a new `work/YYYY-MM-DD-<title>/` folder and normalize the reference copy to MP4 when required.
3. Create `task_config.json`, then run the project pipeline's `intake` stage.
4. Use the project's `tools/decompose_reference.py` to generate `recipe.json`, reference keyframes, and analysis audio, then run the pipeline's `dissect` stage.
5. Record the task as `waiting_for_script`. Reference audio, OCR, and ASR remain analysis material. Do not run `register_script`, matching, voice, render, validation, packaging, or usage confirmation until an authorized formal script is registered.
6. Refresh the browser snapshot and select the newly created task.

The dashboard upload API listens only on `127.0.0.1`. It must reject requests from non-local browser origins and must not move or modify files in `assets/`.

## Data shown

- Display one thumbnail per local video when a cached review frame exists.
- Read confirmed reuse counts from `asset_usage_registry.json`; candidates and unconfirmed previews remain uncounted.
- Mark counts 4 to 5 as near the reuse limit and counts 6 or higher as excluded from automatic recommendation.
- Display the reference video, selected-shot review board, rendered output, missing-shot count, canvas settings, and pipeline stages for each task.
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
