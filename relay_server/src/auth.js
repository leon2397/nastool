// auth.js - API Key 权限中间件
// v7.0 新增：REST API 鉴权
// ─────────────────────────────────────────────────────────────────
// 权限体系
// ─────────────────────────────────────────────────────────────────
// 角色层级：admin > editor > viewer
// 每个角色包含：
//   admin  - 完全访问（设备/命令/部署/报告/文件 + API Key 管理）
//   editor - 设备/命令/部署/报告（无 API Key 管理权）
//   viewer - 只读（设备列表/报告，无命令/部署）
//
// 细粒度 perms 可覆盖 role 默认值（黑名单优先）
// ─────────────────────────────────────────────────────────────────

import { createHash, randomBytes } from 'crypto';
import { verifyApiKey, touchApiKey } from './db.js';

// ─── 角色默认权限 ──────────────────────────────────────

const ROLE_PERMISSIONS = {
  admin: ['devices:read', 'devices:write', 'devices:delete',
           'commands:read', 'commands:write', 'commands:delete',
           'reports:read', 'reports:write',
           'files:read', 'files:write', 'files:delete',
           'deployments:read', 'deployments:write', 'deployments:delete',
           'apikeys:read', 'apikeys:write', 'apikeys:delete'],
  editor: ['devices:read', 'devices:write',
            'commands:read', 'commands:write',
            'reports:read', 'reports:write',
            'files:read', 'files:write',
            'deployments:read', 'deployments:write'],
  viewer: ['devices:read', 'reports:read', 'files:read'],
};

// ─── 权限检查 ─────────────────────────────────────────

/**
 * 合并 role 默认权限 + 细粒度 perms
 * @param {object} keyRecord - api_keys 表行
 * @returns {string[]} 最终权限列表
 */
export function resolvePermissions(keyRecord) {
  const rolePerms = ROLE_PERMISSIONS[keyRecord.role] || ROLE_PERMISSIONS.viewer;
  const extra = JSON.parse(keyRecord.perms || '[]');
  return [...new Set([...rolePerms, ...extra])];
}

/**
 * 检查是否有指定权限
 */
export function hasPermission(keyRecord, perm) {
  if (keyRecord.role === 'admin') return true;
  const perms = resolvePermissions(keyRecord);
  return perms.includes(perm);
}

/**
 * 对请求进行 API Key 或 JWT 鉴权
 * 支持两种认证方式：
 *   1. X-API-Key header → API Key（用于第三方/脚本）
 *   2. Authorization: Bearer <token> → JWT（用于 GUI）
 * @param {object} req - Fastify 请求对象
 * @param {string} requiredPerm - 所需权限
 * @param {object} fastify - Fastify 实例（用于 JWT 验证）
 * @returns {{ ok: true, keyRecord: object|null, authType: string }}
 */
export async function authenticate(req, requiredPerm, fastify) {
  const keyId  = req.headers['x-api-key'] || req.headers['x-nastools-key'];
  const bearer = req.headers['authorization'];

  // 允许不携带任何凭证访问的路径
  const publicPaths = ['/health', '/api/v1/auth/login'];
  if (!keyId && !bearer && publicPaths.some(p => req.url.startsWith(p))) {
    return { ok: true, keyRecord: null, bypass: true };
  }

  // ─── 方式1：API Key ─────────────────────────────
  if (keyId) {
    const keyRecord = await verifyApiKey(keyId);
    if (!keyRecord) {
      return { ok: false, status: 401, message: 'Invalid or expired API Key' };
    }

    if (requiredPerm && !hasPermission(keyRecord, requiredPerm)) {
      return { ok: false, status: 403, message: `Insufficient permission: requires ${requiredPerm}` };
    }

    touchApiKey(keyRecord.key_id).catch(() => {});
    return { ok: true, keyRecord, authType: 'apikey' };
  }

  // ─── 方式2：JWT Bearer Token ────────────────────
  if (bearer && bearer.startsWith('Bearer ')) {
    const token = bearer.slice(7);
    try {
      const decoded = fastify.jwt.verify(token);
      if (decoded.type !== 'gui') {
        return { ok: false, status: 401, message: 'Invalid token type' };
      }
      // JWT 用户天然拥有 admin 全部权限
      return {
        ok: true,
        keyRecord: { role: 'admin', perms: '[]' },
        authType: 'jwt',
        user: decoded,
      };
    } catch {
      return { ok: false, status: 401, message: 'Invalid or expired JWT token' };
    }
  }

  return { ok: false, status: 401, message: 'Missing credentials (X-API-Key or Bearer token)' };
}

// ─── Fastify 装饰器：auth 钩子 ─────────────────────────

/**
 * 为 Fastify 路由注册鉴权钩子
 * @param {object} fastify - Fastify 实例
 * @param {Map} routePermissions - 路由路径 → 所需权限 映射
 */
export function registerAuth(fastify, routePermissions) {
  // 全局 preHandler：每个请求都走这里
  fastify.addHook('preHandler', async (req, reply) => {
    const url = req.url.split('?')[0];

    // 查找所需权限（支持前缀匹配）
    let requiredPerm = null;
    for (const [prefix, perm] of routePermissions) {
      if (url.startsWith(prefix)) { requiredPerm = perm; break; }
    }

    // 无需鉴权的路径直接放行
    if (!requiredPerm) return;

    const result = await authenticate(req, requiredPerm, fastify);
    if (!result.ok) {
      reply.code(result.status).send({ error: result.message });
      return;
    }

    // 将 keyRecord 注入 req，方便路由处理器使用
    req.apiKeyRecord = result.keyRecord;
    req.authType = result.authType;
  });
}

// ─── API Key 创建工具 ─────────────────────────────────

/**
 * 生成 API Key
 * @param {string} prefix - 前缀（如 'nt_'）
 * @param {number} byteLen - 随机字节数
 * @returns {{ keyId: string, keySecret: string, keyHash: string }}
 *   - keyId     : 公开 ID，可泄露（如 'nt_abc123DE'）
 *   - keySecret : 完整密钥，仅创建时返回一次
 *   - keyHash   : SHA-256 哈希值，存入数据库
 */
export function generateApiKey(prefix = 'nt_', byteLen = 24) {
  const randomPart = randomBytes(byteLen).toString('base64url');
  const keySecret = `${prefix}${randomPart}`;
  const keyId = prefix + randomPart.slice(0, 8);  // 公开 ID 取前 8 字符
  const keyHash = createHash('sha256').update(keySecret).digest('hex');
  return { keyId, keySecret, keyHash };
}

// ─── 辅助：权限标签 ───────────────────────────────────

export const PERM_LABELS = {
  'devices:read':    '查看设备',
  'devices:write':   '管理设备',
  'devices:delete':  '删除设备',
  'commands:read':  '查看命令',
  'commands:write':  '下发命令',
  'commands:delete': '删除命令',
  'reports:read':   '查看报告',
  'reports:write':  '写入报告',
  'files:read':     '读取文件',
  'files:write':    '写入文件',
  'files:delete':   '删除文件',
  'deployments:read':   '查看部署',
  'deployments:write':  '创建部署',
  'deployments:delete': '删除部署',
  'apikeys:read':    '查看 API Key',
  'apikeys:write':   '创建 API Key',
  'apikeys:delete':  '删除 API Key',
};

export { ROLE_PERMISSIONS };
