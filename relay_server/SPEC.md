# Relay Server API 规范

> 版本：v2.0 Phase 4-1
> 制定：2026-04-14
> 架构：WebSocket Relay + REST API

---

## 一、架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌──────────┐     WebSocket      ┌──────────┐     WebSocket   │
│  │  Agent   │ ←───────────────→ │  Relay   │ ←─────────────→ │
│  │ (NAS)    │   wss://relay/    │  Server  │  wss://relay/  │
│  └──────────┘    ws/agent        └──────────┘    ws/gui        │
│       ↑                                    ↑                     │
│       │          REST API (可选)            │                     │
│       └────────────────────────────────────┘                     │
│                                                                  │
│  ┌──────────┐                                                   │
│  │ nastools │   ←───  GUI 端通过 HTTP API 管理设备和下发命令     │
│  │   GUI    │                                                   │
│  └──────────┘                                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**核心设计原则：**
- Agent 主动连接 Relay（outbound），绕过 NAT/防火墙
- Relay 只做消息转发，不解析业务内容
- 命令通过队列持久化，断线重连后自动补发

---

## 二、WebSocket 协议

### 2.1 连接端点

| 端点 | 用途 | 认证 |
|------|------|------|
| `ws://host:18888/ws/agent` | Agent 连接 | `agent_key` 在 URL 参数 |
| `ws://host:18888/ws/gui` | GUI 连接 | `session_token` 在 URL 参数 |
| `wss://host:18889/ws/agent` | Agent 连接（加密）| 同上 |
| `wss://host:18889/ws/gui` | GUI 连接（加密）| 同上 |

### 2.2 Agent → Relay 消息格式

```json
{
  "type": "register | heartbeat | report | response | log",
  "id": "uuid-v4",
  "timestamp": 1713000000,
  "payload": { ... }
}
```

| type | 说明 | payload |
|------|------|---------|
| `register` | 设备注册 | `{device_id, device_name, device_type, version, capabilities, hostname, ip_local}` |
| `heartbeat` | 心跳保活 | `{}` |
| `report` | 上报数据 | `{category, items: [{name, status, value, detail}]}` |
| `response` | 命令响应 | `{command_id, code, stdout, stderr, duration_ms}` |
| `log` | 实时日志 | `{level, message}` |
| `error` | 错误上报 | `{code, message}` |

### 2.3 GUI → Relay → Agent 消息格式

```json
{
  "type": "command | file | heartbeat | disconnect",
  "id": "uuid-v4",
  "timestamp": 1713000000,
  "target": "device_id",
  "payload": { ... }
}
```

| type | 说明 | payload |
|------|------|---------|
| `command` | 执行命令 | `{command_id, cmd, timeout_ms, cwd, env}` |
| `file` | 文件传输 | `{file_id, name, size, content_base64, path}` |
| `heartbeat` | 心跳 | `{}` |
| `disconnect` | 断开设备 | `{device_id, reason}` |

### 2.4 消息流程

```
【设备上线】
Agent → register → Relay
Relay → 存储 device → 分配 session_id → Agent

【下发命令】
GUI → command{cmd:"df -h"} → Relay
Relay → 写入 cmd_queue → 转发 → Agent
Agent → 执行 → response → Relay
Relay → 写入 cmd_history → 转发 → GUI

【上报检测结果】
Agent → report{category:"storage", items:[...]} → Relay
Relay → 存储 history → 转发 → GUI（如在线）

【离线补发】
Agent 重连 → register → Relay
Relay → 查找 pending_cmds → 补发 → Agent
```

### 2.5 心跳与超时

| 参数 | 值 | 说明 |
|------|-----|------|
| `heartbeat_interval` | 30s | Agent/GUI 发送心跳间隔 |
| `read_timeout` | 90s | 超过此时间无消息则断开 |
| `reconnect_delay` | 5s | Agent 重连延迟（指数退避）|

---

## 三、REST API

基础路径：`http://120.77.249.3:18888/api/v1`

### 3.1 设备管理

#### GET /devices
获取已注册设备列表

**响应：**
```json
{
  "devices": [
    {
      "device_id": "jellyfin-nas-001",
      "device_name": "客厅NAS",
      "device_type": "synology_ds920p",
      "version": "3.0.7",
      "status": "online",
      "hostname": "DS920P",
      "ip_local": "192.168.1.100",
      "last_seen": 1713000000,
      "registered_at": 1712000000,
      "capabilities": ["storage", "network", "ai", "security"],
      "group": "default"
    }
  ],
  "total": 1,
  "online": 1
}
```

#### GET /devices/{device_id}
获取单个设备详情

#### DELETE /devices/{device_id}
删除设备（断开连接，清除注册信息）

---

### 3.2 命令管理

