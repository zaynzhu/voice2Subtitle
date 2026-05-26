import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Captions, FolderSearch, Play, RefreshCw, Save, Settings, Wand2, Cpu, Trash2 } from "lucide-react";

import {
  createProject,
  exportMedia,
  listMedia,
  listProjects,
  listSubtitles,
  processMedia,
  scanProject,
  updateSubtitle,
  unloadGpuMemory,
  browseDirectory,
  deleteProject,
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
  const [selectedSubtitleId, setSelectedSubtitleId] = useState<number | null>(null);
  const [editSourceText, setEditSourceText] = useState("");
  const [editTranslatedText, setEditTranslatedText] = useState("");
  const [editEditedText, setEditEditedText] = useState("");
  const [editStartMs, setEditStartMs] = useState("0");
  const [editEndMs, setEditEndMs] = useState("0");
  const [projectName, setProjectName] = useState("本地字幕项目");
  const [mediaRoot, setMediaRoot] = useState("");
  const [logLines, setLogLines] = useState<string[]>(["等待连接后端。"]);
  const [busy, setBusy] = useState(false);

  const [toasts, setToasts] = useState<{ id: string; message: string; type: "success" | "error" | "info" }[]>([]);

  function showToast(message: string, type: "success" | "error" | "info" = "info") {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((current) => [...current, { id, message, type }]);
    setTimeout(() => {
      setToasts((current) => current.filter((t) => t.id !== id));
    }, 3500);
  }

  const [deletingProjectId, setDeletingProjectId] = useState<number | null>(null);

  const selectedSubtitle = useMemo(
    () => subtitles.find((segment) => segment.id === selectedSubtitleId) ?? subtitles[0] ?? null,
    [subtitles, selectedSubtitleId]
  );

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
      .then(() => {
        appendLog("后端连接成功。");
        showToast("已成功连接本地字幕工作站后端", "success");
      })
      .catch((error) => {
        appendLog(`后端连接失败：${error.message}`);
        showToast(`后端连接失败：${error.message}`, "error");
      });
  }, []);

  useEffect(() => {
    if (!activeProject) return;
    refreshMedia(activeProject).catch((error) => appendLog(`读取媒体列表失败：${error.message}`));
  }, [activeProject?.id]);

  useEffect(() => {
    if (!activeMedia) {
      setSubtitles([]);
      setSelectedSubtitleId(null);
      return;
    }
    listSubtitles(activeMedia.id)
      .then((nextSubtitles) => {
        setSubtitles(nextSubtitles);
        setSelectedSubtitleId(nextSubtitles[0]?.id ?? null);
      })
      .catch((error) => appendLog(`读取字幕失败：${error.message}`));
  }, [activeMedia?.id]);

  useEffect(() => {
    if (!selectedSubtitle) return;
    setEditSourceText(selectedSubtitle.source_text);
    setEditTranslatedText(selectedSubtitle.translated_text);
    setEditEditedText(selectedSubtitle.edited_text);
    setEditStartMs(String(selectedSubtitle.start_ms));
    setEditEndMs(String(selectedSubtitle.end_ms));
  }, [selectedSubtitle?.id]);

  function handleDeleteProject(projectId: number, event: React.MouseEvent) {
    event.stopPropagation();
    setDeletingProjectId(projectId);
  }

  async function executeDeleteProject(projectId: number) {
    const project = projects.find((p) => p.id === projectId);
    if (!project) return;

    setBusy(true);
    setDeletingProjectId(null);
    try {
      await deleteProject(projectId);
      appendLog(`[系统] 已成功删除项目：${project.name}`);
      showToast(`已成功删除项目 "${project.name}"`, "success");
      const updated = projects.filter((p) => p.id !== projectId);
      setProjects(updated);

      if (activeProject?.id === projectId) {
        const nextActive = updated[0] ?? null;
        setActiveProject(nextActive);
        if (!nextActive) {
          setMediaItems([]);
          setActiveMedia(null);
        }
      }
    } catch (error) {
      appendLog(`[系统] 删除项目失败：${error instanceof Error ? error.message : String(error)}`);
      showToast(`删除项目失败：${error instanceof Error ? error.message : String(error)}`, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateProject() {
    if (!mediaRoot.trim()) {
      appendLog("请先输入视频文件夹路径。");
      showToast("请先选择或输入视频文件夹路径", "info");
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
      showToast(`已成功创建项目 "${project.name}"`, "success");
    } catch (error) {
      appendLog(`创建项目失败：${error instanceof Error ? error.message : String(error)}`);
      showToast(`创建项目失败：${error instanceof Error ? error.message : String(error)}`, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleScan() {
    if (!activeProject) return;
    setBusy(true);
    try {
      const result = await scanProject(activeProject.id);
      const msg = `扫描完成：发现 ${result.found}，新增 ${result.created}，更新 ${result.updated}，跳过 ${result.skipped}。`;
      appendLog(msg);
      showToast(msg, "success");
      await refreshMedia(activeProject);
    } catch (error) {
      appendLog(`扫描失败：${error instanceof Error ? error.message : String(error)}`);
      showToast(`扫描失败：${error instanceof Error ? error.message : String(error)}`, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleProcess() {
    if (!activeMedia) return;
    setBusy(true);
    try {
      const result = await processMedia(activeMedia.id);
      appendLog(`已发起处理任务：#${result.job_id}，阶段 ${result.stage}。`);
      showToast(`任务已成功投递至后台队列 (Job #${result.job_id})`, "success");
    } catch (error) {
      appendLog(`处理失败：${error instanceof Error ? error.message : String(error)}`);
      showToast(`发起处理任务失败：${error instanceof Error ? error.message : String(error)}`, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleExport() {
    if (!activeMedia) return;
    setBusy(true);
    try {
      const result = await exportMedia(activeMedia.id);
      appendLog(`已导出字幕：${result.subtitle_path}`);
      showToast("字幕 SRT 物理文件导出成功！", "success");
      if (activeProject) {
        await refreshMedia(activeProject);
      }
    } catch (error) {
      appendLog(`导出失败：${error instanceof Error ? error.message : String(error)}`);
      showToast(`导出失败：${error instanceof Error ? error.message : String(error)}`, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleUnloadGpu() {
    setBusy(true);
    try {
      const result = await unloadGpuMemory();
      appendLog(`[系统] GPU 资源清理成功：${result.message}`);
      showToast("GPU 显存安全释放成功！", "success");
    } catch (error) {
      appendLog(`[系统] 释放 GPU 资源失败：${error instanceof Error ? error.message : String(error)}`);
      showToast(`释放 GPU 显存失败：${error instanceof Error ? error.message : String(error)}`, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleBrowse() {
    setBusy(true);
    try {
      const result = await browseDirectory();
      if (result.path) {
        setMediaRoot(result.path);
        appendLog(`[系统] 已选定文件夹路径：${result.path}`);
        showToast("已选择文件夹物理路径", "success");
      }
    } catch (error) {
      appendLog(`[系统] 无法打开文件夹选择框，请手动在输入框中填写绝对路径。`);
      showToast("无法打开系统弹窗，请手动填写路径", "info");
    } finally {
      setBusy(false);
    }
  }


  async function handleSaveSubtitle() {
    if (!selectedSubtitle) return;
    setBusy(true);
    try {
      await updateSubtitle(selectedSubtitle.id, {
        source_text: editSourceText,
        translated_text: editTranslatedText,
        edited_text: editEditedText,
        start_ms: Number(editStartMs),
        end_ms: Number(editEndMs)
      });
      appendLog(`字幕段 #${selectedSubtitle.index_no} 已保存。`);
      showToast(`字幕段 #${selectedSubtitle.index_no} 保存成功`, "success");
      if (activeMedia) {
        const nextSubtitles = await listSubtitles(activeMedia.id);
        setSubtitles(nextSubtitles);
        setSelectedSubtitleId(selectedSubtitle.id);
      }
    } catch (error) {
      appendLog(`保存字幕失败：${error instanceof Error ? error.message : String(error)}`);
      showToast(`保存字幕失败：${error instanceof Error ? error.message : String(error)}`, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
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
            <div style={{ display: "flex", gap: "8px", width: "100%", marginTop: "4px" }}>
              <input
                value={mediaRoot}
                onChange={(event) => setMediaRoot(event.target.value)}
                placeholder="E:\\temp\\测试翻译"
                style={{ flex: 1, minWidth: 0 }}
              />
              <button
                className="secondary-button"
                type="button"
                disabled={busy}
                onClick={handleBrowse}
              >
                选择...
              </button>
            </div>
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
              <div
                className={`project-item ${project.id === activeProject?.id ? "selected" : ""}`}
                key={project.id}
              >
                <button
                  className="project-btn"
                  onClick={() => {
                    setActiveProject(project);
                    setActiveMedia(null);
                  }}
                >
                  <strong>{project.name}</strong>
                  <span>{project.media_root}</span>
                </button>
                <button
                  className="delete-btn"
                  title="删除项目"
                  disabled={busy}
                  onClick={(event) => handleDeleteProject(project.id, event)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
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
            <button disabled={!activeMedia || busy} onClick={handleProcess}>
              <Wand2 size={16} />
              处理
            </button>
            <button disabled={!activeMedia || busy} onClick={handleExport}>
              <Save size={16} />
              导出
            </button>
            <button disabled={busy} onClick={handleUnloadGpu} title="释放 GPU 显存资源">
              <Cpu size={16} />
              释放显存
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
                <button
                  className={segment.id === selectedSubtitle?.id ? "subtitle-row selected" : "subtitle-row"}
                  key={segment.id}
                  onClick={() => setSelectedSubtitleId(segment.id)}
                >
                  <span>{segment.index_no}</span>
                  <span>{formatTimestamp(segment.start_ms)}</span>
                  <span>{formatTimestamp(segment.end_ms)}</span>
                  <span>{segment.edited_text || segment.translated_text || segment.source_text}</span>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="editor-panel editor-form">
          <div className="panel-title">
            <span>当前字幕编辑</span>
            <button className="icon-button" title="保存字幕" disabled={!selectedSubtitle || busy} onClick={handleSaveSubtitle}>
              <Save size={16} />
            </button>
          </div>
          {selectedSubtitle ? (
            <div className="subtitle-edit-form">
              <label>
                开始时间（毫秒）
                <input value={editStartMs} onChange={(event) => setEditStartMs(event.target.value)} />
              </label>
              <label>
                结束时间（毫秒）
                <input value={editEndMs} onChange={(event) => setEditEndMs(event.target.value)} />
              </label>
              <label>
                原文
                <textarea value={editSourceText} onChange={(event) => setEditSourceText(event.target.value)} />
              </label>
              <label>
                译文
                <textarea value={editTranslatedText} onChange={(event) => setEditTranslatedText(event.target.value)} />
              </label>
              <label>
                最终文本
                <textarea value={editEditedText} onChange={(event) => setEditEditedText(event.target.value)} />
              </label>
            </div>
          ) : (
            <div className="empty-state">选择一条字幕后可以直接编辑。</div>
          )}
        </div>

        <div className="log-panel">
          {logLines.map((line, index) => (
            <div key={`${line}-${index}`}>{line}</div>
          ))}
        </div>
      </section>
    </main>
      <div className="toast-container">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast ${toast.type}`}>
            <span>{toast.message}</span>
          </div>
        ))}
      </div>

      {deletingProjectId !== null && (
        <div className="modal-overlay" onClick={() => setDeletingProjectId(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <Trash2 size={18} style={{ color: "var(--warning)" }} />
              <span>删除项目确认</span>
            </div>
            <div className="modal-body">
              确定要物理删除项目 <strong>"{projects.find(p => p.id === deletingProjectId)?.name}"</strong> 吗？
              <br />
              此操作将一并清除该项目在数据库中的所有视频、字幕、日志和后台任务，且不可撤销！
            </div>
            <div className="modal-actions">
              <button className="cancel-btn" onClick={() => setDeletingProjectId(null)}>
                取消
              </button>
              <button className="confirm-delete-btn" onClick={() => executeDeleteProject(deletingProjectId)}>
                确定删除
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
