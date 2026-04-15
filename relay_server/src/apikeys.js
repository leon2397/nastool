// apikeys.js - API Key 管理路由
// v7.0 新增：GUI/API Key CRUD
// ─────────────────────────────────────────────────────────────────

import { randomBytes, createHash } from 'crypto';
import {
  createApiKey, listApiKeys, getApiKeyMeta,
  revokeApiKey, deleteApiKey
} from './db.js';
import { generateApiKey, PERM_LABELS, ROLE_PERMISSIONS } from './auth.js';

// ─── 工具 ─────────────────────────────────────────────

/** 生成随机字符串 */
function uid(len = 8) {
  return randomBytes(len).toString('base64url').slice(0, len);
}

/** 格式化的 Key 列表（不含敏感信息） */
function formatKey(key) {
  return {
    key_id:     key.key_id,
    label:      key.label || '',
    role:       key.role,
    perms:      JSON.parse(key.perms || '[]'),
    rate_limit: key.rate_limit || 0,
    expires_at: key.expires_at || null,
    last_used:  key.last_used || null,
    created_at: key.created_at,
    status:     key.revoked_at ? 'revoked' : 'active',
  };
}

// ─── 路由注册 ────────────────────────────────────────

export async function registerApiKeyRoutes(fastify) {

  // ─── 角色选项 ───────────────────────────────────
  fastify.get('/api/v1/apikeys/roles', async (req, reply) => {
    return {
      roles: Object.entries(ROLE_PERMISSIONS).map(([name, perms]) => ({
        name,
        perms,
        labels: Object.fromEntries(
          perms.map(p => [p, PERM_LABELS[p] || p])
        ),
      })),
      allPermissions: PERM_LABELS,
    };
  });

  // ─── 列出所有 Key ───────────────────────────────
  fastify.get('/api/v1/apikeys', async (req, reply) => {
    const keys = listApiKeys();
    return { keys: keys.map(formatKey), total: keys.length };
  });

  // ─── 创建 Key ────────────────────────────────────
  // POST /api/v1/apikeys
  // Body: { label, role, perms?, rate_limit?, expires_days? }
  fastify.post('/api/v1/apikeys', async (req, reply) => {
    const {
      label = '',
      role = 'viewer',
      perms = null,
      rate_limit = 0,
      expires_days = null,
    } = req.body || {};

    if (!['admin', 'editor', 'viewer'].includes(role)) {
      reply.code(400);
      return { error: 'Invalid role. Must be admin/editor/viewer' };
    }

    // 生成 Key
    const { keyId, keySecret, keyHash } = generateApiKey('nt_', 24);
    const expiresAt = expires_days
      ? Date.now() + expires_days * 86400 * 1000
      : null;

    createApiKey(keyId, keyHash, label, role, perms || [], rate_limit, expiresAt);

    return {
      success: true,
      // 完整密钥仅在此处返回一次，后续不再暴露
      key_id:    keyId,
      key_secret: keySecret,   // ⚠️ 仅此一次，务必保存
      label,
      role,
      perms: perms || [],
      rate_limit,
      expires_at: expiresAt,
      created_at: Date.now(),
    };
  });

  // ─── 吊销 Key ───────────────────────────────────
  // DELETE /api/v1/apikeys/:keyId
  fastify.delete('/api/v1/apikeys/:keyId', async (req, reply) => {
    const { keyId } = req.params;
    const meta = getApiKeyMeta(keyId);
    if (!meta) {
      reply.code(404);
      return { error: 'API Key not found' };
    }
    if (meta.revoked_at) {
      reply.code(400);
      return { error: 'API Key already revoked' };
    }
    revokeApiKey(keyId);
    return { success: true, key_id: keyId, revoked_at: Date.now() };
  });

  // ─── 永久删除 Key ───────────────────────────────
  // DELETE /api/v1/apikeys/:keyId/purge
  fastify.delete('/api/v1/apikeys/:keyId/purge', async (req, reply) => {
    const { keyId } = req.params;
    deleteApiKey(keyId);
    return { success: true, key_id: keyId };
  });

  // ─── 验证 Key（测试用） ─────────────────────────
  // GET /api/v1/apikeys/verify
  // Header: X-API-Key: nt_xxxxx
  fastify.get('/api/v1/apikeys/verify', async (req, reply) => {
    const { authenticate } = await import('./auth.js');
    const result = await authenticate(req, null, fastify);
    if (!result.ok) {
      reply.code(result.status);
      return { valid: false, error: result.message };
    }
    const { role, perms, key_id, label } = result.keyRecord || {};
    return {
      valid: true,
      key_id: key_id || null,
      label: label || '',
      role: role || 'unknown',
      perms: JSON.parse(perms || '[]'),
    };
  });
}
