# Voice2Subtitle

本地视频字幕工作站 — 扫描本地视频文件夹，提取音频，语音转录（Whisper 双引擎），自动翻译，双语字幕编辑，导出 SRT。100% 离线运行。

## 功能特性

- **双引擎语音转录** — 自动检测 `faster-whisper`（CTranslate2）和 `openai-whisper`（PyTorch .pt）可用性，匹配本地模型格式
- **自动翻译** — 接入 Google Translate，支持多语言互译，异常句自动跳过不中断流程
- **视频播放器** — 内置 HTML5 播放器，支持 12+ 视频格式，字幕实时叠加显示，点击字幕跳转对应画面
- **字幕编辑** — 双语字幕列表，支持手动修改原文/译文/最终文本，优先级覆盖
- **批量处理** — 串行任务队列，支持勾选多个视频批量投递，可中途终止任务
- **GPU 显存管理** — 一键释放显存，支持低显存环境（如 RTX 3050Ti 4GB）
- **任务取消** — 随时终止正在运行的转录任务，清除队列，释放 GPU 资源
- **SRT 导出** — 一键导出标准 SRT 字幕文件，存放于视频同级目录

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+（前端开发）
- FFmpeg（音频提取）
- CUDA 可选（GPU 加速转录）

### 安装

```bash
# 克隆仓库
git clone https://github.com/zaynzhu/voice2Subtitle.git
cd voice2Subtitle

# 后端依赖
cd backend
pip install -e ".[ml]"          # 含 ML 依赖（faster-whisper）
# 或 pip install -e .           # 仅核心依赖，需手动安装 whisper

# 前端依赖
cd ../frontend
npm install
```

### 启动

**方式一：智能启动脚本（推荐）**

```bash
# 项目根目录，自动选择最佳 Python 环境
python start-backend.py
# 另开终端
cd frontend && npm run dev
```

**方式二：手动启动**

```bash
# 后端（backend/ 目录）
python -m uvicorn app.main:app --host 127.0.0.1 --port 19001 --reload

# 前端（frontend/ 目录）
npm run dev
```

**方式三：生产部署**

```bash
cd frontend && npm run build    # 构建前端
cd ../backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 19000
# 后端自动挂载 frontend/dist/ 作为静态文件，访问 http://127.0.0.1:19000
```

### Whisper 模型

将模型文件放入项目根目录 `whisper_model/`：

```
whisper_model/
├── medium.pt           # OpenAI Whisper 格式（自动使用 openai-whisper 引擎）
└── medium-ct2/         # CTranslate2 格式目录（自动使用 faster-whisper 引擎）
    ├── model.bin
    ├── config.json
    └── ...
```

设置 `V2S_WHISPER_MODEL=auto`（默认）会自动扫描该目录。也可指定具体模型名如 `V2S_WHISPER_MODEL=medium`。

## 项目结构

```
voice2Subtitle/
├── backend/
│   └── app/
│       ├── api/            # REST 路由：projects, media, subtitles, jobs, exports, models
│       ├── models/         # SQLAlchemy ORM + Pydantic schemas
│       ├── services/       # 核心业务：scanner, audio_extractor, transcriber, translator, subtitle_writer
│       ├── workers/        # 串行任务队列 + 守护线程处理器
│       ├── config.py       # pydantic-settings 配置（V2S_ 前缀）
│       ├── db.py           # SQLAlchemy + SQLite WAL 会话工厂
│       └── main.py         # FastAPI 应用入口
├── frontend/
│   └── src/
│       ├── main.tsx        # React 单文件 SPA（无路由，无组件库）
│       ├── api/client.ts   # 类型化 fetch 封装 + API 调用
│       └── styles/app.css  # CSS 自定义属性，磨砂玻璃风格
├── whisper_model/          # Whisper 模型存放目录（gitignored）
├── data/                   # SQLite 数据库 + 音频缓存（gitignored）
├── start-backend.py        # 智能启动脚本
└── .env.example            # 环境变量示例
```

## API 接口

### 项目管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/projects` | 获取项目列表 |
| `POST` | `/api/projects` | 创建项目 |
| `DELETE` | `/api/projects/{id}` | 删除项目 |
| `POST` | `/api/projects/{id}/scan` | 扫描视频文件 |
| `POST` | `/api/projects/browse` | 打开文件夹选择对话框 |

### 媒体操作

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/projects/{id}/media` | 获取项目下的视频列表 |
| `GET` | `/api/media/{id}` | 获取视频详情 |
| `GET` | `/api/media/{id}/stream` | 流式传输视频（支持 Range 请求） |
| `POST` | `/api/media/{id}/process` | 提交处理任务 |
| `POST` | `/api/media/{id}/export` | 导出 SRT 文件 |
| `POST` | `/api/media/unload-gpu` | 释放 GPU 显存 |

### 任务与字幕

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/media/{id}/jobs` | 获取任务列表 |
| `POST` | `/api/jobs/cancel` | 终止任务并释放 GPU |
| `GET` | `/api/media/{id}/subtitles` | 获取字幕段列表 |
| `PATCH` | `/api/subtitles/{id}` | 编辑字幕段 |
| `GET` | `/api/models` | 获取模型和引擎信息 |

## 环境变量

项目使用 `V2S_` 前缀的环境变量，可通过 `.env` 文件或系统环境变量配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `V2S_HOST` | `127.0.0.1` | 监听地址 |
| `V2S_PORT` | `19000` | 生产模式端口 |
| `V2S_DB_PATH` | `./data/app.sqlite3` | 数据库路径 |
| `V2S_CACHE_DIR` | `./data/cache` | 音频缓存目录 |
| `V2S_MODEL_ROOT` | `whisper_model` | Whisper 模型目录 |
| `V2S_WHISPER_MODEL` | `auto` | 模型选择（auto 自动扫描） |
| `V2S_WHISPER_DEVICE` | `auto` | 推理设备（auto: GPU→CPU） |
| `V2S_WHISPER_COMPUTE_TYPE` | `auto` | 计算精度（auto: GPU float16, CPU int8） |
| `V2S_DEFAULT_SOURCE_LANG` | `auto` | 源语言 |
| `V2S_DEFAULT_TARGET_LANG` | `zh-CN` | 翻译目标语言 |
| `V2S_OUTPUT_MODE` | `beside_video` | SRT 导出位置 |

## 支持的视频格式

扫描器支持：`.mp4` `.mkv` `.mov` `.avi` `.wmv` `.flv` `.webm` `.ts` `.mpg` `.mpeg` `.m4v` `.3gp` `.rmvb` `.rm`

播放器支持：`.mp4` `.mkv` `.mov` `.avi` `.wmv` `.flv` `.webm` `.ts` `.mpg` `.mpeg` `.m4v` `.3gp` `.mp3` `.wav` `.aac` `.flac` `.m4a` `.ogg` `.wma`

## 技术栈

- **后端** — FastAPI + SQLAlchemy + SQLite (WAL) + Uvicorn
- **前端** — React 18 + Vite + TypeScript + Lucide Icons
- **转录** — faster-whisper / openai-whisper（双引擎自动选择）
- **翻译** — deep-translator (Google Translate)
- **音频** — FFmpeg

## 开源协议

[MIT License](LICENSE)
