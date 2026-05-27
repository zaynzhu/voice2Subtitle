export type Project = {
  id: number;
  name: string;
  media_root: string;
  output_mode: string;
  created_at: string;
  updated_at: string;
};

export type MediaItem = {
  id: number;
  project_id: number;
  file_path: string;
  file_name: string;
  duration_ms: number | null;
  status: string;
  source_language: string;
  target_language: string;
  subtitle_path: string | null;
  fingerprint: string;
  created_at: string;
  updated_at: string;
};

export type ScanResult = {
  project_id: number;
  found: number;
  created: number;
  updated: number;
  skipped: number;
};

export type SubtitleSegment = {
  id: number;
  media_item_id: number;
  index_no: number;
  start_ms: number;
  end_ms: number;
  source_text: string;
  translated_text: string;
  edited_text: string;
  confidence: number | null;
  speaker: string | null;
  is_edited: boolean;
};

export type SubtitleEditPayload = {
  source_text: string;
  translated_text: string;
  edited_text: string;
  start_ms: number;
  end_ms: number;
};

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function listProjects(): Promise<Project[]> {
  return request<Project[]>("/api/projects");
}

export function createProject(payload: {
  name: string;
  media_root: string;
  output_mode: string;
}): Promise<Project> {
  return request<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function scanProject(projectId: number): Promise<ScanResult> {
  return request<ScanResult>(`/api/projects/${projectId}/scan`, { method: "POST" });
}

export function listMedia(projectId: number): Promise<MediaItem[]> {
  return request<MediaItem[]>(`/api/projects/${projectId}/media`);
}

export function listSubtitles(mediaId: number): Promise<SubtitleSegment[]> {
  return request<SubtitleSegment[]>(`/api/media/${mediaId}/subtitles`);
}

export function updateSubtitle(segmentId: number, payload: SubtitleEditPayload): Promise<{ id: number; status: string }> {
  return request(`/api/subtitles/${segmentId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function processMedia(mediaId: number): Promise<{ media_item_id: number; status: string; message: string }> {
  return request(`/api/media/${mediaId}/process`, { method: "POST" });
}

export type JobInfo = {
  id: number;
  type: string;
  status: string;
  stage: string;
  progress: number | null;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

export function listMediaJobs(mediaId: number): Promise<JobInfo[]> {
  return request<JobInfo[]>(`/api/media/${mediaId}/jobs`);
}

export type ModelInfo = {
  name: string;
  type: string;
  size_mb: number;
};

export type EngineStatus = {
  available: string[];
  faster_whisper: boolean;
  openai_whisper: boolean;
};

export type ModelsResponse = {
  model_root: string;
  active_model: string;
  models: ModelInfo[];
  engines: EngineStatus;
  gpu: { device: string; vram_mb: number } | null;
};

export function listModels(): Promise<ModelsResponse> {
  return request<ModelsResponse>("/api/models");
}

export function exportMedia(mediaId: number): Promise<{ media_id: number; subtitle_path: string }> {
  return request(`/api/media/${mediaId}/export`, { method: "POST" });
}

export function unloadGpuMemory(): Promise<{ success: boolean; message: string }> {
  return request("/api/media/unload-gpu", { method: "POST" });
}

export function browseDirectory(): Promise<{ path: string }> {
  return request<{ path: string }>("/api/projects/browse", { method: "POST" });
}

export function deleteProject(projectId: number): Promise<{ message: string; id: number }> {
  return request<{ message: string; id: number }>(`/api/projects/${projectId}`, { method: "DELETE" });
}

export function cancelJobs(): Promise<{ cancelled_jobs: number; cleared_queue: number; gpu_released: string }> {
  return request<{ cancelled_jobs: number; cleared_queue: number; gpu_released: string }>("/api/jobs/cancel", { method: "POST" });
}

/** 构建媒体流 URL，用于 <video> 或 <audio> 的 src。 */
export function getStreamUrl(mediaId: number): string {
  return `/api/media/${mediaId}/stream`;
}
