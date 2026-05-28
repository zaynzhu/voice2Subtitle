# 开发进度 - 2026-05-28

## 新增功能

### 视频播放器 + 实时字幕
- 新增 `GET /api/media/{id}/stream` 流式端点，使用 `FileResponse` 原生支持 HTTP Range 请求
- 前端用真实 `<video>` 元素替换播放器占位符，字幕通过 `timeupdate` 事件实时叠加
- 点击字幕行自动跳转视频到对应 `start_ms` 位置
- 支持双行字幕显示（主文本 + 原文参考）

### 任务取消
- 新增 `POST /api/jobs/cancel` 端点
- 后端通过 `threading.Event` 实现协作式取消，在流水线各阶段边界检查
- `JobCancelled` 异常标记任务为 `cancelled`（非 `failed`），同时清空队列并释放 GPU 显存
- 前端添加红色"终止任务"按钮

### 格式扩展
- 扫描器支持 14 种视频格式：`.mp4` `.mkv` `.mov` `.avi` `.wmv` `.flv` `.webm` `.ts` `.mpg` `.mpeg` `.m4v` `.3gp` `.rmvb` `.rm`
- 流式端点支持 18 种格式（含音频：`.mp3` `.wav` `.aac` `.flac` `.m4a` `.ogg` `.wma`）

### UI 优化
- 字幕编辑表单紧凑化：原文改为只读，译文/最终文本 textarea 缩小
- 开始时间/结束时间字段合并为同一行
- 三列布局调整：中间和右侧自适应无上限，右侧略宽于中间
- `.log/` 目录加入 `.gitignore`

### 修复
- CORS origins 从 5173 修正为 19000（匹配 Vite 开发端口）
- 流式端点从手动 Range 处理改为 `FileResponse`（修复 `Response(content=generator)` 不支持生成器的 500 错误）
