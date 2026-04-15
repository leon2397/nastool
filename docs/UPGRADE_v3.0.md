# nastools V3.0 升级计划

**制定日期：** 2026-04-14
**当前版本：** nastool 3.0.7 + nastools_pkg 1.0.2 + relay_server 2.0.0
**目标版本：** nastools V3.0.0（一站式套件）

---

## 一、现状分析

### 1.1 组件现状

| 组件 | 当前版本 | 代码规模 | 状态 |
|------|----------|----------|------|
| **nastool** (ARM诊断引擎) | 3.0.7 | 106文件，~17K行 | 🟢 成熟 |
| **nastools_pkg** (Windows GUI) | 1.0.2 | 40+文件，~8K行 | 🟡 基础可用 |
| **relay_server** (中继服务器) | 2.0.0 | Node.js，~3K行 | 🟡 协议完整，代码未验证 |
| **Agent** (ARM端中继客户端) | 2.0.0 | ~600行 | 🔴 不完整/未测试 |

### 1.2 架构演进

```
V1.x 架构（当前主流）
┌──────────────┐      SSH       ┌──────────────┐
│ nastools_pkg │ ←───────────→  │  ARM 设备     │
│  (Windows)   │   同一局域网     │  nastool     │
└──────────────┘               └──────────────┘

V2.x 架构（已设计，未上线）
┌──────────────┐   WebSocket   ┌────────────┐   WebSocket   ┌──────────────┐
│ nastools_pkg │ ←───────────→ │ Relay      │ ←───────────→ │  ARM 设备    │
│  (Windows)   │   公网        │ Server     │   公网        │  Agent       │
└──────────────┘               └────────────┘               └──────────────┘

V3.0 目标架构（一体化）
┌──────────────┐   HTTPS/WSS   ┌────────────┐   WebSocket   ┌──────────────┐
│ Web Dashboard │ ←──────────→ │ Relay      │ ←───────────→ │  ARM 设备    │
│  (浏览器)      │   公网        │ Server     │   公网        │  nastool     │
└──────────────┘               └────────────┘               └──────────────┘
        ↕                              ↕
┌──────────────┐               ┌────────────┐
│ Mobile App   │               │ SQLite DB  │
│  (后续版本)   │               │ (持久化)    │
└──────────────┘               └────────────┘
```

---

## 二、V3.0 核心目标

| 目标 | 说明 | 优先级 |
|------|------|--------|
| **Relay Server 产品化** | 修复 bug，补充缺失模块，稳定部署到 ECS | P0 |
| **Web Dashboard** | 浏览器端管理界面，替代 Windows GUI | P0 |
| **Agent 完整集成** | nastool 内嵌 Agent，开机自启，自动上报 | P0 |
| **多设备舰队管理** | 同时管理多台 ARM NAS 设备 | P1 |
| **部署流水线** | 一键远程部署 + 自动验证 + 回滚 | P1 |
| **移动端适配** | 手机浏览器可用的响应式界面 | P2 |

---

## 三、P0 任务详解

### 3.1 Relay Server 补全 🔴

**当前状态：** `SPEC.md` 协议设计完整，但 `src/` 代码有多处缺失。

#### 待修复/补充的模块

| 模块 | 文件 | 问题 | 工作量 |
|------|------|------|--------|
| **数据库初始化** | `src/db.js` | 声明了 `initDb()` 但未读取 sql.js wasm 文件路径 | 0.5天 |
| **Agent WS 处理器** | `src/ws_handler.js` | 函数引用但文件缺失 | 1天 |
| **路由层** | `src/routes.js` | 函数声明但文件缺失 | 0.5天 |
| **Agent protocol** | `agent/protocol.py` | `MessageType` 枚举不完整 | 0.5天 |
| **Agent config** | `agent/config.py` | `AgentConfig.load()` 未实现 | 0.5天 |
| **心跳检测** | `src/ws_handler.js` | `startHeartbeat()` 未实现 | 0.5天 |
| **离线命令补发** | `src/ws_handler.js` | pending_cmds 队列未实现 | 1天 |
| **文件传输** | `agent/agent.py` | `handle_file_request()` 路径拼接有 bug | 0.5天 |
| **Agent 部署脚本** | `agent/installer.py` | 缺失 | 1天 |

