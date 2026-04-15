// nastools Relay Server - 主入口
// v2.0.0
import Fastify from 'fastify';
import cors from '@fastify/cors';
import jwt from '@fastify/jwt';
import websocket from '@fastify/websocket';
import { initDb } from './db.js';
import { handleAgentConnection, handleGuiConnection, startHeartbeat } from './ws_handler.js';
import { registerDeviceRoutes } from './routes.js';
// v7.0 新增：API Key 鉴权
import { registerAuth } from './auth.js';
import { registerApiKeyRoutes } from './apikeys.js';

const PORT = process.env.PORT || 18888;
const HOST = process.env.HOST || '0.0.0.0';
const JWT_SECRET = process.env.JWT_SECRET || 'nastools-relay-secret-2026';
const GUI_USER = process.env.GUI_USER || 'admin';
const GUI_PASS = process.env.GUI_PASS || 'relay-admin-2026';

const fastify = Fastify({
  logger: {
    level: process.env.LOG_LEVEL || 'info',
    transport: process.env.NODE_ENV === 'development' ? {
      target: 'pino-pretty',
      options: { colorize: true }
    } : undefined
  }
});

async function start() {
  // ─── 初始化数据库 ─────────────────────────────────
  await initDb();
  fastify.log.info('Database initialized');

  // ─── 插件 ────────────────────────────────────────
  await fastify.register(cors, { origin: true, credentials: true });
  await fastify.register(jwt, { secret: JWT_SECRET });
  await fastify.register(websocket);

  // ─── GUI 认证 ───────────────────────────────────
  fastify.post('/api/v1/auth/login', async (req, reply) => {
    const { username, password } = req.body || {};
    if (username !== GUI_USER || password !== GUI_PASS) {
      reply.code(401);
      return { error: 'Invalid credentials' };
    }
    const token = fastify.jwt.sign({ sub: username, role: 'admin', type: 'gui' }, { expiresIn: '7d' });
    return { token, expires_in: 7 * 24 * 3600 };
  });

  // ─── REST API ───────────────────────────────────
  await registerDeviceRoutes(fastify);

  // ─── API Key 管理路由（需 admin 权限）────────────
  await registerApiKeyRoutes(fastify);

  // ─── API Key 鉴权中间件 ─────────────────────────
  // 路由前缀 → 所需权限
  const routePermissions = new Map([
    ['/api/v1/devices',       'devices:read'],
    ['/api/v1/commands',      'commands:read'],
    ['/api/v1/reports',       'reports:read'],
    ['/api/v1/files',         'files:read'],
    ['/api/v1/deployments',   'deployments:read'],
    ['/api/v1/apikeys',       'apikeys:read'],
  ]);
  registerAuth(fastify, routePermissions);

  // ─── WebSocket ──────────────────────────────────
  fastify.get('/ws/agent', { websocket: true }, (ws, req) => {
    handleAgentConnection(ws, req);
  });

  fastify.get('/ws/gui', { websocket: true }, async (ws, req) => {
    const url = new URL(req.url, 'http://localhost');
    const token = url.searchParams.get('token');
    if (!token) { ws.close(4001, 'Missing token'); return; }
    try {
      const decoded = fastify.jwt.verify(token);
      if (decoded.type !== 'gui') { ws.close(4002, 'Invalid token type'); return; }
      handleGuiConnection(ws, req, decoded);
    } catch {
      ws.close(4003, 'Invalid or expired token');
    }
  });

  // ─── 健康检查 ────────────────────────────────────
  fastify.get('/health', async () => ({ status: 'ok', server: 'nastools-relay', version: '2.0.0' }));

  // ─── 心跳检测 ────────────────────────────────────
  const stopHeartbeat = startHeartbeat(fastify.log);

  // ─── 启动 ────────────────────────────────────────
  await fastify.listen({ port: Number(PORT), host: HOST });
  fastify.log.info(`🚀 nastools Relay Server v2.0.0 on ${HOST}:${PORT}`);
  fastify.log.info(`   ws/agent: ws://${HOST}:${PORT}/ws/agent`);
  fastify.log.info(`   ws/gui:   ws://${HOST}:${PORT}/ws/gui`);
  fastify.log.info(`   REST:     http://${HOST}:${PORT}/api/v1`);

  const shutdown = async () => {
    fastify.log.info('Shutting down...');
    stopHeartbeat();
    await fastify.close();
    process.exit(0);
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

start().catch(err => { console.error(err); process.exit(1); });
