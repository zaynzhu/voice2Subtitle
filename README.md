# Voice2Subtitle 本地字幕工作站

Voice2Subtitle 是一个用于从本地视频文件生成、校对、编辑和导出字幕的单用户本地 Web 工作站。

**当前状态**：核心链路已全部打通（包含音频提取、Whisper 语音转录、机器翻译、串行后台任务队列及 SRT 字幕文件导出）。

---

## 🛠️ 技术栈与特性

- **后端**：基于 FastAPI、SQLAlchemy 与 SQLite (开启 WAL 模式) 提供数据持久化；
- **任务调度**：内置线程安全的 `JobQueue` 和常驻后台 `SerialProcessor` 串行执行繁重的媒体处理任务，避免阻塞 HTTP 线程；
- **语音转录**：基于 `faster-whisper`，支持模型懒加载以及 CPU (int8) / GPU (float16) 硬件自适应检测；
- **机器翻译**：集成 `deep-translator` (Google 翻译)，内置空文本过滤与单句异常隔离机制；
- **前端**：采用 React + Vite + TS 搭建的现代单页控制台，提供视频播放器预览、实时双语字幕编辑表格、任务状态及日志输出；
- **一站式部署**：支持将编译后的前端静态资源直接挂载到 FastAPI 服务下，实现单入口快速启动。

---

## 🚀 快速开始与开发调试

### 1. 后端服务

首次运行请确保创建了 Python 虚拟环境并安装了依赖：

```bash
cd backend
python -m venv .venv
# Windows 下激活虚拟环境：
.venv\Scripts\activate
# 安装核心依赖
pip install -r requirements.txt
# 安装额外的主依赖项
pip install deep-translator>=1.11.4 faster-whisper>=1.0.0
# 启动后端开发服务器
uvicorn app.main:app --host 127.0.0.1 --port 19000 --reload
```

后端默认监听端口：`http://127.0.0.1:19000`。

### 2. 前端服务

```bash
cd frontend
# 安装前端依赖
npm install
# 启动前端开发服务器
npm run dev
```

前端开发服务器将运行在 `http://127.0.0.1:5173`。Vite 配置了自动代理，所有请求将透明代理至后端的 `19000` 端口。

---

## 📦 一站式打包与本地部署

如果你希望像生产环境一样，只启动后端端口即可同时服务前端界面，可以运行以下命令：

```bash
# 1. 编译前端静态文件
cd frontend
npm run build

# 2. 启动 Uvicorn 即可（后端会自动扫描并挂载 frontend/dist 目录）
cd ../backend
uvicorn app.main:app --host 127.0.0.1 --port 19000
```
运行后，直接在浏览器中打开 `http://127.0.0.1:19000` 即可访问完整的工作站。

---

## ⚠️ 注意事项

以下运行时产生的较大文件、本地数据库和构建产物已被 Git 忽略：

- `backend/data/` (SQLite 数据库文件及音频缓存)
- `backend/models/` (本地下载的 Whisper 模型文件)
- `frontend/node_modules/` 与 `frontend/dist/`

原始的探索性单文件原型存放在 `E:\temp\测试翻译` 目录中。