#### relay_server/src/db.js 修复示例

```javascript
// 当前问题：sql.js wasm 文件路径未配置
// 修复方案：使用 jsDelivr CDN 或本地 copy

import initSqlJs from 'sql.js';

// 初始化数据库
async function initDb() {
  const SQL = await initSqlJs({
    // 推荐：从本地 static/ 加载（relay_server/static/sql-wasm.wasm）
    locateFile: file => `https://cdn.jsdelivr.net/npm/sql.js@1.10.3/dist/${file}`
  });
  // 完整实现见 scripts/fix_db.js
}
```

#### relay_server/src/ws_handler.js 骨架（缺失）

```javascript
// 需要实现的核心函数
export function handleAgentConnection(ws, req) { /* 注册/心跳/命令处理 */ }
export function handleGuiConnection(ws, req, decoded) { /* 订阅设备/接收报告 */ }
export function startHeartbeat(logger) { /* 每30s检查超时连接 */ }
```

**预计工作量：5.5 天**

---

### 3.2 Web Dashboard 🟡

**当前状态：** nastool/web/ 有 `index.html`（仪表盘），但：
- 没有后端 API 集成
- 没有 WebSocket 连接
- 没有真实数据展示

#### 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| **框架** | Vue 3 + Vite | 快速开发，组件化 |
| **UI 库** | Tailwind CSS | 定制化强，不需要笨重组件库 |
| **图表** | Chart.js | 轻量，趋势图够用 |
| **WebSocket** | 原生 WebSocket API | 简单够用 |
| **HTTP** | Axios | 请求拦截/统一错误处理 |

#### 页面规划

| 页面 | 路由 | 功能 |
|------|------|------|
| **登录** | `/login` | Relay 用户名/密码登录 |
| **设备列表** | `/devices` | 舰队总览，卡片展示 |
| **设备详情** | `/devices/:id` | 单台设备管理 |
| **诊断报告** | `/devices/:id/report` | 历史报告，趋势图 |
| **部署管理** | `/devices/:id/deploy` | 远程部署流水线 |
| **设置** | `/settings` | Agent Key 管理 |

#### 目录结构

```
web_dashboard/
├── src/
│   ├── views/
│   │   ├── Login.vue
│   │   ├── DeviceList.vue
│   │   ├── DeviceDetail.vue
│   │   ├── ReportView.vue
│   │   └── Settings.vue
│   ├── components/
│   │   ├── DeviceCard.vue
│   │   ├── HealthGauge.vue
│   │   ├── ReportTable.vue
│   │   ├── DeployPanel.vue
│   │   └── WSStatus.vue
│   ├── api/
│   │   ├── client.js       # Axios 实例
│   │   ├── auth.js          # 登录/刷新
│   │   ├── devices.js       # 设备 CRUD
│   │   └── relay.js         # Relay 状态
│   ├── websocket/
│   │   └── relay.js         # WebSocket 统一管理
│   ├── stores/
│   │   ├── auth.js          # Pinia: 登录状态
│   │   └── devices.js       # Pinia: 设备列表
│   └── router/
│       └── index.js
├── index.html
└── vite.config.js
```

**预计工作量：8 天**

---

### 3.3 Agent 完整集成 🟡

**当前状态：** `agent/agent.py` 骨架完整，但未在 nastool 中集成。

#### 集成方案

nastool/arm_diagnose.py 增加 `--relay` 参数：

```bash
# 启动 nastool 诊断 + 连接 Relay
python3 arm_diagnose.py --relay wss://relay.qizhiainas.com

# 后台常驻，连接 Relay 接受命令
python3 -m nastool.relay.agent --config /opt/nastool/relay.yaml
```

#### relay.yaml 配置

```yaml
relay_url: wss://relay.qizhiainas.com/ws/agent
agent_key: ak_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
device_id: auto          # 自动从设备信息生成
device_name: 自动获取     # 从 hostname 读取
device_type: auto        # 自动检测（jetson/rk3588/synology...）
capabilities:
  - storage
  - network
  - ai
  - security
  - nas
