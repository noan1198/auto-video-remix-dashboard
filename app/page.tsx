"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Health = {
  ok: boolean;
  capabilities?: { referenceReady: boolean; assetCount: number };
};

type Shot = {
  index: number;
  start: number;
  end: number;
  duration: number;
  keyframePath: string;
  clipPath: string | null;
};

type Storyboard = {
  ok: boolean;
  folder: string;
  title: string;
  duration: number;
  width: number;
  height: number;
  fps: number;
  referencePath: string;
  shots: Shot[];
};

type UploadResult = {
  ok: boolean;
  folder: string;
  title: string;
  shots: number;
  duration: number;
  error?: string;
};

const localApiUrl = process.env.NEXT_PUBLIC_LOCAL_API_URL || "http://127.0.0.1:8765";

function formatSeconds(value: number) {
  return `${value.toFixed(2)}s`;
}

function mediaUrl(folder: string, path: string | null) {
  if (!path) return "";
  const query = new URLSearchParams({ folder, path });
  return `${localApiUrl}/api/media?${query.toString()}`;
}

async function loadStoryboard(folder: string) {
  const response = await fetch(`${localApiUrl}/api/storyboard?folder=${encodeURIComponent(folder)}`, {
    cache: "no-store",
  });
  const payload = (await response.json()) as Storyboard & { error?: string };
  if (!response.ok || !payload.ok) throw new Error(payload.error || "分镜数据读取失败");
  return payload;
}

function uploadVideo(file: File, title: string, onProgress: (value: number) => void) {
  return new Promise<UploadResult>((resolve, reject) => {
    const query = new URLSearchParams({ filename: file.name, title });
    const request = new XMLHttpRequest();
    request.open("POST", `${localApiUrl}/api/tasks?${query.toString()}`);
    request.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () => reject(new Error("本地拆解服务没有启动"));
    request.onload = () => {
      try {
        const payload = JSON.parse(request.responseText) as UploadResult;
        if (request.status >= 200 && request.status < 300 && payload.ok) resolve(payload);
        else reject(new Error(payload.error || "视频拆解失败"));
      } catch {
        reject(new Error("本地拆解服务返回了无法识别的内容"));
      }
    };
    request.send(file);
  });
}

function CompositionGrid({ visible }: { visible: boolean }) {
  return (
    <div className={`composition-grid ${visible ? "visible" : ""}`} aria-hidden="true">
      <span className="grid-line vertical first" />
      <span className="grid-line vertical second" />
      <span className="grid-line horizontal first" />
      <span className="grid-line horizontal second" />
    </div>
  );
}