#### POST /devices/{device_id}/commands
向设备下发命令

**请求：**
```json
{
  "cmd": "df -h",
  "timeout_ms": 30000,
  "cwd": "/root",
  "env": {}
}
```

**响应：**
```json
{
  "command_id": "cmd_abc123",
  "device_id": "jellyfin-nas-001",
  "status": "queued",
  "created_at": 1713000000,
  "estimated_time_ms": 5000
}
```

#### GET /devices/{device_id}/commands/{command_id}
查询命令执行结果

**响应：**
```json
{
  "command_id": "cmd_abc123",
  "device_id": "jellyfin-nas-001",
  "status": "completed",
  "cmd": "df -h",
  "stdout": "Filesystem      Size  Used Avail Use% Mounted on\n...",
  "stderr": "",
  "exit_code": 0,
  "duration_ms": 234,
  "created_at": 1713000000,
  "completed_at": 1713000234
}
```

#### GET /devices/{device_id}/commands
获取设备的命令历史

**Query 参数：**
- `limit` - 返回条数（默认50）
- `offset` - 偏移量
- `status` - 过滤状态（pending/completed/failed/timeout）

---

### 3.3 检测报告

#### GET /devices/{device_id}/reports/latest
获取最新检测报告

**响应：**
```json
{
  "device_id": "jellyfin-nas-001",
  "reported_at": 1713000000,
  "overall_score": 85,
  "categories": {
    "storage": {"score": 90, "status": "ok"},
    "network": {"score": 80, "status": "ok"},
    "system": {"score": 85, "status": "ok"},
    "security": {"score": 75, "status": "warning"},
    "ai": {"score": 100, "status": "ok"}
  },
  "items": [
    {
      "category": "storage",
      "name": "磁盘空间",
      "status": "ok",
      "value": "65%",
      "detail": "3.2TB / 4.8TB"
    }
  ]
}
```

#### GET /devices/{device_id}/reports
获取历史报告列表

#### GET /devices/{device_id}/reports/{report_id}
获取指定历史报告

---

### 3.4 文件传输

#### POST /devices/{device_id}/files/upload
上传文件到设备

**请求（multipart/form-data）：**
- `file` - 文件内容
- `path` - 目标路径（默认 `/tmp/`）
- `mode` - 文件权限（默认 `0644`）

**响应：**
```json
{
  "file_id": "file_xyz789",
  "device_id": "jellyfin-nas-001",
  "name": "arm_server.py",
  "size": 45678,
  "path": "/opt/ai-nas/arm_server.py",
  "status": "uploaded",
  "checksum_sha256": "abc123..."
}
```

#### GET /devices/{device_id}/files/download
从设备下载文件

**Query：** `path` - 设备上文件路径

---

### 3.5 部署管理

#### POST /devices/{device_id}/deploy
触发远程部署 AI-NAS

**请求：**
```json
{
  "version": "latest",
  "config": {
    "api_server": "https://qizhiainas.com",
    "device_name": "客厅NAS",
    "auto_start": true
  }
}
```

#### GET /devices/{device_id}/deploy/status
获取部署状态

---

### 3.6 管理接口

#### GET /relay/status
Relay Server 状态

**响应：**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime_seconds": 86400,
  "connections": {
    "agents": 3,
    "gui_clients": 1
  },
  "queue": {
    "pending_commands": 0,
    "pending_files": 0
  },
  "memory_mb": 128,
  "cpu_percent": 5.2
}
```

#### GET /health
健康检查（给 nginx 探活用）

---

## 四、WebSocket 消息示例

### 4.1 Agent 注册

```json
// Agent → Relay
{
  "type": "register",
  "id": "req_001",
  "timestamp": 1713000000,
  "payload": {
    "device_id": "jellyfin-nas-001",
    "device_name": "客厅NAS",
    "device_type": "synology_ds920p",
    "version": "3.0.7",
    "hostname": "DS920P",
    "ip_local": "192.168.1.100",
    "capabilities": ["storage", "network", "ai", "security", "nas"],
    "agent_key": "ak_xxxxxxxxxxxx",
    "os": "Linux 5.10.0 DSM 7.2",
    "arch": "x86_64",
    "python_version": "3.11.9"
  }
}

// Relay → Agent（注册成功）
{
  "type": "register_ack",
  "id": "req_001",
  "timestamp": 1713000001,
  "payload": {
    "session_id": "sess_abc123",
    "server_version": "2.0.0",
    "config": {
      "heartbeat_interval": 30,
      "read_timeout": 90,
      "max_command_timeout": 300000,
      "relay_url": "wss://relay.qizhiainas.com"
    }
  }
}
```

### 4.2 GUI 下发命令

```json
// GUI → Relay
{
  "type": "command",
  "id": "cmd_001",
  "timestamp": 1713001000,
  "target": "jellyfin-nas-001",
  "payload": {
    "command_id": "cmd_abc123",
    "cmd": "python3 /opt/ai-nas/arm_diagnose.py --full",
    "timeout_ms": 120000,
    "cwd": "/root",
    "env": {}
  }
}

