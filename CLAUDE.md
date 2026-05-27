# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Voice2Subtitle — 本地视频转字幕工作站。扫描本地视频文件夹，提取音频（FFmpeg），语音转录（Whisper 双引擎），自动翻译（Google Translate），双语字幕编辑，导出 SRT。100% 离线运行，针对低显存 GPU（如 RTX 3050Ti）优化。

## 开发命令

### 后端（在 `backend/` 目录下执行）

```bash
pip install -e ".[ml]"          # 安装（含 ML 依赖）
python -m pytest                 # 运行全部测试
python -m pytest tests/test_x.py # 运行单个测试
```

### 前端（在 `frontend/` 目录下执行）

```bash
npm install    # 安装依赖
npm run dev    # Vite 开发服务器 127.0.0.1:19000，代理 /api → :19001
npm run build  # tsc && vite build → frontend/dist/
```

### 全栈启动（推荐）

```bash
# 项目根目录下，自动选择最完整的 Python 环境（检测 Anaconda 等）
python start-backend.py
```

手动方式：
```bash
# 后端（在 backend/ 下）
python -m uvicorn app.main:app --host 127.0.0.1 --port 19001 --reload
# 前端（在 frontend/ 下）
npm run dev
```

生产部署：先 `npm run build`，后端启动在 19000 — FastAPI 挂载 `frontend/dist/` 作为静态文件。

## 架构

### 后端：FastAPI + SQLAlchemy + Worker 线程

```
backend/app/
├── main.py          # 应用工厂，静态文件挂载
├── config.py        # pydantic-settings，V2S_ 前缀，model_root 基于项目根绝对路径
├── db.py            # SQLAlchemy + SQLite WAL 会话工厂
├── api/             # 8 个路由：health, projects, media, subtitles, subtitle_edits, jobs, exports, models
├── models/          # entities.py（ORM），schemas.py（Pydantic）
├── services/
│   ├── transcriber.py      # 双引擎工厂：自动检测可用引擎，优先 CTranslate2
│   ├── job_pipeline.py     # 编排：探测 → 提取 → 转录 → 翻译 → 写入
│   └── ...                 # scanner, audio_extractor, media_probe, translator, subtitle_writer
├── workers/
│   ├── queue.py      # 内存 FIFO（deque + Lock），不持久化
│   └── processor.py  # SerialProcessor 守护线程
```

核心模式：
- **Whisper 双引擎自动选择** — `create_transcriber_from_settings()` 检测 `faster_whisper`/`openai-whisper` 可用性，匹配模型格式（`.pt` 用原生，CTranslate2 目录用 faster-whisper），引擎不可用时给出明确 ImportError。
- **`V2S_WHISPER_MODEL=auto`** — 从 `whisper_model/` 目录自动扫描模型文件。
- **GPU 显存释放** — `/api/media/unload-gpu` 执行 `gc.collect()` + `torch.cuda.empty_cache()`。
- **`GET /api/models`** — 返回可用引擎、模型列表、GPU 信息，供前端显示。

### 前端：React SPA（单文件架构）

```
frontend/src/
├── main.tsx       # App() 组件，hooks 管理所有状态
├── api/client.ts  # 类型化 fetch 封装 + 全部 API 调用
└── styles/app.css # CSS 自定义属性，无框架
```

- 无 React Router，无组件库，无状态管理库。
- 侧边栏模型卡片显示引擎状态（CT2/PT）和 GPU 信息。
- 视频列表支持 checkbox 勾选批量处理，工具栏按钮分两行。
- Toast 通知系统 + 任务进度轮询 + 项目删除确认弹窗。

### 数据流

```
用户选择文件夹 → Scanner 扫描视频 → 勾选视频 → 批量处理
  → SerialProcessor 串行消费
  → 探测 → 提取音频 → 转录(Whisper) → 翻译(Google) → 写入 SRT
  → 用户编辑字幕 → 导出最终 SRT
```

## 规范

- **Python**：snake_case，`backend/` 为工作目录。
- **TypeScript**：camelCase 变量/函数，PascalCase 组件/类型。
- **API 路由**：`/api/` 前缀，在 `backend/app/api/` 定义。
- **数据库**：SQLite `data/app.sqlite3`，WAL 模式。缓存 `data/cache/`。
- **Whisper 模型**：放于项目根 `whisper_model/`（gitignored），`V2S_WHISPER_MODEL=auto` 自动扫描。
- **前端为中文界面** — 用户可见文案均为中文。
- **环境检测** — `start-backend.py` 自动搜索 PATH + conda 中引擎最全的 Python 环境。