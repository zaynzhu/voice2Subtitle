# Voice2Subtitle 本地字幕工作站设计方案

## 1. 项目背景
原先位于 `E:\temp\测试翻译` 目录下的单脚本原型可以扫描目录下的视频、使用 FFmpeg 提取音频、调用 Whisper 进行日语语音转录、调用 `deep-translator` 翻译为简体中文并最终在同级目录下输出 `.srt` 文件。

为了提升易用性、稳定性和交互体验，本项目旨在将该原型改造成一个**本地 Web 字幕工作站**。第一版方案专注于极佳的本地端到端字幕生命周期管理、清晰的异步任务调度状态、高效的交互式双语字幕编辑，并为后续 Docker 容器化部署到 NAS 等私有设备打下坚实基础。

---

## 2. 产品方向与定位
- **定位**：单用户本地一站式字幕工作站，专注于本地视频文件的字幕自动生成、双语校对、编辑与物理导出。
- **非实时系统**：本系统处理已有的离线媒体文件，并将所有中间转录与翻译数据写入 SQLite 数据库，以便在某个步骤失败时能够从中断处恢复，无需从头开始。
- **本地运行端口**：
  ```text
  http://127.0.0.1:19000
  ```
- **未来扩展**：相同的系统架构可轻松打包至 Docker 镜像，通过挂载 NAS 上的媒体目录实现云端/私有云部署。

---

## 3. 首版功能范围

### 包含特性：
1. **项目管理**：支持绑定本地媒体文件夹创建项目，并支持多次扫描。
2. **多视频格式扫描**：支持扫描并管理 `.mkv`、`.mp4` 和 `.mov` 文件。
3. **媒体元数据解析**：通过 `ffprobe` 快速读取视频时长与分辨率等元数据。
4. **音频自动提取**：通过 `ffmpeg` 提取 16 kHz 单声道低码率音频缓存。
5. **智能自适应语音识别 (Task A)**：
   - 支持 `FasterWhisperTranscriber`（支持 CTranslate2 模型格式）与 `OpenAIWhisperTranscriber`（原生 PyTorch `.pt` 格式模型，如 1.5GB `medium.pt` 离线文件）双引擎。
   - 100% 物理完全离线模型载入，无需联网校验，智能识别并复用本地大模型资产。
   - 自适应硬件环境，CUDA 可用时启用 GPU 加速（采用 float16 精度），否则平滑降级至 CPU 运行（采用 int8 精度）。
6. **高容错自动翻译 (Task B)**：对接 `deep-translator` (Google 翻译)，提供 None 结果安全守卫和空行过滤，支持单句异常隔离。
7. **串行异步任务调度 (Task C & D)**：引入内存双端队列与常驻后台 `SerialProcessor` 串行处理线程，避免重型 GPU 识别任务阻塞 HTTP 线程，提供宕机自动中断恢复机制。
8. **一键释放显存（Wow 体验）**：在前端提供“释放显存”按钮，通过后台触发垃圾回收与 `torch.cuda.empty_cache()`，在 1 秒内归还显存。
9. **交互式 Web 控制台**：
   - 视频列表与状态过滤。
   - 视频播放器与字幕实时高亮、Seeking 点击跳转。
   - 类似 Excel 的交互式双语字幕表格编辑器，双击即时编辑并秒级保存至 SQLite。
   - 一键导出规范的 `.srt` 物理字幕文件。
   - 实时处理进度展示与 Uvicorn 终端日志流。

### 暂缓特性：
- 实时直播流字幕生成。
- 多用户注册与权限管理。
- 复杂的音频波形图可视化编辑。
- 视频流实时转码播放。
- 说话人角色识别（Speaker Diarization）。

---

## 4. 技术栈推荐

### 后端：
- **开发语言**：Python
- **Web 框架**：FastAPI
- **持久化**：SQLite (开启 WAL 模式以应对多线程并发) + SQLAlchemy ORM
- **数据校验**：Pydantic schemas
- **媒体工具**：`ffmpeg` 和 `ffprobe`
- **AI 引擎**：`faster-whisper` 与原生 `openai-whisper`

### 前端：
- **框架**：React + Vite + TypeScript
- **播放器**：原生 HTML5 Video + 字幕同步高亮组件
- **编辑器**：交互式表格字幕校对系统

### 部署方式：
- **本地部署**：将前端编译打包后的静态目录 `frontend/dist` 动态挂载到 FastAPI 服务下，实现单入口一键运行。
- **Docker 容器化**：后期提供 `Dockerfile` 及 `Docker Compose` 配置。

---

## 5. 架构设计

```text
backend/ (后端)
  app/
    main.py              # FastAPI 启动入口，挂载前端静态文件
    config.py            # 统一环境变量及配置对象
    db.py                # SQLite WAL 数据库连接与会话工厂
    api/                 # API 路由层
      projects.py
      media.py           # 媒体扫描与显存释放接口
      jobs.py            # 任务调度与日志监控接口
      subtitles.py       # 字幕增删改查及保存接口
    services/            # 核心业务服务层
      scanner.py         # 磁盘视频扫描服务
      media_probe.py     # ffprobe 元数据服务
      audio_extractor.py # ffmpeg 音频提取服务
      transcriber.py     # 智能双引擎语音识别服务 (Task A)
      translator.py      # Google 翻译引擎 (Task B)
      subtitle_writer.py # SRT 字幕导出服务
    workers/             # 异步任务处理层 (Task C)
      queue.py           # 线程安全双端任务队列
      processor.py       # 常驻后台串行执行 Worker
    models/              # 数据模型层
      entities.py        # SQLAlchemy ORM 数据库实体
      schemas.py         # Pydantic 输入输出校验模型

frontend/ (前端)
  src/
    app/                 # 前端应用入口
    components/          # 基础 UI 按钮、图标、弹窗组件
    pages/               # 主工作站页面
    api/                 # API 请求封装
    styles/              # Vanilla CSS 现代动效与配色系统
```

