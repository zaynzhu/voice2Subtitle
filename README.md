# Voice2Subtitle 本地字幕工作站

> 🎬 一站式本地化视频语音转录、双语字幕翻译、交互式校对与一键 SRT 导出工作站。

---

## 📖 简介

**Voice2Subtitle** 是一款专为个人打造的本地 Web 字幕工作站。它能够将您本地媒体文件夹下的视频文件，一键转录为高精度的语音时间轴段落，自动接入翻译，并提供极佳的交互式双语校对工作台，最终物理导出为标准字幕文件。

项目秉持 **100% 本地化优先** 的原则，深度优化了在低显存本地环境（如 RTX 3050Ti）下的资源分配。首创了 **自适应原生/CTranslate2 双引擎转录** 与 **显存一键安全释放（Unload GPU）** 技术，确保您在断网或离线状态下，依然能流畅复用本地高清模型资产。

---

## ✨ 已完成核心特性

### 1. 🤖 智能自适应语音识别 (Task A)
- **自适应双引擎转录**：无缝支持 `faster-whisper`（CTranslate2 格式模型）与原生 OpenAI Whisper（PyTorch `.pt` 格式，如本地 1.5GB `medium.pt` 物理文件）双引擎自动识别。
- **100% 完全物理离线加载**：首创物理路径截取与本地缓存目录绑定策略，彻底绕过原生 Whisper 对外网（openaipublic.blob）的联网拉取检测，杜绝因无翻墙网络导致的加载卡死。
- **硬件自适应检测**：自动检测 CUDA 状态，可用时优先启用 GPU 加速（float16 精度），否则平滑降级至 CPU 运行（int8 精度）。

### 2. 🈲 高容错机器翻译通道 (Task B)
- **自动翻译引擎**：无缝对接 `deep-translator` 库，支持将 Recognized 原始文本（如日语、英语）自动翻译为简体中文。
- **异常隔离与 None 守卫**：内置空行跳过过滤、翻译返回 `None` 时的安全防护机制。单句翻译异常自动隔离，保证重型转录不会因某句网络波动而发生灾难性中断。

### 3. 🚦 串行异步任务队列 (Task C)
- **零阻塞异步架构**：基于 `threading.Lock` 保护的双端内存任务队列 `JobQueue`，以前台轻量轮询代替同步长连接等待。
- **常驻后台串行 Worker**：由独立守护线程 `SerialProcessor` 统一消费任务，避免高并发投递引发的 GPU 显存撑爆及 Uvicorn 线程同步阻塞。

### 4. 🔗 异步流水线全链路打通 (Task D)
- **大闭环生命周期管理**：自动串联 `探针扫描 -> FFmpeg 音频提取 -> Whisper 语音转录 -> 写入 SQLite -> 发起自动翻译 -> 自动导出物理 SRT` 的全套生命周期。
- **宕机与中断恢复保护**：在服务启动时自动回收扫描 `running` 中断状态的残留任务，回滚为 `interrupted` 并允许随时一键重试。

### 5. 🛠️ 体验与健壮性优化 (Wow Moments)
- **显存一键安全释放 (Unload GPU)**：前端集成带 Cpu 动画图标的控制按钮，一键向后台发送 `/unload-gpu` 请求，在 1 秒内强制执行 `gc.collect()` 和 `torch.cuda.empty_cache()`，将显存完璧归赵返还系统。
- **Windows GBK 控制台 Unicode 兼容**：彻底过滤并重构了终端输出中可能导致 Windows CMD/PowerShell 抛出 `UnicodeEncodeError` 报错中断 Pipeline 的所有特殊 Unicode 字符。
- **SQLite 物理并发锁死防护**：数据库连接池启用 SQLite WAL 模式，且在后台 Worker 中使用上下文管理器 `with self._session_factory() as session:` 规范会话，规避了高并发下的数据库写死锁。

---

## 🛠️ 技术栈

