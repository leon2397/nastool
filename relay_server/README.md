# nastools Relay Server v2.0.0

> WebSocket 中继服务器，用于 nastools v2.0 跨网远程管理 ARM NAS 设备

---

## 功能

- **Agent 管理**：通过 WebSocket 接收 ARM 设备注册，保持持久连接
- **命令转发**：GUI 下发命令 → Relay → Agent 执行 → 结果返回
- **报告接收**：Agent 上报检测结果 → Relay → 转发给 GUI
- **文件传输**：GUI 上传文件 → Relay → Agent 接收
- **离线补发**：Agent 断线重连后自动补发 pending 命令
- **部署管理**：远程触发 AI-NAS 部署

## 架构

```
nastools GUI ←──WS──→ Relay Server ←──WS──→ ARM Agent
   (客户端)          (18888)          (NAS设备)
```

## 快速启动

```bash
cd relay_server
npm install
cp .env.example .env
npm start
# 或开发模式
npm run dev
```

## REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | GUI 登录获取 JWT |
| GET | `/api/v1/devices` | 设备列表 |
| GET | `/api/v1/devices/:id` | 设备详情 |
| DELETE | `/api/v1/devices/:id` | 删除设备 |
| POST | `/api/v1/devices/:id/commands` | 下发命令 |
| GET | `/api/v1/devices/:id/commands/:cid` | 命令结果 |
| GET | `/api/v1/devices/:id/reports/latest` | 最新报告 |
| POST | `/api/v1/devices/:id/deploy` | 触发部署 |
| POST | `/api/v1/keys/generate` | 生成 agent_key |
| GET | `/api/v1/relay/status` | 服务状态 |
| GET | `/health` | 健康检查 |

## WebSocket 端点

| 端点 | 认证 | 用途 |
|------|------|------|
| `ws://host:18888/ws/agent?key=ak_xxx` | agent_key | Agent 连接 |
| `ws://host:18888/ws/gui?token=xxx` | JWT | GUI 连接 |

## 部署到 ECS

```bash
# 1. 上传代码到 ECS
scp -r relay_server root@120.77.249.3:/root/ai-nas/relay_server

# 2. 安装依赖
ssh root@120.77.249.3 "cd /root/ai-nas/relay_server && npm install --production"

# 3. 启动
ssh root@120.77.249.3 "cd /root/ai-nas/relay_server && pm2 start ecosystem.config.js"

# 4. 配置 Nginx 反向代理
# 添加 ws/agent, ws/gui, /api/v1 路由到 18888 端口
```

## 端口

| 端口 | 协议 | 说明 |
|------|------|------|
| 18888 | HTTP | REST API + WebSocket |
| 18889 | WSS | 加密 WebSocket（可选）|

## 默认凭据

| 项目 | 值 |
|------|------|
| GUI 用户 | admin |
| GUI 密码 | relay-admin-2026 |
| JWT 过期 | 7 天 |
