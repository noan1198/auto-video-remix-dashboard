"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type UsageStatus = "unused" | "used" | "near-limit" | "excluded";

type AssetRecord = {
  id: string;
  name: string;
  relativePath: string;
  collection: string;
  product: string;
  category: string;
  description: string;
  thumbnail: string | null;
  usageCount: number;
  usageStatus: UsageStatus;
  lastUsedAt: string | null;
  duration: number;
  width: number;
  height: number;
};

type StageRecord = {
  name: string;
  status: string;
  updatedAt: string | null;
};

type ProjectRecord = {
  id: string;
  folder: string;
  title: string;
  date: string;
  taskStatus?: string;
  reference: { name: string; poster: string | null };
  output: { exists: boolean; name: string; poster: string | null };
  reviewBoard: string | null;
  shotCount: number;
  matchedCount: number;
  missingCount: number;
  auditStatus: string;
  auditDecision: string;
  packageStatus: string;
  canvas: { orientation?: string; width?: number; height?: number; fps?: number };
  stages: StageRecord[];
};

type DashboardData = {
  schemaVersion: number;
  generatedAt: string;
  source: string;
  summary: {
    assetTotal: number;
    usedAssetTotal: number;
    nearLimitTotal: number;
    excludedTotal: number;
    projectTotal: number;
    outputTotal: number;
  };
  assets: AssetRecord[];
  projects: ProjectRecord[];
};

type UploadResult = {
  ok: boolean;
  projectId: string;
  folder: string;
  title: string;
  shots: number;
  duration: number;
  status: "waiting_for_script";
  error?: string;
};

type ProjectCapabilities = {
  schemaVersion: number;
  mode: "not-ready" | "dashboard-only" | "reference-intake" | "production-toolkit";
  viewerReady: boolean;
  referenceReady: boolean;
  productionToolkitPresent: boolean;
  assetCount: number;
  missing: {
    viewer: string[];
    reference: string[];
    productionToolkit: string[];
  };
  perTaskRequirements: string[];
};

const capabilityFeatures = [
  { number: "01", title: "导入对标爆款", detail: "拖入 MP4、MOV 或 M4V，在本机建立独立日期任务。" },
  { number: "02", title: "拆解镜头节奏", detail: "识别镜头边界、时长和关键帧，保留参考音轨供分析。" },
  { number: "03", title: "查看素材缩略图", detail: "按场景、动作、产品和文件名搜索自己的素材库。" },
  { number: "04", title: "管理素材复用", detail: "显示确认成片中的使用次数、冷却和复用上限。" },
  { number: "05", title: "一屏对照制作", detail: "同时查看对标视频、当前选片审核图和生成成片。" },
  { number: "06", title: "追踪生产状态", detail: "查看文案、匹配、配音、渲染、审核和交付阶段。" },
];

const localApiUrl = process.env.NEXT_PUBLIC_LOCAL_API_URL || "http://127.0.0.1:8765";

const stageLabels: Record<string, string> = {
  intake: "导入对标",
  preflight: "生产检查",
  dissect: "拆解镜头",
  register_script: "登记文案",
  match: "匹配素材",
  voice: "整篇配音",
  render: "生成成片",
  audit_visual: "视觉去重",
  audit_usage: "使用审核",
  build_draft: "可编辑草稿",
  validate: "最终验收",
  package: "整理交付",
};

const usageLabels: Record<UsageStatus | "all", string> = {
  all: "全部素材",
  unused: "未使用",
  used: "已使用",
  "near-limit": "接近上限",
  excluded: "已达上限",
};

function formatDate(value: string | null | undefined) {
  if (!value) return "暂无记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function statusText(status: string) {
  if (status === "passed" || status === "completed") return "已通过";
  if (status === "stale") return "需重新检查";
  if (status === "needs_review" || status === "pending") return "待审核";
  if (status === "failed") return "未通过";
  return status || "待处理";
}

function readinessClass(value: boolean | undefined) {
  if (value === undefined) return "checking";
  return value ? "ready" : "missing";
}

async function fetchDashboardData() {
  for (const source of ["/dashboard-data.json", "/dashboard-data.example.json"]) {
    try {
      const response = await fetch(source, { cache: "no-store" });
      if (!response.ok) continue;
      return (await response.json()) as DashboardData;
    } catch {
      continue;
    }
  }
  throw new Error("网页数据没有生成");
}