| 层级 | 核心技术 | 作用说明 |
|:---|:---|:---|
| **后端** | FastAPI | 提供轻量、快速的高并发 RESTful 路由与静态资源挂载能力 |
| **持久化** | SQLAlchemy + SQLite (WAL) | 采用 WAL 模式保障多线程并发写入的数据持久化与行段记录 |
| **异步调度** | 线程安全 JobQueue + 守护 Worker 线程 | 以前后端分离的串行任务队列消费繁重的音视频转录任务 |
| **AI 语音转录** | OpenAI Whisper & Faster-Whisper | 自适应双引擎，支持本地 pt 格式大模型离线快速推理 |
| **机器翻译** | deep-translator (Google Translate) | 提供断句级高精度双语翻译及异常句自动忽略保护 |
| **前端** | React 18 + Vite + TypeScript | 搭建响应敏捷的现代化单页控制台，采用 Vanilla CSS 编写微交互 |
| **播放器** | HTML5 Video Player | 深度对接时间轴，支持高亮字幕同步联动与 Seeking 双向跳转 |

---

## 📂 项目结构

```text
voice2Subtitle/
├── backend/                  # 后端项目根目录
│   ├── app/
│   │   ├── api/              # RESTful API 控制器层 (路由与接口定义)
│   │   ├── models/           # Pydantic 校验模型与 SQLAlchemy 数据库实体
│   │   ├── services/         # 核心业务服务层 (包含扫描、音频提取、双引擎转录、翻译、SRT写入)
│   │   ├── workers/          # 后台常驻守护线程与任务队列
│   │   ├── config.py         # 统一环境变量加载器
│   │   ├── db.py             # 数据库引擎与会话工厂定义
│   │   └── main.py           # FastAPI 服务入口及前端静态目录挂载
│   ├── data/                 # 本地持久化数据库及音频解析缓存 (已忽略)
│   ├── requirements.txt      # 核心运行依赖
│   └── pyproject.toml        # 可选依赖及项目元数据
├── frontend/                 # 前端项目根目录
│   ├── src/
│   │   ├── components/       # 基础通用 UI 元素
│   │   ├── pages/            # 工作站主控制台及交互表格
│   │   ├── api/              # HTTP 请求与后台接口对接层
│   │   └── styles/           # 现代化磨砂玻璃、色彩渐变与微动效配色系统
│   ├── package.json          # 前端依赖配置
│   ├── vite.config.ts        # Vite 打包及跨域反向代理配置
│   └── dist/                 # 前端静态打包产物目录 (已忽略)
├── docs/                     # 系统核心技术文档与设计方案
│   ├── plans/                # 系统详细设计方案 (简体中文)
│   └── progress/             # 开发进度与里程碑进展总结 (简体中文)
├── AGENTS.md                 # 智能体开发规范与协作指南
├── README.md                 # 本项目主文档
└── .gitignore                # 版本控制忽略配置
```

---

## 🚀 本地快速启动

### 方式零：智能启动脚本（推荐）

项目根目录提供 `start-backend.py`，自动搜索 PATH 和 Anaconda 中引擎最全的 Python 环境：

```powershell
# 项目根目录下执行，自动选择最佳 Python 并启动后端
python start-backend.py
```

前端开发时另开终端：`cd frontend && npm run dev`

### 方式一：全局 Python 环境极速启动

如果您不想折腾复杂的虚拟环境，并且电脑中已安装 Python 3.11+，可以直接使用本方法：