heartbeat_interval: 30    # 秒
reconnect_delay: 5        # 秒（指数退避，最大60s）
auto_report: true         # 诊断完成后自动上报
auto_diagnose_interval: 0 # 0=不自动巡检，3600=每小时
```

#### nastool 集成点

| 文件 | 改动 |
|------|------|
| `arm_diagnose.py` | 增加 `--relay` 参数，连接 Relay 并上报 |
| `relay/agent.py` | 重构为可导入模块（支持 `python -m` 调用）|
| `relay/config.py` | `AgentConfig.load()` 完整实现 |
| `relay/protocol.py` | `MessageType` 补全（含 DEPLOY 系列消息）|
| `relay/__init__.py` | 模块入口 |
| `config.yaml.example` | 增加 relay 配置项 |

#### 开机自启配置

```bash
# systemd 服务
[Unit]
Description=nastool Relay Agent v3.0
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /opt/nastool/relay/agent.py --config /opt/nastool/relay.yaml
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**预计工作量：6 天**

---

### 3.4 部署流水线 🔴

**当前状态：** `scripts/deploy.py` 有完整脚本，但未与 Relay 打通。

#### 目标流程

```
GUI 点击"部署"
    ↓
Relay 接收部署请求
    ↓
Relay 查询设备在线状态
    ├─ 在线 → 转发 deploy 命令到 Agent
    └─ 离线 → 入队，设备重连后自动补发
    ↓
Agent 执行部署脚本（本地 NAS_DEPLOY_SCRIPT）
    ↓
Agent 上报进度（deploy_progress）
    ↓
Agent 上报结果（deploy_result）
    ↓
GUI 实时显示进度条
    ↓
验证通过 → 完成
验证失败 → 自动回滚
```

#### Relay 新增端点

```
POST /api/v1/devices/{id}/deploy
  Body: { version, url, files[], config{} }
  → 写入 deployments 表
  → 如果在线：立即转发
  → 如果离线：pending_deploy 入队

GET /api/v1/devices/{id}/deploy/status
  → 返回 deployments 表中最新状态
```

#### Agent 部署状态机

```
IDLE → DOWNLOADING → EXTRACTING → CONFIGURING → RESTARTING → VERIFYING → DONE
                        ↓                                      ↓
                     ERROR ──────────────────────────────→ ROLLED_BACK
```

**预计工作量：5 天**

---

## 四、P1 任务

### 4.1 多设备舰队管理

| 功能 | 说明 |
|------|------|
| 设备分组 | 按位置/用途分组（客厅NAS、机房等）|
| 批量诊断 | 勾选多台设备，同时发起诊断 |
| 批量部署 | 选定版本，批量推送到多台设备 |
| 统一视图 | 所有设备健康状态一览 |
| 筛选/搜索 | 按状态/类型/名称筛选 |

### 4.2 通知系统

| 渠道 | 实现 |
|------|------|
| **Web Dashboard** | 实时通知（WebSocket 推送）|
| **邮件** | 部署完成/设备离线告警（nodemailer）|
| **微信** | 企业微信 webhook（可选）|

### 4.3 历史数据增强

- 诊断趋势图（折线图：健康分/存储/内存随时间变化）
- 设备对比（选两台设备，同一指标对比）
- 报告归档（标签/备注）

---

## 五、技术债务清理

### 5.1 代码质量

| 问题 | 现状 | 清理方案 |
|------|------|----------|
| **print() 残留** | 还有 `print()` 语句 | 全部替换为 logger |
| **tkinter 耦合** | notifications.py 依赖 tkinter | 抽取纯逻辑，GUI 层调用 |
| **SSH vs Relay 混合** | nastools_pkg 混用两种模式 | 统一为 Relay 模式，SSH 作为 fallback |
| **config.yaml 分散** | 多个配置文件 | 统一为 `/opt/nastool/config.yaml` |
| **版本号分散** | 3 处定义版本 | 统一为 `/opt/nastool/VERSION` |

### 5.2 测试覆盖

| 模块 | 当前测试 | V3.0 目标 |
|------|----------|-----------|
| nastool checks | ✅ 基础测试 | 28 项全覆 |
| relay_server | ❌ 无测试 | Jest 单元测试 |
| Agent | ❌ 无测试 | pytest 集成测试 |
| deploy scripts | ⚠️ 手动测试 | 自动化冒烟测试 |

### 5.3 安全审计

