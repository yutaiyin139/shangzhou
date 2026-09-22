# 异步任务模块 —— Celery + Redis

## 概述

本模块实现了基于 Celery + Redis 的异步任务队列，支持：

1. **工作流异步执行** —— 长时间运行的工作流可在后台执行
2. **Embedding 异步生成** —— 文档向量生成不阻塞上传流程
3. **定时任务** —— 自动清理、健康检查、统计
4. **WebSocket 推送** —— 实时进度通知

## 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Flask     │────▶│   Redis     │────▶│   Celery    │
│   Web App   │     │   Broker    │     │   Worker    │
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │                    │
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  SocketIO   │◀────│   Redis     │◀────│   Result    │
│  WebSocket  │     │   Pub/Sub   │     │   Backend   │
└─────────────┘     └─────────────┘     └─────────────┘
```

## 快速开始

### 1. 确保 Redis 运行

```bash
redis-server
```

### 2. 启动 Celery Worker

```bash
# 进入 backend 目录
cd backend

# 启动 Worker（处理所有队列）
celery -A tasks.celery_app worker --loglevel=info

# 或指定队列
celery -A tasks.celery_app worker --loglevel=info -Q workflow,embedding,scheduled
```

### 3. 启动 Celery Beat（定时任务）

```bash
celery -A tasks.celery_app beat --loglevel=info
```

### 4. 同时启动 Worker + Beat

```bash
celery -A tasks.celery_app worker -B --loglevel=info
```

### 5. 监控 Flower（可选）

```bash
celery -A tasks.celery_app flower --port=5555
```

## 任务列表

### 工作流任务 (`tasks/workflow_tasks.py`)

| 任务名称 | 说明 | 队列 |
|---------|------|------|
| `run_workflow_async` | 异步执行工作流 | workflow |
| `run_workflow_stream_async` | 异步流式执行工作流 | workflow |

### Embedding 任务 (`tasks/embedding_tasks.py`)

| 任务名称 | 说明 | 队列 |
|---------|------|------|
| `generate_embeddings_async` | 生成指定数据集的 Embedding | embedding |
| `generate_all_pending_embeddings` | 生成所有待处理的 Embedding | embedding |
| `generate_single_embedding` | 为单个分段生成 Embedding | embedding |

### 定时任务 (`tasks/scheduled.py`)

| 任务名称 | 说明 | 频率 |
|---------|------|------|
| `generate_pending_embeddings` | 生成待处理的 Embedding | 每 5 分钟 |
| `cleanup_expired_results` | 清理过期缓存 | 每天 3:00 |
| `cleanup_stale_workflow_runs` | 清理卡住的工作流 | 每天 4:00 |
| `health_check` | 系统健康检查 | 手动 |
| `daily_statistics` | 每日统计 | 手动 |

## API 端点

### 工作流异步 API

```
POST /api/workflows/<app_id>/run-async    —— 异步触发工作流
GET  /api/workflows/tasks/<task_id>        —— 查询任务状态
POST /api/workflows/tasks/<task_id>/cancel —— 取消任务
```

### Embedding 异步 API

```
POST /api/knowledge/datasets/<id>/generate-embeddings  —— 异步生成 Embedding
POST /api/knowledge/generate-all-embeddings            —— 批量生成所有 Embedding
GET  /api/knowledge/tasks/<task_id>                    —— 查询任务状态
GET  /api/knowledge/datasets/<id>/pending-count        —— 获取待处理数量
GET  /api/knowledge/pending-count-all                  —— 获取所有待处理数量
```

### 任务管理 API

```
GET  /api/tasks/<task_id>          —— 查询任务状态
POST /api/tasks/<task_id>/cancel   —— 取消任务
GET  /api/tasks/active             —— 获取活跃任务列表
GET  /api/tasks/scheduled/logs     —— 获取定时任务日志
GET  /api/tasks/health             —— 系统健康检查
```

## WebSocket 事件

连接 WebSocket 后，可以订阅以下事件：

```javascript
const socket = io();

// 订阅工作流进度
socket.emit('subscribe_workflow', {run_id: 'xxx'});
socket.on('workflow_progress', (data) => {
    console.log('工作流进度:', data);
});

// 订阅 Embedding 进度
socket.emit('subscribe_embedding', {dataset_id: 'xxx'});
socket.on('embedding_progress', (data) => {
    console.log('Embedding 进度:', data);
});

// 系统通知
socket.on('system_notification', (data) => {
    console.log('系统通知:', data);
});
```

## 配置

在 `tasks/celery_app.py` 中修改配置：

```python
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB_BROKER = 0
REDIS_DB_BACKEND = 1
```

或通过环境变量：

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=your_password  # 可选
```

## 故障排除

### Worker 无法启动

1. 检查 Redis 是否运行：`redis-cli ping`
2. 检查依赖是否安装：`pip install celery[redis]`
3. 检查日志：`celery -A tasks.celery_app worker --loglevel=debug`

### 任务执行失败

1. 检查 Worker 日志
2. 查询任务状态：`GET /api/tasks/<task_id>`
3. 检查 MySQL 连接

### 定时任务未执行

1. 检查 Beat 是否启动
2. 检查时区配置：`timezone='Asia/Shanghai'`
3. 检查日志：`celery -A tasks.celery_app beat --loglevel=debug`