```powershell
# 1. 进入后端目录，一键安装所有核心依赖与 AI 库
cd backend
python -m pip install "deep-translator>=1.11.4" "fastapi>=0.111.0" "pydantic-settings>=2.2.1" "sqlalchemy>=2.0.30" "uvicorn[standard]>=0.29.0" "faster-whisper>=1.0.0"

# 2. 启动一站式托管服务（后端将自动挂载前端已编译好的 dist 静态网页）
python -m uvicorn app.main:app --host 127.0.0.1 --port 19000
```
> 🎉 **运行成功**：在浏览器中打开 [http://127.0.0.1:19000](http://127.0.0.1:19000) 即可开始使用！

---

### 方式二：虚拟环境一站式部署模式

如果您希望在独立的隔离环境中运行项目，可以采用本模式：

```powershell
cd backend
# 1. 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 2. 直接安装核心第三方依赖与 AI 库（规避本地包发现打包问题）
pip install "deep-translator>=1.11.4" "fastapi>=0.111.0" "pydantic-settings>=2.2.1" "sqlalchemy>=2.0.30" "uvicorn[standard]>=0.29.0" "faster-whisper>=1.0.0"

# 3. 启动一站式服务
python -m uvicorn app.main:app --host 127.0.0.1 --port 19000
```

---

### 方式三：前后端独立开发调试模式

如果您需要对前端代码进行实时热更新（HMR）调试，可以同时开启两个终端：

#### 1. 启动后端 API 服务
```powershell
cd backend
# 激活环境并启动
.venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 19001 --reload
```

#### 2. 启动前端 Vite 开发服务器
```powershell
cd frontend
# 安装依赖并运行
npm install
npm run dev
```
> 前端开发服务器运行在 `http://127.0.0.1:19000`，Vite 代理将 `/api` 和 `/health` 转发到后端 `19001`。

---

## 🔌 核心 API 接口说明

### 1. 项目与文件管理
```text
GET    /api/projects              获取本地所有绑定的项目列表
POST   /api/projects              创建或绑定一个本地文件夹项目
DELETE /api/projects/:id          删除指定项目
POST   /api/projects/:id/scan      对项目路径进行多媒体视频（.mkv/.mp4/.mov）增量扫描
POST   /api/projects/browse        打开本地文件夹选择对话框
```

### 2. 视频与物理资源操作
```text
GET    /api/projects/:id/media    获取指定项目下的所有视频列表
GET    /api/media/:id             获取指定视频的详细数据（包含大小、时长与当前状态）
POST   /api/media/:id/process     将指定视频投递至后台异步串行任务队列，触发语音识别和翻译
POST   /api/media/unload-gpu      一键卸载和释放 Whisper 占用的显存，归还系统
POST   /api/media/:id/export      按内容优先级策略（修改文 > 译文 > 原文）导出物理 SRT 文件
```

### 3. 后台任务监控
```text
GET    /api/jobs/media/:media_id  获取指定视频的处理任务列表（含进度、阶段、错误信息）
```

### 4. 字幕编辑
```text
GET    /api/subtitles/media/:media_id  获取指定视频的完整双语字幕列表
PATCH  /api/subtitles/:id              保存用户对单条字幕文本（edited_text）、起止时间戳的即时编辑
```

### 5. 模型与引擎信息
```text
GET    /api/models                获取 Whisper 模型列表、引擎可用性及 GPU 信息
```

---

## 📝 本地环境配置参数 (.env)

| 环境变量名 | 默认值 | 作用说明 | 推荐配置 |
|:---|:---|:---|:---|
| `V2S_HOST` | `127.0.0.1` | 后端服务监听的主机地址 | `127.0.0.1` |
| `V2S_PORT` | `19000` | 后端服务运行的端口号 | `19000` |
| `V2S_DB_PATH` | `./data/app.sqlite3` | SQLite 数据库物理文件的存储物理路径 | `./data/app.sqlite3` |
| `V2S_CACHE_DIR` | `./data/cache` | FFmpeg 提取的 16kHz 音频等临时缓存的存放物理路径 | `./data/cache` |
| `V2S_MODEL_ROOT` | `whisper_model`（项目根下） | Whisper 模型目录，支持相对路径或绝对路径 | 放入 `.pt` 或 CTranslate2 模型即可 |
| `V2S_OUTPUT_MODE` | `beside_video` | SRT 导出规则（beside_video：视频同级目录） | `beside_video` |
| `V2S_DEFAULT_SOURCE_LANG` | `auto` | 转录源语言 | `auto` |
| `V2S_DEFAULT_TARGET_LANG` | `zh-CN` | 翻译目标语言 | `zh-CN` |
| `V2S_WHISPER_MODEL` | `auto` | 模型选择（auto：自动扫描 whisper_model/ 目录） | `auto` |
| `V2S_WHISPER_DEVICE` | `auto` | 推理设备（auto：检测 CUDA → GPU，否则 CPU） | `auto` |
| `V2S_WHISPER_COMPUTE_TYPE` | `auto` | 计算精度（auto：GPU float16，CPU int8） | `auto` |

---

## 🔮 未来规划与路线图

- [ ] **容器化与 NAS 适配**：编写一键部署的 `Dockerfile` 与 `docker-compose.yml`，深度优化在 ZSpace 等 NAS 设备 CPU 环境下的转录速度。
- [ ] **多源翻译引擎**：除 Google Translate 外，接入 DeepL、OpenAI 以及本地 Ollama (如 Qwen2) 离线翻译接口。
- [ ] **音频波形波段可视化**：提供波段高保真缩略图，便于更精准地以拖拽形式微调时间戳起止毫秒。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 许可协议开源。
