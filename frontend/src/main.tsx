import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Captions, FolderSearch, Play, RefreshCw, Save, Settings, Wand2 } from "lucide-react";

import {
  createProject,
  listMedia,
  listProjects,
  listSubtitles,
  scanProject,
  type MediaItem,
  type Project,
  type SubtitleSegment
} from "./api/client";
import "./styles/app.css";

function formatDuration(ms: number | null): string {
  if (ms === null) return "--:--";
  const seconds = Math.floor(ms / 1000);
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return h > 0
    ? `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
    : `${m}:${s.toString().padStart(2, "0")}`;
}

function formatTimestamp(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const millis = ms % 1000;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s
    .toString()
    .padStart(2, "0")}.${millis.toString().padStart(3, "0")}`;
}

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const [activeMedia, setActiveMedia] = useState<MediaItem | null>(null);
  const [subtitles, setSubtitles] = useState<SubtitleSegment[]>([]);
  const [projectName, setProjectName] = useState("本地字幕项目");
  const [mediaRoot, setMediaRoot] = useState("");
  const [logLines, setLogLines] = useState<string[]>(["等待连接后端。"]);
  const [busy, setBusy] = useState(false);

  const selectedSubtitle = useMemo(() => subtitles[0], [subtitles]);

  function appendLog(line: string) {
    setLogLines((current) => [line, ...current].slice(0, 10));
  }

  async function refreshProjects() {
    const nextProjects = await listProjects();
    setProjects(nextProjects);
    setActiveProject((current) => current ?? nextProjects[0] ?? null);
  }

  async function refreshMedia(project: Project) {
    const nextMedia = await listMedia(project.id);
    setMediaItems(nextMedia);
    setActiveMedia((current) => current ?? nextMedia[0] ?? null);
  }

  useEffect(() => {
    refreshProjects()
      .then(() => appendLog("后端连接成功。"))
      .catch((error) => appendLog(`后端连接失败：${error.message}`));
  }, []);

  useEffect(() => {
    if (!activeProject) return;
    refreshMedia(activeProject).catch((error) => appendLog(`读取媒体列表失败：${error.message}`));
  }, [activeProject?.id]);

  useEffect(() => {
    if (!activeMedia) {
      setSubtitles([]);
      return;
    }
    listSubtitles(activeMedia.id)
      .then(setSubtitles)
      .catch((error) => appendLog(`读取字幕失败：${error.message}`));
  }, [activeMedia?.id]);

  async function handleCreateProject() {
    if (!mediaRoot.trim()) {
      appendLog("请先输入视频文件夹路径。");
      return;
    }

    setBusy(true);
    try {
      const project = await createProject({
        name: projectName.trim() || "本地字幕项目",
        media_root: mediaRoot.trim(),
        output_mode: "beside_video"
      });
      setProjects((current) => [project, ...current]);
      setActiveProject(project);
      appendLog(`已创建项目：${project.name}`);
    } catch (error) {
      appendLog(`创建项目失败：${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleScan() {
    if (!activeProject) return;
    setBusy(true);
    try {
      const result = await scanProject(activeProject.id);
      appendLog(
        `扫描完成：发现 ${result.found}，新增 ${result.created}，更新 ${result.updated}，跳过 ${result.skipped}。`
      );
      await refreshMedia(activeProject);
    } catch (error) {
      appendLog(`扫描失败：${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="workspace">
      <aside className="sidebar">
        <div className="brand">
          <Captions size={26} />
          <div>
            <strong>Voice2Subtitle</strong>
            <span>Local workstation</span>
          </div>
        </div>

        <section className="panel project-form">
          <label>
            项目名
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} />
          </label>
          <label>
            视频文件夹路径
            <input
              value={mediaRoot}
              onChange={(event) => setMediaRoot(event.target.value)}
              placeholder="E:\\temp\\测试翻译"
            />
          </label>
          <button className="primary" disabled={busy} onClick={handleCreateProject}>
            <FolderSearch size={16} />
            创建项目
          </button>
        </section>

        <section className="panel">
          <div className="panel-title">
            <span>项目</span>
            <button className="icon-button" title="刷新项目" onClick={refreshProjects}>
              <RefreshCw size={16} />
            </button>
          </div>
          <div className="project-list">
            {projects.map((project) => (
              <button
                className={project.id === activeProject?.id ? "selected" : ""}
                key={project.id}
                onClick={() => {
                  setActiveProject(project);
                  setActiveMedia(null);
                }}
              >
                <strong>{project.name}</strong>
                <span>{project.media_root}</span>
              </button>
            ))}
          </div>
        </section>
      </aside>

      <section className="media-column">
        <div className="toolbar">
          <div>
            <span className="eyebrow">Media Queue</span>
            <h1>{activeProject?.name ?? "未选择项目"}</h1>
          </div>
          <div className="actions">
            <button disabled={!activeProject || busy} onClick={handleScan}>
              <RefreshCw size={16} />
              扫描
            </button>
            <button disabled>
              <Wand2 size={16} />
              处理
            </button>
            <button disabled>
              <Save size={16} />
              导出
            </button>
          </div>
        </div>

        <div className="media-list">
          {mediaItems.map((item) => (
            <button
              className={item.id === activeMedia?.id ? "media-row active" : "media-row"}
              key={item.id}
              onClick={() => setActiveMedia(item)}
            >
              <span className={`status-dot ${item.status}`} />
              <span className="file-name">{item.file_name}</span>
              <span>{formatDuration(item.duration_ms)}</span>
              <span>{item.status}</span>
              <span>{item.subtitle_path ? "SRT" : "No subtitle"}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="review-column">
        <div className="player-shell">
          <div className="video-placeholder">
            <Play size={42} />
            <span>{activeMedia?.file_name ?? "选择一个视频后开始预览"}</span>
          </div>
          <div className="subtitle-overlay">
            {selectedSubtitle
              ? selectedSubtitle.edited_text || selectedSubtitle.translated_text || selectedSubtitle.source_text
              : "字幕预览将在这里显示"}
          </div>
        </div>

        <div className="editor-panel">
          <div className="panel-title">
            <span>字幕段</span>
            <button className="icon-button" title="设置">
              <Settings size={16} />
            </button>
          </div>
          <div className="subtitle-table">
            <div className="subtitle-head">
              <span>#</span>
              <span>开始</span>
              <span>结束</span>
              <span>文本</span>
            </div>
            {subtitles.length === 0 ? (
              <div className="empty-state">还没有字幕段。后续处理完成后会显示原文和译文。</div>
            ) : (
              subtitles.map((segment) => (
                <div className="subtitle-row" key={segment.id}>
                  <span>{segment.index_no}</span>
                  <span>{formatTimestamp(segment.start_ms)}</span>
                  <span>{formatTimestamp(segment.end_ms)}</span>
                  <span>{segment.edited_text || segment.translated_text || segment.source_text}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="log-panel">
          {logLines.map((line, index) => (
            <div key={`${line}-${index}`}>{line}</div>
          ))}
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