---

## 6. 数据流向

```text
创建项目绑定文件夹 
-> 自动扫描视频文件 
-> 计算指纹写入 media_items 表 
-> 用户点击“开始转录” 
-> 生成后台任务并推入 JobQueue 
-> Worker 提取音频 
-> 语音转录服务 (自适应 GPU 加速) 
-> 写入原始字幕段落到数据库 
-> 触发自动翻译 
-> 写入翻译后字幕段落 
-> 标记媒体状态为“ready_for_review”并自动物理导出 `.srt` 
-> 用户在前端点击播放、 Seeking 跳转、修改文本或微调时间戳 
-> 秒级保存编辑数据 
-> 用户重新点击导出或修改后自动覆盖物理字幕文件
```

---

## 7. 数据库设计 (WAL 模式)
SQLite 在多进程或并发写入下容易死锁，我们采用 SQLite **WAL (Write-Ahead Logging)** 模式，并设置超时锁释放时长：
```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
```

### 核心表结构：
1. **projects** (项目表)
   - `id` (主键)
   - `name` (项目名)
   - `media_root` (物理媒体路径)
   - `created_at` / `updated_at`
2. **media_items** (媒体文件表)
   - `id` (主键)
   - `project_id` (关联项目)
   - `file_path` (文件物理绝对路径)
   - `file_name` (文件名)
   - `duration_ms` (视频时长，毫秒)
   - `status` (视频转录状态)
   - `source_language` / `target_language` (源语言/目标语言)
   - `fingerprint` (由路径、文件大小和修改时间组合计算出的排重指纹)
3. **jobs** (后台任务表)
   - `id` (主键)
   - `media_item_id` (关联视频)
   - `status` (任务状态：pending / running / succeeded / failed / interrupted)
   - `stage` (当前子阶段：probing / extracting_audio / transcribing / translating)
   - `progress` (处理进度 0.0 - 1.0)
   - `error_code` / `error_message` (错误代码及信息)
   - `started_at` / `finished_at`
4. **subtitle_segments** (字幕段落明细表)
   - `id` (主键)
   - `media_item_id` (关联视频)
   - `index_no` (从 1 开始的行号)
   - `start_ms` / `end_ms` (起止毫秒时间戳)
   - `source_text` (Whisper 转录原文)
   - `translated_text` (自动翻译译文)
   - `edited_text` (人工修改后的最终文本)
   - `is_edited` (是否经过人工修改)
   - `confidence` (转录置信度)
5. **job_logs** (任务日志明细表)
   - `id` (主键)
   - `job_id` (关联任务)
   - `level` (日志级别)
   - `message` (日志文本)

---

## 8. 字幕导出优先级策略
导出物理字幕时，系统将遵循严格的**内容覆盖优先级策略**，确保人工作业的最高权威性，即使重新运行自动翻译，也绝不会覆盖用户手工校对的结果：
```text
最终导出内容 = edited_text (若 is_edited=True) > translated_text > source_text
```

---

## 9. 异常处理机制与错误代码

- `media_probe_failed`：视频封装格式损坏或 `ffprobe` 解析失败。
- `audio_extract_failed`：FFmpeg 音频解析或磁盘写入失败。
- `model_load_failed`：本地 Whisper 模型文件缺失或显存不足。
- `transcribe_failed`：语音识别期间发生异常崩溃。
- `translate_failed`：机器翻译接口超时或网络不可用。
- `subtitle_export_failed`：物理 SRT 写入目录权限不足。
- `filesystem_permission`：Windows 文件系统锁定或无写权限。

---

## 10. 本地环境配置参考 (.env)

```text
V2S_HOST=127.0.0.1
V2S_PORT=19000
V2S_DB_PATH=./data/app.sqlite3
V2S_CACHE_DIR=./data/cache
V2S_MODEL_ROOT=E:\temp\测试翻译\whisper_model  # 绑定用户本地的高清模型存放目录
V2S_OUTPUT_MODE=beside_video
V2S_DEFAULT_SOURCE_LANG=auto
V2S_DEFAULT_TARGET_LANG=zh-CN
V2S_WHISPER_MODEL=medium                       # 启用高精度 medium 模型
V2S_WHISPER_DEVICE=auto
V2S_WHISPER_COMPUTE_TYPE=auto
```

---

## 11. 部署与交付总结
整个开发进程高度契合了**渐进式增强**与**本地化优先**原则：
- **开发与调试**：通过解决 Windows GBK 兼容性、SQLite WAL 多线程锁竞争和 native whisper 完全离线路径解析，打造了极高健壮性的后台服务。
- **用户体验**：首创的“显存一键释放”和“本地模型智能免转换识别”，彻底解决了用户在 3050Ti 本地显卡调试时的痛点。
- **成果**：全套流程在本地无缝连通，为用户提供了媲美专业工作站的使用体验。