- [ ] Relay JWT secret 必须从环境变量读取（禁止硬编码默认值）
- [ ] Agent Key 生成使用 `secrets.token_urlsafe(32)`
- [ ] 命令执行增加黑名单（`rm -rf /`、`dd` 等危险命令过滤）
- [ ] SFTP 上传路径做 `realpath` 校验（禁止路径穿越）
- [ ] WebSocket 连接数限制（防 DoS）

---

## 六、数据结构

### 6.1 Relay Server 数据库（SQLite）

```sql
-- agents: 已注册设备（不变）
-- sessions: 在线会话（不变）
-- commands: 命令队列（不变）
-- reports: 检测报告（不变）

-- 新增表
CREATE TABLE IF NOT EXISTS fleets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS fleet_devices (
  fleet_id INTEGER REFERENCES fleets(id),
  device_id TEXT REFERENCES agents(device_id),
  PRIMARY KEY (fleet_id, device_id)
);

CREATE TABLE IF NOT EXISTS deployments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  deployment_id TEXT UNIQUE NOT NULL,
  device_id TEXT REFERENCES agents(device_id),
  version TEXT,
  status TEXT DEFAULT 'pending',
  progress INTEGER DEFAULT 0,
  logs TEXT,  -- JSON array
  error TEXT,
  created_at INTEGER DEFAULT (strftime('%s', 'now')),
  completed_at INTEGER
);

CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id TEXT REFERENCES agents(device_id),
  type TEXT,  -- offline/deploy_failed/health_critical
  title TEXT,
  message TEXT,
  read INTEGER DEFAULT 0,
  created_at INTEGER DEFAULT (strftime('%s', 'now'))
);
```

### 6.2 Relay API 新增端点

```
GET    /api/v1/fleets                    # 舰队列表
POST   /api/v1/fleets                    # 创建舰队
GET    /api/v1/fleets/:id                # 舰队详情
PUT    /api/v1/fleets/:id                # 更新舰队
DELETE /api/v1/fleets/:id                # 删除舰队
POST   /api/v1/fleets/:id/devices        # 添加设备到舰队
DELETE /api/v1/fleets/:id/devices/:did  # 从舰队移除设备

GET    /api/v1/notifications             # 通知列表
PUT    /api/v1/notifications/:id/read    # 标记已读
DELETE /api/v1/notifications/clean      # 清空已读

GET    /api/v1/devices/:id/history      # 设备历史（评分趋势）
POST   /api/v1/devices/:id/batch-cmd    # 批量命令（舰队用）
```

---

## 七、部署架构

### 7.1 ECS 部署

```
/root/ai-nas/
├── relay_server/         # Node.js 中继服务
│   ├── src/
│   ├── static/           # 前端静态文件
│   ├── data/             # SQLite 数据库
│   ├── logs/             # 日志
│   ├── ecosystem.config.js
│   └── package.json
│
├── web_dashboard/         # 前端构建产物
│   ├── dist/
│   └── (由 Vue 构建输出)
│
└── nastool/              # ARM 诊断工具（源码）
    ├── relay/            # Agent 模块（V3.0 新增）
    └── ...
```

### 7.2 Nginx 配置更新

```nginx
# Relay Server
location /ws/agent {
    proxy_pass http://127.0.0.1:18888/ws/agent;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}
location /ws/gui {
    proxy_pass http://127.0.0.1:18888/ws/gui;
    proxy_http_version 1.0;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}
location /api/v1 {
    proxy_pass http://127.0.0.1:18888/api/v1;
}
location /api/v1/keys/generate {
    proxy_pass http://127.0.0.1:18888/api/v1/keys/generate;
}

# Web Dashboard（静态文件）
location / {
    root /root/ai-nas/web_dashboard/dist;
    try_files $uri $uri/ /index.html;
}
```

---

## 八、测试计划

### 8.1 单元测试