export default function Home() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [serviceReady, setServiceReady] = useState<boolean | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<"idle" | "uploading" | "analyzing" | "done" | "error">("idle");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("选择一条爆款视频，系统会识别每一次镜头切换");
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [page, setPage] = useState(1);
  const [selectedShot, setSelectedShot] = useState<Shot | null>(null);
  const [compositionGridVisible, setCompositionGridVisible] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function initialize() {
      try {
        const response = await fetch(`${localApiUrl}/api/health`, { cache: "no-store" });
        const payload = (await response.json()) as Health;
        if (!cancelled) setServiceReady(Boolean(response.ok && payload.ok && payload.capabilities?.referenceReady));
      } catch {
        if (!cancelled) setServiceReady(false);
        return;
      }

      try {
        const response = await fetch(`${localApiUrl}/api/storyboard/latest`, { cache: "no-store" });
        if (!response.ok) return;
        const payload = (await response.json()) as Storyboard;
        if (!cancelled) {
          setStoryboard(payload);
          setMessage(`最近一次任务识别出 ${payload.shots.length} 个镜头`);
        }
      } catch {
        return;
      }
    }
    initialize();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function selectFile(nextFile: File | null) {
    if (!nextFile) return;
    if (!/\.(mp4|mov|m4v)$/i.test(nextFile.name)) {
      setPhase("error");
      setMessage("请选择 MP4、MOV 或 M4V 视频");
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(nextFile);
    setPreviewUrl(URL.createObjectURL(nextFile));
    setTaskTitle(nextFile.name.replace(/\.[^.]+$/, ""));
    setPhase("idle");
    setProgress(0);
    setMessage("视频已经准备好，点击开始拆解");
  }

  async function startSplit() {
    if (!file || !serviceReady || phase === "uploading" || phase === "analyzing") return;
    setPhase("uploading");
    setProgress(0);
    setMessage("正在把视频送入本地拆解任务");
    try {
      const result = await uploadVideo(file, taskTitle.trim(), (value) => {
        setProgress(value);
        if (value >= 100) {
          setPhase("analyzing");
          setMessage("视频已导入，正在识别镜头切点并生成分段视频");
        }
      });
      const payload = await loadStoryboard(result.folder);
      setStoryboard(payload);
      setPage(1);
      setSelectedShot(null);
      setPhase("done");
      setMessage(`拆解完成，共识别 ${payload.shots.length} 个镜头`);
    } catch (error) {
      setPhase("error");
      setMessage(error instanceof Error ? error.message : "视频拆解失败");
    }
  }

  const pageCount = Math.max(1, Math.ceil((storyboard?.shots.length || 0) / 9));
  const visibleShots = useMemo(
    () => storyboard?.shots.slice((page - 1) * 9, page * 9) || [],
    [storyboard, page],
  );
  const averageDuration = storyboard?.shots.length
    ? storyboard.shots.reduce((sum, shot) => sum + shot.duration, 0) / storyboard.shots.length
    : 0;

  return (
    <main className="splitter-page">
      <header className="site-header">
        <div className="brand-mark">CUT</div>
        <div className="brand-copy">
          <strong>爆款视频拆镜头</strong>
          <span>本地运行，视频保留在你的电脑中</span>
        </div>
        <div className={`service-state ${serviceReady ? "ready" : serviceReady === false ? "offline" : "checking"}`}>
          <i />
          {serviceReady ? "拆解服务已连接" : serviceReady === false ? "拆解服务未启动" : "正在连接拆解服务"}
        </div>
      </header>

      <section className="hero">
        <div>
          <p className="hero-kicker">SHOT DETECTION</p>
          <h1>把一条爆款视频<br />拆成完整分镜九宫格</h1>
        </div>
        <p className="hero-note">自动识别每一次画面切换，生成镜头编号、时间范围、关键帧和独立视频片段。</p>
      </section>

      <section className="workbench">
        <div
          className={`upload-panel ${dragging ? "dragging" : ""} ${file ? "has-file" : ""}`}
          onDragEnter={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            selectFile(event.dataTransfer.files[0] || null);
          }}
        >
          <div className="step-label"><span>01</span>导入爆款视频</div>
          <button className="drop-button" type="button" onClick={() => inputRef.current?.click()}>
            <span className="drop-symbol">{file ? "✓" : "+"}</span>
            <strong>{file ? file.name : "把视频拖到这里"}</strong>
            <small>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB，点击可以重新选择` : "支持 MP4、MOV 和 M4V"}</small>
          </button>
          <input
            ref={inputRef}
            className="hidden-input"
            type="file"
            accept="video/mp4,video/quicktime,.m4v"
            onChange={(event) => selectFile(event.target.files?.[0] || null)}
          />
          <label className="title-field">
            <span>任务名称</span>
            <input value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} placeholder="输入这条视频的名称" />
          </label>
          <button
            className="split-button"
            type="button"
            disabled={!file || !serviceReady || phase === "uploading" || phase === "analyzing"}
            onClick={startSplit}
          >
            {phase === "uploading" ? `正在导入 ${progress}%` : phase === "analyzing" ? "正在拆解镜头" : "开始拆解视频"}
          </button>
          <div className={`process-message ${phase}`}>
            <div className="progress-track">
              <span style={{ width: `${phase === "analyzing" || phase === "done" ? 100 : progress}%` }} />
            </div>
            <p>{message}</p>
          </div>
        </div>

        <div className="preview-panel">
          <div className="step-label"><span>02</span>原视频预览</div>
          <div className="video-frame">
            {previewUrl ? (
              // Source previews do not have a separate caption file.
              // eslint-disable-next-line jsx-a11y/media-has-caption
              <video src={previewUrl} controls playsInline />
            ) : storyboard?.referencePath ? (
              // Source previews do not have a separate caption file.
              // eslint-disable-next-line jsx-a11y/media-has-caption
              <video src={mediaUrl(storyboard.folder, storyboard.referencePath)} controls playsInline />
            ) : (
              <div className="video-empty"><span>等待视频</span></div>
            )}
          </div>
          <div className="preview-caption">
            <strong>{file?.name || storyboard?.title || "还没有选择视频"}</strong>
            <span>{storyboard ? `${formatSeconds(storyboard.duration)} · ${storyboard.width}×${storyboard.height}` : "选择视频后会在这里播放"}</span>
          </div>
        </div>
      </section>

      <section className="storyboard-section">
        <div className="storyboard-heading">
          <div>
            <div className="step-label"><span>03</span>分镜九宫格</div>
            <h2>{storyboard ? `共识别 ${storyboard.shots.length} 个镜头` : "等待生成分镜"}</h2>
          </div>
          {storyboard && (
            <div className="storyboard-actions">
              <button
                className={`composition-toggle ${compositionGridVisible ? "active" : ""}`}
                type="button"
                aria-pressed={compositionGridVisible}
                onClick={() => setCompositionGridVisible((value) => !value)}
              >
                <span className="toggle-grid-icon" aria-hidden="true" />
                构图九宫格 {compositionGridVisible ? "已显示" : "已隐藏"}
              </button>
              <div className="result-stats">
                <span><small>视频时长</small>{formatSeconds(storyboard.duration)}</span>
                <span><small>镜头数量</small>{storyboard.shots.length}</span>
                <span><small>平均镜头</small>{formatSeconds(averageDuration)}</span>
              </div>
            </div>
          )}
        </div>

        <div className={`shot-grid ${visibleShots.length ? "has-results" : ""}`}>
          {visibleShots.length
            ? visibleShots.map((shot) => (
                <button className="shot-card" type="button" key={shot.index} onClick={() => setSelectedShot(shot)}>
                  <div className="shot-image">
                    <img src={mediaUrl(storyboard!.folder, shot.keyframePath)} alt={`镜头 ${shot.index} 关键帧`} />
                    <CompositionGrid visible={compositionGridVisible} />
                    <span className="shot-number">{String(shot.index).padStart(2, "0")}</span>
                    <span className="shot-play">▶</span>
                  </div>
                  <div className="shot-meta">
                    <strong>镜头 {String(shot.index).padStart(2, "0")}</strong>
                    <span>{formatSeconds(shot.start)} → {formatSeconds(shot.end)}</span>
                    <em>{formatSeconds(shot.duration)}</em>
                  </div>
                </button>
              ))
            : Array.from({ length: 9 }).map((_, index) => (
                <div className="shot-placeholder" key={index}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                </div>
              ))}
        </div>

        {storyboard && pageCount > 1 && (
          <div className="pagination">
            <button type="button" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>上一组</button>
            <span>第 {page} 组，共 {pageCount} 组</span>
            <button type="button" disabled={page === pageCount} onClick={() => setPage((value) => value + 1)}>下一组</button>
          </div>
        )}
      </section>

      {selectedShot && storyboard && (
        <div
          className="shot-dialog-backdrop"
          role="presentation"
          onClick={(event) => {
            if (event.target === event.currentTarget) setSelectedShot(null);
          }}
        >
          <section className="shot-dialog" role="dialog" aria-modal="true">
            <button
              className={`dialog-grid-toggle ${compositionGridVisible ? "active" : ""}`}
              type="button"
              aria-pressed={compositionGridVisible}
              onClick={() => setCompositionGridVisible((value) => !value)}
            >
              构图九宫格 {compositionGridVisible ? "开" : "关"}
            </button>
            <button className="dialog-close" type="button" aria-label="关闭" onClick={() => setSelectedShot(null)}>×</button>
            <div className="dialog-video">
              {selectedShot.clipPath ? (
                // Reference clips do not have a separate caption file.
                // eslint-disable-next-line jsx-a11y/media-has-caption
                <video src={mediaUrl(storyboard.folder, selectedShot.clipPath)} controls autoPlay playsInline />
              ) : (
                <img src={mediaUrl(storyboard.folder, selectedShot.keyframePath)} alt={`镜头 ${selectedShot.index}`} />
              )}
              <CompositionGrid visible={compositionGridVisible} />
            </div>
            <div className="dialog-copy">
              <span>镜头 {String(selectedShot.index).padStart(2, "0")}</span>
              <strong>{formatSeconds(selectedShot.start)} 到 {formatSeconds(selectedShot.end)}</strong>
              <small>持续 {formatSeconds(selectedShot.duration)}</small>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