function uploadBenchmark(
  file: File,
  title: string,
  onProgress: (progress: number) => void,
): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const query = new URLSearchParams({ filename: file.name, title });
    const request = new XMLHttpRequest();
    request.open("POST", `${localApiUrl}/api/tasks?${query.toString()}`);
    request.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () => reject(new Error("本机视频接口没有启动，请重新打开这个 Skill"));
    request.onload = () => {
      let payload: UploadResult;
      try {
        payload = JSON.parse(request.responseText) as UploadResult;
      } catch {
        reject(new Error("本机视频接口返回了无法识别的结果"));
        return;
      }
      if (request.status >= 200 && request.status < 300 && payload.ok) resolve(payload);
      else reject(new Error(payload.error || "对标视频导入失败"));
    };
    request.send(file);
  });
}

function EmptyVisual({ label }: { label: string }) {
  return (
    <div className="empty-visual" aria-label={label}>
      <span className="empty-visual-mark" />
      <span>{label}</span>
    </div>
  );
}

function VisualCard({
  eyebrow,
  title,
  image,
  detail,
  tone,
}: {
  eyebrow: string;
  title: string;
  image: string | null;
  detail: string;
  tone: "yellow" | "blue" | "green";
}) {
  return (
    <article className={`visual-card visual-card-${tone}`}>
      <div className="visual-card-head">
        <span>{eyebrow}</span>
        <small>{detail}</small>
      </div>
      <div className="visual-frame">
        {image ? <img src={image} alt={title} loading="lazy" /> : <EmptyVisual label="待生成缩略图" />}
      </div>
      <h3>{title}</h3>
    </article>
  );
}

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loadingError, setLoadingError] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [query, setQuery] = useState("");
  const [usageFilter, setUsageFilter] = useState<UsageStatus | "all">("all");
  const [assetPage, setAssetPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [benchmarkFile, setBenchmarkFile] = useState<File | null>(null);
  const [taskTitle, setTaskTitle] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "analyzing" | "done" | "error">("idle");
  const [uploadMessage, setUploadMessage] = useState("");
  const [capabilities, setCapabilities] = useState<ProjectCapabilities | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    async function load() {
      try {
        const payload = await fetchDashboardData();
        setData(payload);
        setSelectedProjectId(payload.projects[0]?.id ?? "");
      } catch {
        setLoadingError(true);
      }
    }
    load();
    async function loadCapabilities() {
      try {
        const response = await fetch(`${localApiUrl}/api/health`, { cache: "no-store" });
        if (!response.ok) return;
        const payload = (await response.json()) as { capabilities?: ProjectCapabilities };
        if (payload.capabilities) setCapabilities(payload.capabilities);
      } catch {
        return;
      }
    }
    loadCapabilities();
  }, []);

  function chooseBenchmark(file: File | null) {
    if (!file) return;
    if (!/\.(mp4|mov|m4v)$/i.test(file.name)) {
      setUploadStatus("error");
      setUploadMessage("请选择 MP4、MOV 或 M4V 视频");
      return;
    }
    setBenchmarkFile(file);
    setTaskTitle((current) => current || file.name.replace(/\.[^.]+$/, ""));
    setUploadStatus("idle");
    setUploadMessage("");
  }

  async function createBenchmarkTask() {
    if (!benchmarkFile || capabilities?.referenceReady === false || uploadStatus === "uploading" || uploadStatus === "analyzing") return;
    setUploadStatus("uploading");
    setUploadProgress(0);
    setUploadMessage("正在把视频保存到新的本地任务文件夹");
    try {
      const result = await uploadBenchmark(benchmarkFile, taskTitle.trim(), (progress) => {
        setUploadProgress(progress);
        if (progress >= 100) {
          setUploadStatus("analyzing");
          setUploadMessage("视频已保存，正在拆解镜头和节奏");
        }
      });
      const payload = await fetchDashboardData();
      setData(payload);
      setSelectedProjectId(result.projectId);
      setUploadStatus("done");
      setUploadMessage(`已拆出 ${result.shots} 个镜头，下一步需要提供正式文案`);
    } catch (error) {
      setUploadStatus("error");
      setUploadMessage(error instanceof Error ? error.message : "对标视频导入失败");
    }
  }

  const selectedProject = useMemo(
    () => data?.projects.find((project) => project.id === selectedProjectId) ?? data?.projects[0] ?? null,
    [data, selectedProjectId],
  );

  const filteredAssets = useMemo(() => {
    if (!data) return [];
    const normalized = query.trim().toLowerCase();
    return data.assets.filter((asset) => {
      const statusMatches = usageFilter === "all" || asset.usageStatus === usageFilter;
      const queryMatches =
        !normalized ||
        [asset.name, asset.collection, asset.category, asset.description, asset.product]
          .join(" ")
          .toLowerCase()
          .includes(normalized);
      return statusMatches && queryMatches;
    });
  }, [data, query, usageFilter]);

  const visibleAssets = filteredAssets.slice(0, assetPage * 24);

  if (loadingError) {
    return <main className="load-state">网页数据没有生成，请先导出本地工作台数据。</main>;
  }

  if (!data || !selectedProject) {
    return <main className="load-state">正在读取素材库和视频任务……</main>;
  }

  const progress = selectedProject.shotCount
    ? Math.round((selectedProject.matchedCount / selectedProject.shotCount) * 100)
    : 0;
  const referenceReady = capabilities?.referenceReady === true;

  return (
    <main className="dashboard-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-glyph">M</span>
          <div>
            <strong>爆款素材工作台</strong>
            <small>Auto Video Remix</small>
          </div>
        </div>

        <button
          className="new-task-card"
          type="button"
          aria-label="新建爆款任务"
          onClick={() => {
            if (!referenceReady) {
              setUploadStatus("error");
              setUploadMessage(`当前项目还不能拆解视频，缺少：${capabilities?.missing.reference.join("、") || "本机生产工具"}`);
            }
            setCreateOpen(true);
          }}
        >
          <span className="new-task-plus">+</span>
          <span>
            <strong>新建爆款任务</strong>
            <small>拖入今天的对标视频</small>
          </span>
        </button>

        <nav className="side-nav" aria-label="工作台导航">
          <a className="active" href="#overview"><span>01</span>本次任务</a>
          <a href="#capabilities"><span>02</span>能做什么</a>
          <a href="#assets"><span>03</span>素材库</a>
          <a href="#projects"><span>04</span>历史成片</a>
        </nav>

        <div className="sidebar-note">
          <span className={`source-dot ${data.source === "demo" ? "demo" : ""}`} />
          <div>
            <strong>{data.source === "demo" ? "演示数据" : "本地数据已连接"}</strong>
            <small>更新于 {formatDate(data.generatedAt)}</small>
          </div>
        </div>
      </aside>

      <section className="dashboard-content">
        <header className="topbar" id="overview">
          <div>
            <p className="eyebrow">今天的视频生产</p>
            <h1>{selectedProject.title}</h1>
          </div>
          <div className="top-actions">
            <label className="project-select-label">
              <span>切换任务</span>
              <select value={selectedProject.id} onChange={(event) => setSelectedProjectId(event.target.value)}>
                {data.projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.date}  {project.title}
                  </option>
                ))}
              </select>
            </label>
            <button className="primary-button" type="button" onClick={() => document.querySelector("#workflow")?.scrollIntoView({ behavior: "smooth" })}>
              查看制作进度
            </button>
          </div>
        </header>

        <section className="summary-grid" aria-label="素材库统计">
          <article>
            <span>素材总数</span>
            <strong>{data.summary.assetTotal}</strong>
            <small>{data.summary.usedAssetTotal} 条进入过成片</small>
          </article>
          <article>
            <span>接近复用上限</span>
            <strong>{data.summary.nearLimitTotal}</strong>
            <small>第 4 至 5 次使用会降低排名</small>
          </article>
          <article>
            <span>已生成成片</span>
            <strong>{data.summary.outputTotal}</strong>
            <small>共 {data.summary.projectTotal} 个视频任务</small>
          </article>
          <article className="accent-stat">
            <span>本次素材匹配</span>
            <strong>{selectedProject.matchedCount}/{selectedProject.shotCount}</strong>
            <small>{progress}% 镜头已找到素材</small>
          </article>
        </section>

        <section className="capability-section" id="capabilities">
          <div className="section-heading capability-heading">
            <div>
              <p className="eyebrow">这个工作台能做什么</p>
              <h2>把对标、素材、选片和成片放在一套本机流程里</h2>
            </div>
            <p>网页负责看清任务和启动对标拆解，完整成片仍按正式文案、素材匹配、整篇配音和审核流程继续生产。</p>
          </div>

          <div className="capability-grid">
            {capabilityFeatures.map((feature) => (
              <article key={feature.number}>
                <span>{feature.number}</span>
                <h3>{feature.title}</h3>
                <p>{feature.detail}</p>
              </article>
            ))}
          </div>

          <div className="readiness-panel">
            <div>
              <p className="eyebrow">当前电脑安装检查</p>
              <h3>网页能打开，不代表已经具备完整自动剪辑条件</h3>
              <p>生产工具齐全后，每条视频仍需要正式文案、可用配音配置和人工视觉审核。</p>
            </div>
            <div className="readiness-list" aria-label="当前项目能力">
              <span className={readinessClass(capabilities?.viewerReady)}>
                <i />网页查看素材与任务
              </span>
              <span className={readinessClass(capabilities?.referenceReady)}>
                <i />导入并拆解对标视频
              </span>
              <span className={readinessClass(capabilities?.productionToolkitPresent)}>
                <i />完整生产工具脚本
              </span>
            </div>
          </div>
        </section>

        <section className="project-stage" id="workflow">
          <div className="section-heading">
            <div>
              <p className="eyebrow">从对标到成片</p>
              <h2>本次视频一屏对照</h2>
            </div>
            <div className="project-facts">
              <span>{selectedProject.canvas.width || "?"}×{selectedProject.canvas.height || "?"}</span>
              <span>{selectedProject.canvas.fps || "?"} FPS</span>
              {selectedProject.taskStatus === "waiting_for_script" && (
                <span className="status-chip status-script">待提供正式文案</span>
              )}
              <span className={`status-chip status-${selectedProject.auditDecision}`}>
                视觉审核 {statusText(selectedProject.auditDecision)}
              </span>
            </div>
          </div>

          <div className="visual-comparison">
            <VisualCard
              eyebrow="对标爆款"
              title={selectedProject.reference.name}
              image={selectedProject.reference.poster}
              detail="只参考镜头结构与节奏"
              tone="yellow"
            />
            <VisualCard
              eyebrow="本次选片"
              title={`${selectedProject.matchedCount} 个镜头已匹配`}
              image={selectedProject.reviewBoard}
              detail={`${selectedProject.missingCount} 个缺口`}
              tone="blue"
            />
            <VisualCard
              eyebrow="生成成片"
              title={selectedProject.output.name}
              image={selectedProject.output.poster}
              detail={selectedProject.output.exists ? "已生成本地成片" : "等待生成"}
              tone="green"
            />
          </div>

          <div className="stage-strip" aria-label="视频生产流程">
            {selectedProject.stages.map((stage, index) => (
              <div className={`stage-item stage-${stage.status}`} key={stage.name}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{stageLabels[stage.name] || stage.name}</strong>
                  <small>
                    {stage.name === "register_script" && stage.status === "pending" && selectedProject.taskStatus === "waiting_for_script"
                      ? "待提供正式文案"
                      : statusText(stage.status)}
                  </small>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="asset-section" id="assets">
          <div className="section-heading asset-heading">
            <div>
              <p className="eyebrow">素材库</p>
              <h2>看画面，也看它已经用了几次</h2>
            </div>
            <label className="search-field">
              <span className="visually-hidden">搜索素材</span>
              <span className="search-icon" />
              <input
                type="search"
                placeholder="搜索场景、动作、产品或文件名"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setAssetPage(1);
                }}
              />
            </label>
          </div>

          <div className="filter-row" role="group" aria-label="按素材使用次数筛选">
            {(Object.keys(usageLabels) as Array<UsageStatus | "all">).map((status) => (
              <button
                className={usageFilter === status ? "active" : ""}
                key={status}
                type="button"
                onClick={() => {
                  setUsageFilter(status);
                  setAssetPage(1);
                }}
              >
                {usageLabels[status]}
              </button>
            ))}
            <span>{filteredAssets.length} 条结果</span>
          </div>

          <div className="asset-grid">
            {visibleAssets.map((asset) => (
              <article className="asset-card" key={asset.id}>
                <div className="asset-image">
                  {asset.thumbnail ? <img src={asset.thumbnail} alt={asset.description} loading="lazy" /> : <EmptyVisual label="待生成缩略图" />}
                  <span className={`usage-badge usage-${asset.usageStatus}`}>
                    {asset.usageCount === 0 ? "还没用过" : `已用 ${asset.usageCount} 次`}
                  </span>
                  {asset.duration > 0 && <span className="duration-badge">{asset.duration.toFixed(1)}s</span>}
                </div>
                <div className="asset-body">
                  <div className="asset-meta">
                    <span>{asset.category}</span>
                    <small>{asset.collection}</small>
                  </div>
                  <h3>{asset.description}</h3>
                  <p title={asset.name}>{asset.name}</p>
                  <div className="usage-meter" aria-label={`素材已使用 ${asset.usageCount} 次`}>
                    {Array.from({ length: 6 }).map((_, index) => (
                      <span className={index < asset.usageCount ? "filled" : ""} key={index} />
                    ))}
                  </div>
                </div>
              </article>
            ))}
          </div>

          {visibleAssets.length < filteredAssets.length && (
            <button className="load-more" type="button" onClick={() => setAssetPage((value) => value + 1)}>
              再显示 24 条素材
            </button>
          )}
        </section>

        <section className="history-section" id="projects">
          <div className="section-heading">
            <div>
              <p className="eyebrow">历史任务</p>
              <h2>每条成片都能追回对标和选片</h2>
            </div>
          </div>
          <div className="history-list">
            {data.projects.slice(0, 12).map((project) => (
              <button
                className={project.id === selectedProject.id ? "active" : ""}
                key={project.id}
                type="button"
                onClick={() => {
                  setSelectedProjectId(project.id);
                  document.querySelector("#overview")?.scrollIntoView({ behavior: "smooth" });
                }}
              >
                <span>{project.date}</span>
                <strong>{project.title}</strong>
                <small>{project.matchedCount}/{project.shotCount} 镜头</small>
                <em>{project.output.exists ? "有成片" : "制作中"}</em>
              </button>
            ))}
          </div>
        </section>
      </section>

      {createOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="create-modal" role="dialog" aria-modal="true" aria-labelledby="create-task-title">
            <div className="create-modal-head">
              <div>
                <p className="eyebrow">新的对标爆款</p>
                <h2 id="create-task-title">拖入视频，建立今天的任务</h2>
              </div>
              <button
                className="modal-close"
                type="button"
                aria-label="关闭"
                disabled={uploadStatus === "uploading" || uploadStatus === "analyzing"}
                onClick={() => setCreateOpen(false)}
              >
                ×
              </button>
            </div>

            <button
              className={`drop-zone ${dragActive ? "active" : ""} ${benchmarkFile ? "has-file" : ""}`}
              type="button"
              onClick={() => fileInputRef.current?.click()}
              onDragEnter={(event) => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={() => setDragActive(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragActive(false);
                chooseBenchmark(event.dataTransfer.files[0] || null);
              }}
            >
              <span className="drop-icon">{benchmarkFile ? "✓" : "+"}</span>
              <strong>{benchmarkFile ? benchmarkFile.name : "把爆款视频拖到这里"}</strong>
              <small>
                {benchmarkFile
                  ? `${(benchmarkFile.size / 1024 / 1024).toFixed(1)} MB，点击可以重新选择`
                  : "也可以点击选择 MP4、MOV 或 M4V 视频"}
              </small>
            </button>
            <input
              ref={fileInputRef}
              className="hidden-file-input"
              type="file"
              accept="video/mp4,video/quicktime,.m4v"
              onChange={(event) => chooseBenchmark(event.target.files?.[0] || null)}
            />

            <label className="task-title-field">
              <span>任务名称</span>
              <input
                type="text"
                maxLength={80}
                placeholder="例如：今天的车载收纳爆款"
                value={taskTitle}
                onChange={(event) => setTaskTitle(event.target.value)}
              />
            </label>

            <div className="reference-rule">
              <strong>这一步只分析镜头结构和节奏</strong>
              <span>参考视频的原文、原声不会直接用于新成片。拆解完成后，任务会停在“待提供正式文案”。</span>
            </div>

            {!referenceReady && (
              <div className="missing-tools-note">
                <strong>当前项目还不能创建对标任务</strong>
                <span>缺少：{capabilities?.missing.reference.join("、") || "本机视频拆解工具"}</span>
              </div>
            )}

            {(uploadStatus === "uploading" || uploadStatus === "analyzing") && (
              <div className="upload-progress" aria-live="polite">
                <div><span style={{ width: `${uploadStatus === "analyzing" ? 100 : uploadProgress}%` }} /></div>
                <small>{uploadMessage}</small>
              </div>
            )}

            {(uploadStatus === "done" || uploadStatus === "error") && (
              <p className={`upload-result ${uploadStatus}`} aria-live="polite">{uploadMessage}</p>
            )}

            <div className="create-modal-actions">
              <button
                className="secondary-button"
                type="button"
                disabled={uploadStatus === "uploading" || uploadStatus === "analyzing"}
                onClick={() => setCreateOpen(false)}
              >
                {uploadStatus === "done" ? "查看新任务" : "取消"}
              </button>
              <button
                className="primary-button"
                type="button"
                disabled={!benchmarkFile || !referenceReady || uploadStatus === "uploading" || uploadStatus === "analyzing" || uploadStatus === "done"}
                onClick={createBenchmarkTask}
              >
                {uploadStatus === "uploading" ? `正在上传 ${uploadProgress}%` : uploadStatus === "analyzing" ? "正在拆解视频" : "创建并开始拆解"}
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