// Relay → Agent（转发）
{
  "type": "command",
  "id": "cmd_001",
  "timestamp": 1713001001,
  "source": "gui_xxx",
  "payload": { ... }
}

// Agent → Relay（执行结果）
{
  "type": "response",
  "id": "cmd_001",
  "timestamp": 1713002000,
  "payload": {
    "command_id": "cmd_abc123",
    "code": 0,
    "stdout": "=== NAS 诊断报告 ===\n存储: OK\n网络: OK\n...",
    "stderr": "",
    "duration_ms": 9823
  }
}

// Relay → GUI（转发）
{
  "type": "response",
  "id": "cmd_001",
  "timestamp": 1713002001,
  "payload": { ... }
}
```

### 4.3 Agent 上报检测结果

```json
// Agent → Relay
{
  "type": "report",
  "id": "rpt_001",
  "timestamp": 1713000000,
  "payload": {
    "overall_score": 85,
    "categories": {
      "storage": {"score": 90, "status": "ok"},
      "network": {"score": 80, "status": "ok"},
      "system": {"score": 85, "status": "ok"},
      "security": {"score": 75, "status": "warning"},
      "ai": {"score": 100, "status": "ok"}
    },
    "items": [
      {
        "category": "storage",
        "name": "磁盘空间",
        "status": "ok",
        "value": "65%",
        "detail": "/dev/sda1: 3.2TB / 4.8TB"
      },
      {
        "category": "storage",
        "name": "SMART健康",
        "status": "ok",
        "value": "PASSED",
        "detail": "Model: WD40EFAX"
      }
    ]
  }
}

// Relay → GUI（如在线则转发）
{
  "type": "report",
  "id": "rpt_001",
  "timestamp": 1713000001,
  "source": "jellyfin-nas-001",
  "payload": { ... }
}
```

---

## 五、数据库设计（SQLite）

### 表：agents（注册设备）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| device_id | TEXT UNIQUE | 设备唯一标识（UUID或用户指定）|
| device_name | TEXT | 设备昵称 |
| device_type | TEXT | 设备型号 |
| version | TEXT | Agent 版本 |
| hostname | TEXT | 主机名 |
| ip_local | TEXT | 局域网IP |
| agent_key | TEXT | 设备密钥（注册时验证）|
| status | TEXT | online / offline |
| capabilities | TEXT | JSON数组 |
| registered_at | INTEGER | 注册时间戳 |
| last_seen | INTEGER | 最后活跃时间 |

### 表：sessions（在线会话）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| session_id | TEXT UNIQUE | 会话ID |
| device_id | TEXT FK | 关联设备 |
| ws_conn_id | TEXT | WebSocket 连接ID |
| connected_at | INTEGER | 连接时间 |
| disconnected_at | INTEGER | 断开时间（NULL表示在线）|

### 表：commands（命令队列）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| command_id | TEXT UNIQUE | 命令ID |
| device_id | TEXT FK | 目标设备 |
| gui_session_id | TEXT | 下令的GUI会话 |
| cmd | TEXT | 命令内容 |
| timeout_ms | INTEGER | 超时毫秒 |
| status | TEXT | pending / sent / completed / failed / timeout |
| stdout | TEXT | 标准输出 |
| stderr | TEXT | 标准错误 |
| exit_code | INTEGER | 退出码 |
| duration_ms | INTEGER | 执行时长 |
| created_at | INTEGER | 创建时间 |
| sent_at | INTEGER | 发送到Agent时间 |
| completed_at | INTEGER | 完成时间 |

### 表：reports（检测报告）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| report_id | TEXT UNIQUE | 报告ID |
| device_id | TEXT FK | 来源设备 |
| overall_score | INTEGER | 综合评分 |
| categories | TEXT | JSON |
| items | TEXT | JSON |
| reported_at | INTEGER | 上报时间 |

### 表：files（文件传输记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| file_id | TEXT UNIQUE | 文件ID |
| device_id | TEXT FK | 目标设备 |
| name | TEXT | 文件名 |
| size | INTEGER | 文件大小 |
| path | TEXT | 目标路径 |
| checksum_sha256 | TEXT | SHA256校验 |
| status | TEXT | pending / uploaded / failed |
| created_at | INTEGER | 创建时间 |

### 表：deployments（部署记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| deployment_id | TEXT UNIQUE | 部署ID |
| device_id | TEXT FK | 目标设备 |
| version | TEXT | 部署版本 |
| status | TEXT | pending / deploying / completed / failed |
| logs | TEXT | JSON 部署日志 |
| created_at | INTEGER | 创建时间 |
| completed_at | INTEGER | 完成时间 |

---

## 六、安全设计

### 6.1 Agent 认证

```
Agent 注册流程：
1. Agent 使用 agent_key（设备密钥）连接 ws/agent
2. Relay 验证 agent_key 有效性
3. 验证通过后分配 session_id，建立持久连接
```

- `agent_key` 格式：`ak_` + 32位随机字符
- 每个设备有独立 agent_key
- agent_key 可在 Relay Server 管理界面生成/撤销

### 6.2 GUI 认证

```
GUI 认证流程：
1. 用户在 nastools GUI 输入 Relay URL + 账户密码
2. Relay 验证，返回 session_token（JWT）
3. GUI 用 session_token 连接 ws/gui
```

- session_token 有效期：7天
- Refresh token 有效期：30天
- 支持账号：单个管理员账号（或对接 AI-NAS 用户系统）

### 6.3 通信安全

| 层级 | 方案 |
|------|------|
| Agent ↔ Relay | wss（TLS） |
| GUI ↔ Relay | wss（TLS）+ 证书 pinning |
| 敏感数据 | 命令内容端到端加密（可选）|
| Agent Key | 仅首次注册传输，后续存Relay |

---

## 七、部署架构

```
                    ┌──────────────────┐
                    │   阿里云 ECS      │
                    │   120.77.249.3   │
                    │                  │
  ┌──────────┐      │  ┌────────────┐  │
  │ nastools │──────│  │   Relay    │  │
  │   GUI    │ HTTPS│  │  Server    │  │
  └──────────┘      │  │  (18888)   │  │
                    │  │            │  │
  ┌──────────┐      │  │  ┌──────┐  │  │
  │ nastools │──────│  │  │SQLite│  │  │
  │   GUI    │ HTTPS│  │  │  DB  │  │  │
  └──────────┘      │  │  └──────┘  │  │
                    │  └────────────┘  │
                    └──────────────────┘
                           ↑
                    NAT / 公网
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────┴───┐  ┌────┴───┐  ┌────┴───┐
         │ Jetson │  │群晖NAS│  │ RK3588 │
         │ Agent  │  │ Agent │  │ Agent  │
         └────────┘  └────────┘  └────────┘
