# NASTool Relay Agent 部署 - 问题分析与解决方案

## 问题分析

### Relay Server v2.0.0 架构限制

Relay Server 的 agent 注册流程：

```
1. 创建 agent_key: POST /keys/generate { label: "nvidia-123" }
   → agent_keys 表插入记录，device_id=NULL

2. Agent WebSocket 连接: ws://relay/ws/agent?key=ak_xxx
   → handleAgentConnection() 从 agent_keys 表读取 agent_key
   → agent.device_id = NULL
   → agentPool.set(NULL, { socket, ... })  ← key 是 NULL
   → upsertAgent({ device_id: NULL, ... })  ← agents 表 device_id=NULL

3. REST API 发送命令: POST /devices/test-e2e-agent/commands
   → isAgentOnline("test-e2e-agent") → agentPool.has("test-e2e-agent") → false
   → 命令状态=queued（不会转发给 agent）
```

**根因**: `POST /keys/generate` 的 `createAgentKey(agentKey, label)` 不接受 device_id 参数，
而 `handleAgentConnection` 只从 agent_keys 表读 device_id，不从 agent WebSocket 消息中读。

### 数据库表结构

```sql
-- agent_keys 表（有 device_id 列，但从未被填充）
CREATE TABLE agent_keys (
  id INTEGER PRIMARY KEY,
  agent_key TEXT UNIQUE NOT NULL,
  device_id TEXT,          ← 始终为 NULL
  label TEXT,
  created_at INTEGER,
  revoked_at INTEGER
);
```

## 可行方案

### 方案A: 修改 Relay Server 代码（需要 ECS 访问权限）

**用户明确禁止修改 ECS 文件，不可行。**

### 方案B: 直连 SSH（不通过 Relay）

如果云电脑能直接 SSH 到 192.168.1.123（通过 VPN/跳板机），可以直接运行 nastool 诊断。

**可行性取决于网络打通方式。**

### 方案C: 修改 Relay Server 的 POST /keys/generate 接受 device_id

只需要改一行代码：
```javascript
// routes.js - POST /keys/generate
// 原: createAgentKey(agentKey, label);
// 改: createAgentKey(agentKey, label, deviceId);
```

以及 db.js:
```javascript
// 原: INSERT INTO agent_keys (agent_key, label, created_at) VALUES (?,?,?)
// 改: INSERT INTO agent_keys (agent_key, label, device_id, created_at) VALUES (?,?,?,?)
```

**用户明确禁止修改 ECS 文件，不可行。**

### 方案D: 在 192.168.1.123 上运行独立的 HTTP 诊断服务

不依赖 Relay，直接在 192.168.1.123 上启动一个 HTTP API 服务，
云电脑通过公网 IP（如果有的话）或内网穿透访问。

**需要 192.168.1.123 有公网 IP 或内网穿透工具。**

### 方案E: 在 Relay Server 上更新 agent_keys 表（SQL 操作）

如果能访问 Relay Server 的 SQLite 数据库文件（relay.db），直接执行：
```sql
UPDATE agent_keys SET device_id = 'nvidia-123' WHERE agent_key = 'ak_xxx';
```

然后 agent 重新连接即可。

**需要 ECS 文件系统访问权限。**

## 建议

1. **联系 ECS 管理员**，请求更新 Relay Server 代码（一行改动）
2. **或者** 获取 ECS 的 SSH 访问权限，手动更新 agent_keys 表
3. **或者** 提供 VPN/跳板机，直接 SSH 到 192.168.1.123 运行 nastool

## 已验证的工作项

| 项目 | 状态 |
|------|------|
| Relay Server HTTP API | ✅ 可用（/health, /devices, /relay/status） |
| WebSocket 连接 | ✅ agent 可连接到 /ws/agent |
| agent_key 生成 | ✅ POST /keys/generate 可用 |
| agent 注册 | ✅ 连接后收到 agent:register 确认 |
| agents 表更新 | ✅ upsertAgent 写入 agents 表 |
| agentPool 注册 | ⚠️ key=NULL（因为 agent_keys.device_id=NULL） |
| 命令转发 | ❌ isAgentOnline 查不到设备 |
| 诊断执行 | ❌ 无法通过 Relay 下发命令 |
