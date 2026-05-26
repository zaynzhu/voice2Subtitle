# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Voice2Subtitle — 本地视频转字幕工作站。扫描本地视频文件夹，提取音频（FFmpeg），语音转录（Whisper 双引擎），自动翻译（Google Translate），双语字幕编辑，导出 SRT。100% 离线运行，针对低显存 GPU（如 RTX 3050Ti）优化。

## 开发命令

### 后端（在 `backend/` 目录下执行）

```bash
# 安装（含 ML 依赖，用于 Whisper）
pip install -e ".[ml]"

# 启动开发服务器（端口 19001 用于 Vite 代理；19000 用于独立部署）
python -m uvicorn app.main:app --host 127.0.0.1 --port 19001 --reload

# 运行全部测试
python -m pytest

# 运行单个测试文件
python -m pytest tests/test_subtitle_writer.py
```

### 前端（在 `frontend/` 目录下执行）

```bash
npm install
npm run dev       # Vite 开发服务器，127.0.0.1:19000，代理 /api → :19001
npm run build     # tsc && vite build → frontend/dist/
```

### 全栈开发流程

后端跑在 19001，前端跑在 19000。Vite 代理将 `/api` 和 `/health` 转发到后端。生产部署：先 `npm run build`，后端启动在 19000 — FastAPI 会挂载 `frontend/dist/` 作为静态文件。

## 架构

### 后端：FastAPI + SQLAlchemy + Worker 线程

```
backend/app/
├── main.py          # 应用工厂，startup/shutdown 生命周期，静态文件挂载
├── config.py        # pydantic-settings，环境变量前缀 V2S_，读取 .env
├── db.py            # SQLAlchemy 引擎 + SQLite WAL 会话工厂
├── api/             # 7 个路由模块：health, projects, media, subtitles, subtitle_edits, jobs, exports
├── models/          # entities.py（SQLAlchemy ORM），schemas.py（Pydantic 请求/响应）
├── services/        # 无状态业务逻辑
│   ├── scanner.py          # 遍历文件夹，指纹视频文件
│   ├── audio_extractor.py  # FFmpeg 提取 WAV
│   ├── media_probe.py      # ffprobe 获取元数据
│   ├── transcriber.py      # Whisper 工厂（faster-whisper vs 原生）
│   ├── translator.py       # Google 翻译（deep-translator）
│   ├── subtitle_writer.py  # SRT 文件生成
│   └── job_pipeline.py     # 编排：探测 → 提取 → 转录 → 翻译 → 写入
├── workers/
│   ├── queue.py      # 内存 FIFO 队列（collections.deque + threading.Lock）
│   └── processor.py  # SerialProcessor 守护线程，每秒轮询队列
```

核心模式：
- **内存队列，串行执行** — 同一时间只处理一个 job，重启后队列不持久化。启动时 `recover_interrupted_jobs()` 将孤立的 `running` 状态 job 标记为 `interrupted`。
- **Whisper 双引擎** — `create_transcriber_from_settings()` 根据 `.pt` 文件（原生 whisper）vs CTranslate2 模型（faster-whisper）自动选择。由 `V2S_WHISPER_MODEL`、`V2S_WHISPER_DEVICE`、`V2S_WHISPER_COMPUTE_TYPE` 控制。
- **GPU 显存释放** — `/api/media/unload-gpu` 端点执行 `gc.collect()` + `torch.cuda.empty_cache()`。
- **配置** — 所有设置通过 `V2S_` 前缀环境变量或 `.env` 文件，参见 `.env.example`。

### 前端：单文件 React SPA

```
frontend/src/
├── main.tsx       # 整个 UI 在一个 App() 组件中（~550 行），hooks 管理状态
├── api/client.ts  # 类型化 fetch 封装 + 全部 API 调用函数
└── styles/app.css # 原生 CSS + CSS 自定义属性，无框架
```

- 无 React Router，无组件库，无状态管理库。
- 所有 UI 状态通过 `useState`/`useEffect` 在 `App()` 中管理。
- API 客户端是轻量 `fetch()` 封装，带类型化的请求/响应函数。

### 数据流

```
用户选择文件夹 → Scanner 扫描视频 → 用户提交任务
  → SerialProcessor 从队列取出
  → 探测(ffprobe) → 提取音频(ffmpeg) → 转录(Whisper)
  → 翻译(Google) → 写入 SRT → 任务完成
  → 用户在浏览器编辑字幕 → 导出最终 SRT
```

## 规范

- **Python**：snake_case，`backend/` 为 uvicorn/pytest 的工作目录。
- **TypeScript**：camelCase 变量/函数，PascalCase 组件/类型。
- **API 路由**：`/api/` 前缀，在 `backend/app/api/` 模块中定义。
- **数据库**：SQLite，路径 `data/app.sqlite3`，WAL 模式。音频缓存 `data/cache/`。
- **Whisper 模型**：存放于 `models/whisper/`（gitignored）。
- **前端为中文界面** — 用户可见文案均为中文。