```

**Nginx 代理配置：**
```nginx
# Relay Server (WebSocket)
location /ws/agent {
    proxy_pass http://127.0.0.1:18888/ws/agent;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}

location /ws/gui {
    proxy_pass http://127.0.0.1:18888/ws/gui;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}

# REST API
location /api/v1 {
    proxy_pass http://127.0.0.1:18888/api/v1;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

# 健康检查
location /health {
    proxy_pass http://127.0.0.1:18888/health;
    proxy_http_version 1.1;
}
```

---

## 八、技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| **Runtime** | Node.js 20 LTS | WebSocket 原生支持，部署简单 |
| **Framework** | Fastify | 高性能，比 Express 快 2x |
| **WebSocket** | @fastify/websocket | 集成在 Fastify 内 |
| **数据库** | SQLite | 轻量，无需额外部署 |
| **ORM** | better-sqlite3 | 同步API，简单直接 |
| **JWT** | @fastify/jwt | 集成在 Fastify 内 |
| **日志** | pino | Fastify 默认，高性能 |
| **进程管理** | PM2 | 已有，熟悉 |
| **端口** | 18888（HTTP）/ 18889（HTTPS WSS）| |

---

## 九、Agent 端（嵌入式）

Agent 端代码嵌入 nastool，作为可选模块：

```
nastool/
├── relay/
│   ├── agent.py          # Agent 主程序
│   ├── config.py         # 配置管理
│   ├── protocol.py       # WebSocket 协议
│   └── installer.py      # 一键安装脚本
└── arm_diagnose.py      # 修改：增加 --relay 参数
```

**Agent 工作流程：**
1. nastools 部署时询问"是否启用远程管理"
2. 用户同意 → 生成 agent_key → 下载安装脚本
3. Agent 在 NAS 上运行，保持连接 Relay
4. nastools 后续可通过 Relay 远程管理

---

## 十、CLI 管理工具（可选）

```bash
# 管理已注册设备
relay-cli devices list
relay-cli devices info <device_id>
relay-cli devices remove <device_id>

# 管理 agent_key
relay-cli keys generate <device_name>
relay-cli keys revoke <key>

# 查看状态
relay-cli status
relay-cli connections

# 查看命令历史
relay-cli logs <device_id> --limit 50
```

---

*规范版本：v1.0*
*制定日期：2026-04-14*
*下一步：用户确认后开始写代码*