| 模块 | 框架 | 覆盖目标 |
|------|------|----------|
| relay_server/src/db.js | Jest | SQL 执行、迁移 |
| relay_server/src/ws_handler.js | Jest | 消息路由、广播 |
| relay_server/src/routes.js | Supertest | REST API 端点 |
| nastool/checks/* | pytest | 各检测项逻辑 |
| nastool/relay/protocol.py | pytest | 消息序列化 |

### 8.2 集成测试

| 场景 | 工具 | 验证点 |
|------|------|--------|
| Agent 注册 Relay | 手动 + 脚本 | register_ack、session_id |
| 命令下发+执行 | curl + expect | response 正确返回 |
| 报告上报+转发 | python script | GUI 收到 report |
| 断线重连+补发 | kill -STOP | pending 命令补发 |
| 部署+验证+回滚 | 脚本自动化 | 全流程 |

### 8.3 冒烟测试清单

```bash
# 1. Relay Server 启动
pm2 start ecosystem.config.js
curl http://localhost:18888/health  # → {"status":"ok"}

# 2. Agent 连接
python3 agent/agent.py --config agent/relay.yaml &
# → [Agent] 已连接到 Relay
# → [Agent] 注册成功

# 3. GUI 登录
curl -X POST http://localhost:18888/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"relay-admin-2026"}'
# → {"token":"eyJ..."}

# 4. WebSocket 连接
wscat -c "ws://localhost:18888/ws/gui?token=<JWT>"
# → connected

# 5. 命令下发
curl -X POST http://localhost:18888/api/v1/devices/<id>/commands \
  -H "Authorization: Bearer <JWT>" \
  -d '{"cmd":"echo hello"}'
# → {"command_id":"cmd_xxx","status":"queued"}
```

---

## 九、里程碑

| 阶段 | 内容 | 预计时间 |
|------|------|----------|
| **V3.0 Alpha** | Relay Server 可用 + Agent 基础连接 | 3天 |
| **V3.0 Beta** | Web Dashboard 完成 + 部署流水线 | 7天 |
| **V3.0 RC** | 多设备管理 + 通知 + 测试完善 | 5天 |
| **V3.0 GA** | 安全审计 + 文档 + 打包发布 | 3天 |
| **总计** | | **18天** |

---

## 十、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| WebSocket 长连接稳定性 | 高 | 指数退避 + 心跳 + 重连 |
| ARM 设备网络不稳定 | 高 | 离线命令队列 + 断线补发 |
| 部署回滚逻辑复杂 | 中 | 先做端到端测试再上线 |
| 前端人力不足 | 中 | 使用现有 Vue 模板加速 |
| ECS 18888 端口暴露 | 中 | 配置防火墙 + agent_key 认证 |

---

## 十一、附录

### 11.1 V3.0 目录结构

```
C:\tools414\
├── nastool/                    # ARM 诊断工具
│   ├── relay/                   # 【新增】Agent 模块
│   │   ├── __init__.py
│   │   ├── agent.py            # 主程序（重构）
│   │   ├── config.py           # 配置管理
│   │   ├── protocol.py         # 消息协议
│   │   └── installer.py        # 一键安装
│   ├── checks/
│   ├── fixes/
│   ├── adapters/
│   └── arm_diagnose.py         # 增加 --relay 参数
│
├── nastools_pkg/               # Windows GUI（V3.0 降级为 Legacy）
│   └── (保持现有代码，V3.0 以 Web Dashboard 为主)
│
├── relay_server/               # Node.js 中继服务器
│   ├── src/
│   │   ├── index.js            # 补全 initDb + 心跳
│   │   ├── ws_handler.js       # 【重写】完整实现
│   │   ├── routes.js           # 【重写】完整实现
│   │   └── db.js              # 【修复】sql.js wasm 路径
│   ├── static/
│   │   └── sql-wasm.wasm      # 【新增】sql.js wasm 文件
│   ├── agent/                  # 【移动】ARM Agent 安装脚本
│   ├── web_dashboard/          # 【新增】Vue 前端源码
│   └── package.json
│
└── docs/
    └── UPGRADE_v3.0.md        # 【新增】V3.0 升级指南
```

### 11.2 版本对应关系

| 组件 | V2.0 | V3.0 |
|------|------|------|
| nastool | 3.0.7 | 4.0.0 |
| nastools_pkg | 1.0.2 | 2.0.0 (Legacy) |
| relay_server | 2.0.0 | 3.0.0 |
| Agent | 2.0.0 | 3.0.0 |
| Web Dashboard | - | 1.0.0 |

> **注意：** V3.0 采用套件统一版本，全部为 **3.0.0**
