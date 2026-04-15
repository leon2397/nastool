// 数据库层 - sql.js (WASM, 无需编译)
import initSqlJs from 'sql.js';
import { createHash } from 'crypto';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
// 修复路径计算：从 src/ 目录往上一级到项目根目录
const DATA_DIR = join(__dirname, '../data');
const DB_PATH = join(DATA_DIR, 'relay.db');

console.log('[DB] __dirname:', __dirname);
console.log('[DB] DATA_DIR:', DATA_DIR);
console.log('[DB] DB_PATH:', DB_PATH);

let db = null;
let SQL = null;

// ─── 初始化 ────────────────────────────────────────────

export async function initDb() {
  if (db) return db;

  mkdirSync(DATA_DIR, { recursive: true });

  // WASM 路径：使用相对路径，兼容 Windows/Linux
  const sqlJsPath = new URL(
    '../node_modules/sql.js/dist/',
    import.meta.url
  ).href;

  SQL = await initSqlJs({
    locateFile: file => `${sqlJsPath}${file}`
  });

  // 加载已有数据库或新建
  if (existsSync(DB_PATH)) {
    const buffer = readFileSync(DB_PATH);
    db = new SQL.Database(buffer);
  } else {
    db = new SQL.Database();
  }

  initSchema();
  ensureDefaultAdmin();
  return db;
}

function saveDb() {
  if (!db) return;
  const data = db.export();
  const buffer = Buffer.from(data);
  writeFileSync(DB_PATH, buffer);
}

// ─── Schema ────────────────────────────────────────────

function initSchema() {
  db.run(`
    CREATE TABLE IF NOT EXISTS agents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      device_id TEXT UNIQUE NOT NULL,
      device_name TEXT NOT NULL DEFAULT '',
      device_type TEXT NOT NULL DEFAULT '',
      version TEXT NOT NULL DEFAULT '',
      hostname TEXT NOT NULL DEFAULT '',
      ip_local TEXT NOT NULL DEFAULT '',
      agent_key TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'offline',
      capabilities TEXT NOT NULL DEFAULT '[]',
      os_info TEXT NOT NULL DEFAULT '',
      arch TEXT NOT NULL DEFAULT '',
      python_version TEXT NOT NULL DEFAULT '',
      group_name TEXT NOT NULL DEFAULT 'default',
      registered_at INTEGER NOT NULL,
      last_seen INTEGER NOT NULL
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS sessions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT UNIQUE NOT NULL,
      device_id TEXT NOT NULL,
      ws_conn_id TEXT NOT NULL,
      connected_at INTEGER NOT NULL,
      disconnected_at INTEGER
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS commands (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      command_id TEXT UNIQUE NOT NULL,
      device_id TEXT NOT NULL,
      gui_session_id TEXT,
      cmd TEXT NOT NULL,
      timeout_ms INTEGER NOT NULL DEFAULT 30000,
      cwd TEXT NOT NULL DEFAULT '',
      env TEXT NOT NULL DEFAULT '{}',
      status TEXT NOT NULL DEFAULT 'pending',
      stdout TEXT NOT NULL DEFAULT '',
      stderr TEXT NOT NULL DEFAULT '',
      exit_code INTEGER,
      duration_ms INTEGER,
      created_at INTEGER NOT NULL,
      sent_at INTEGER,
      completed_at INTEGER
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS reports (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      report_id TEXT UNIQUE NOT NULL,
      device_id TEXT NOT NULL,
      overall_score INTEGER NOT NULL DEFAULT 0,
      categories TEXT NOT NULL DEFAULT '{}',
      items TEXT NOT NULL DEFAULT '[]',
      reported_at INTEGER NOT NULL
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS files (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      file_id TEXT UNIQUE NOT NULL,
      device_id TEXT NOT NULL,
      name TEXT NOT NULL,
      size INTEGER NOT NULL DEFAULT 0,
      path TEXT NOT NULL,
      mode TEXT NOT NULL DEFAULT '0644',
      checksum_sha256 TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'pending',
      created_at INTEGER NOT NULL
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS deployments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      deployment_id TEXT UNIQUE NOT NULL,
      device_id TEXT NOT NULL,
      version TEXT NOT NULL DEFAULT 'latest',
      config TEXT NOT NULL DEFAULT '{}',
      status TEXT NOT NULL DEFAULT 'pending',
      logs TEXT NOT NULL DEFAULT '[]',
      created_at INTEGER NOT NULL,
      completed_at INTEGER
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS agent_keys (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      agent_key TEXT UNIQUE NOT NULL,
      device_id TEXT,
      label TEXT NOT NULL DEFAULT '',
      created_at INTEGER NOT NULL,
      revoked_at INTEGER
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'admin',
      created_at INTEGER NOT NULL
    )
  `);

  // v7.0 新增：API Keys 表（细粒度权限）
  db.run(`
    CREATE TABLE IF NOT EXISTS api_keys (
      id           INTEGER PRIMARY KEY AUTOINCREMENT,
      key_id       TEXT UNIQUE NOT NULL,       -- 公开 ID（如 nastools_abc123）
      key_hash     TEXT UNIQUE NOT NULL,      -- SHA-256 哈希值存储
      label        TEXT NOT NULL DEFAULT '',
      role         TEXT NOT NULL DEFAULT 'viewer',  -- admin / editor / viewer
      perms        TEXT NOT NULL DEFAULT '[]', -- 细粒度权限列表
      rate_limit   INTEGER NOT NULL DEFAULT 0, -- 每分钟请求上限，0=不限
      expires_at   INTEGER,                     -- 过期时间戳，NULL=永不过期
      last_used    INTEGER,                     -- 最后使用时间
      created_at   INTEGER NOT NULL,
      revoked_at   INTEGER
    )
  `);

  // v7.1 新增：Agent OTA 版本表
  db.run(`
    CREATE TABLE IF NOT EXISTS agent_versions (
      id           INTEGER PRIMARY KEY AUTOINCREMENT,
      version      TEXT UN KEY NOT NULL,      -- 版本号，如 "2.1.0"
      download_url TEXT NOT NULL DEFAULT '',    -- OTA 包下载地址
      checksum_sha256 TEXT NOT NULL DEFAULT '', -- 包 SHA-256 校验
      file_size    INTEGER NOT NULL DEFAULT 0, -- 包大小（字节）
      release_date INTEGER NOT NULL,            -- 发布时间戳
      release_note TEXT NOT NULL DEFAULT '',   -- 更新说明
      min_version  TEXT NOT NULL DEFAULT '',    -- 最低兼容版本（空=无限制）
      device_types TEXT NOT NULL DEFAULT '[]',  -- 支持的设备类型列表
      status       TEXT NOT NULL DEFAULT 'stable', -- stable | beta | deprecated
      created_at   INTEGER NOT NULL
    )
  `);

  // 索引
  db.run(`CREATE INDEX IF NOT EXISTS idx_agents_device_id ON agents(device_id)`);
  db.run(`CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)`);
  db.run(`CREATE INDEX IF NOT EXISTS idx_commands_device_id ON commands(device_id)`);
  db.run(`CREATE INDEX IF NOT EXISTS idx_commands_status ON commands(status)`);
  db.run(`CREATE INDEX IF NOT EXISTS idx_reports_device_id ON reports(device_id)`);
  db.run(`CREATE INDEX IF NOT EXISTS idx_files_device_id ON files(device_id)`);

  saveDb();
}

// ─── 辅助：行转对象 ───────────────────────────────────

function rowsToObjects(stmt) {
  const columns = stmt.getColumnNames();
  const result = [];
  while (stmt.step()) {
    const row = stmt.get();
    const obj = {};
    columns.forEach((col, i) => { obj[col] = row[i]; });
    result.push(obj);
  }
  stmt.free();
  return result;
}

function rowToObject(stmt) {
  const result = rowsToObjects(stmt);
  return result[0] || null;
}

function exec(sql, params = []) {
  db.run(sql, params);
  saveDb();
}

// ─── Agent ────────────────────────────────────────────

export function upsertAgent(data) {
  const now = Date.now();
  const cols = ['device_id', 'device_name', 'device_type', 'version', 'hostname',
    'ip_local', 'agent_key', 'status', 'capabilities', 'os_info', 'arch',
    'python_version', 'registered_at', 'last_seen', 'group_name'];
  const vals = [data.device_id, data.device_name || '', data.device_type || '',
    data.version || '', data.hostname || '', data.ip_local || '', data.agent_key,
    'online', JSON.stringify(data.capabilities || []), data.os_info || '',
    data.arch || '', data.python_version || '', data.registered_at || now,
    now, data.group_name || 'default'];

  // 尝试插入，冲突则更新
  try {
    exec(`INSERT INTO agents (${cols.join(',')}) VALUES (${cols.map(() => '?').join(',')})`, vals);
  } catch {
    const sets = cols.filter(c => c !== 'device_id').map(c => `${c}=?`).join(',');
    const upVals = vals.filter((_, i) => cols[i] !== 'device_id');
    exec(`UPDATE agents SET ${sets} WHERE device_id=?`, [...upVals, data.device_id]);
  }
}

export function setAgentOffline(deviceId) {
  exec(`UPDATE agents SET status='offline' WHERE device_id=?`, [deviceId]);
}

export function getAgentByKey(agentKey) {
  const stmt = db.prepare(`SELECT * FROM agents WHERE agent_key=?`);
  stmt.bind([agentKey]);
  return rowToObject(stmt);
}

export function getAgent(deviceId) {
  const stmt = db.prepare(`SELECT * FROM agents WHERE device_id=?`);
  stmt.bind([deviceId]);
  return rowToObject(stmt);
}

export function getAllAgents() {
  const stmt = db.prepare(`SELECT * FROM agents ORDER BY last_seen DESC`);
  return rowsToObjects(stmt);
}

export function deleteAgent(deviceId) {
  exec(`DELETE FROM agents WHERE device_id=?`, [deviceId]);
}

// ─── Session ──────────────────────────────────────────

export function createSession(sessionId, deviceId, wsConnId) {
  exec(`INSERT INTO sessions (session_id, device_id, ws_conn_id, connected_at) VALUES (?,?,?,?)`,
    [sessionId, deviceId, wsConnId, Date.now()]);
}

export function closeSession(sessionId) {
  exec(`UPDATE sessions SET disconnected_at=? WHERE session_id=? AND disconnected_at IS NULL`,
    [Date.now(), sessionId]);
}

export function getOnlineAgents() {
  const stmt = db.prepare(`
    SELECT a.*, s.session_id, s.ws_conn_id, s.connected_at
    FROM agents a JOIN sessions s ON a.device_id=s.device_id
    WHERE a.status='online' AND s.disconnected_at IS NULL
  `);
  return rowsToObjects(stmt);
}

// ─── Command ──────────────────────────────────────────

export function createCommand(commandId, deviceId, guiSessionId, cmd, timeoutMs, cwd, env) {
  exec(`INSERT INTO commands (command_id, device_id, gui_session_id, cmd, timeout_ms, cwd, env, created_at)
    VALUES (?,?,?,?,?,?,?,?)`,
    [commandId, deviceId, guiSessionId, cmd, timeoutMs, cwd, JSON.stringify(env || {}), Date.now()]);
}

export function updateCommand(commandId, status, stdout, stderr, exitCode, durationMs) {
  const completedAt = ['completed', 'failed', 'timeout'].includes(status) ? Date.now() : null;
  exec(`UPDATE commands SET status=?, stdout=?, stderr=?, exit_code=?, duration_ms=?, completed_at=?
    WHERE command_id=?`,
    [status, stdout || '', stderr || '', exitCode, durationMs, completedAt, commandId]);
}

export function getPendingCommands(deviceId) {
  const stmt = db.prepare(`SELECT * FROM commands WHERE device_id=? AND status='pending' ORDER BY created_at ASC`);
  stmt.bind([deviceId]);
  return rowsToObjects(stmt);
}

export function getCommand(commandId) {
  const stmt = db.prepare(`SELECT * FROM commands WHERE command_id=?`);
  stmt.bind([commandId]);
  return rowToObject(stmt);
}

export function getCommandsByDevice(deviceId, limit = 50, offset = 0, status) {
  let sql = `SELECT * FROM commands WHERE device_id=? `;
  const params = [deviceId];
  if (status) { sql += `AND status=? `; params.push(status); }
  sql += `ORDER BY created_at DESC LIMIT ? OFFSET ?`;
  params.push(limit, offset);
  const stmt = db.prepare(sql);
  stmt.bind(params);
  return rowsToObjects(stmt);
}

// ─── Report ───────────────────────────────────────────

export function saveReport(reportId, deviceId, overallScore, categories, items, reportedAt) {
  exec(`INSERT INTO reports (report_id, device_id, overall_score, categories, items, reported_at)
    VALUES (?,?,?,?,?,?)`,
    [reportId, deviceId, overallScore, JSON.stringify(categories), JSON.stringify(items), reportedAt]);
}

export function getLatestReport(deviceId) {
  const stmt = db.prepare(`SELECT * FROM reports WHERE device_id=? ORDER BY reported_at DESC LIMIT 1`);
  stmt.bind([deviceId]);
  return rowToObject(stmt);
}

export function getReports(deviceId, limit = 20) {
  const stmt = db.prepare(`SELECT * FROM reports WHERE device_id=? ORDER BY reported_at DESC LIMIT ?`);
  stmt.bind([deviceId, limit]);
  return rowsToObjects(stmt);
}

// ─── File ─────────────────────────────────────────────

export function createFile(fileId, deviceId, name, size, path, mode, checksum) {
  exec(`INSERT INTO files (file_id, device_id, name, size, path, mode, checksum_sha256, created_at)
    VALUES (?,?,?,?,?,?,?,?)`,
    [fileId, deviceId, name, size, path, mode || '0644', checksum || '', Date.now()]);
}

export function updateFileStatus(fileId, status) {
  exec(`UPDATE files SET status=? WHERE file_id=?`, [status, fileId]);
}

export function getFile(fileId) {
  const stmt = db.prepare(`SELECT * FROM files WHERE file_id=?`);
  stmt.bind([fileId]);
  return rowToObject(stmt);
}

// ─── Deployment ───────────────────────────────────────

export function createDeployment(deploymentId, deviceId, version, config) {
  exec(`INSERT INTO deployments (deployment_id, device_id, version, config, created_at)
    VALUES (?,?,?,?,?)`,
    [deploymentId, deviceId, version, JSON.stringify(config), Date.now()]);
}

export function updateDeployment(deploymentId, status, logs) {
  const completedAt = ['completed', 'failed'].includes(status) ? Date.now() : null;
  exec(`UPDATE deployments SET status=?, logs=?, completed_at=? WHERE deployment_id=?`,
    [status, JSON.stringify(logs), completedAt, deploymentId]);
}

export function getDeployment(deploymentId) {
  const stmt = db.prepare(`SELECT * FROM deployments WHERE deployment_id=?`);
  stmt.bind([deploymentId]);
  return rowToObject(stmt);
}

// ─── Agent Key ────────────────────────────────────────

export function createAgentKey(agentKey, label) {
  exec(`INSERT INTO agent_keys (agent_key, label, created_at) VALUES (?,?,?)`,
    [agentKey, label, Date.now()]);
}

export function getAgentKey(agentKey) {
  const stmt = db.prepare('SELECT * FROM agent_keys WHERE agent_key=? AND revoked_at IS NULL');
  stmt.bind([agentKey]);
  return rowToObject(stmt);
}

export function revokeAgentKey(agentKey) {
  exec(`UPDATE agent_keys SET revoked_at=? WHERE agent_key=?`, [Date.now(), agentKey]);
}

// ─── API Key (v7.0) ───────────────────────────────────

/**
 * 创建 API Key
 * @param {string} keyId    - 公开 ID（如 nastools_abc123）
 * @param {string} keyHash  - SHA-256 哈希值
 * @param {string} label    - 标签
 * @param {string} role     - admin / editor / viewer
 * @param {string[]} perms  - 细粒度权限列表
 * @param {number} rateLimit - 每分钟请求上限
 * @param {number|null} expiresAt - 过期时间戳
 */
export function createApiKey(keyId, keyHash, label, role, perms, rateLimit, expiresAt) {
  exec(`INSERT INTO api_keys (key_id, key_hash, label, role, perms, rate_limit, expires_at, created_at)
    VALUES (?,?,?,?,?,?,?,?)`,
    [keyId, keyHash, label, role, JSON.stringify(perms || []), rateLimit || 0, expiresAt || null, Date.now()]);
}

/**
 * 验证 API Key（通过 keySecret 计算哈希后查找）
 * @param {string} keySecret - 原始密钥（完整字符串）
 * @returns {object|null} API Key 记录或 null
 */
export async function verifyApiKey(keySecret) {
  const keyHash = createHash('sha256').update(keySecret).digest('hex');
  const stmt = db.prepare(`
    SELECT * FROM api_keys
    WHERE key_hash=? AND revoked_at IS NULL
      AND (expires_at IS NULL OR expires_at > ?)
  `);
  stmt.bind([keyHash, Date.now()]);
  return rowToObject(stmt);
}

/**
 * 按 keyId 查询 API Key（元数据，不含 hash）
 */
export function getApiKeyMeta(keyId) {
  const stmt = db.prepare(`
    SELECT id, key_id, label, role, perms, rate_limit, expires_at,
           last_used, created_at, revoked_at
    FROM api_keys WHERE key_id=?
  `);
  stmt.bind([keyId]);
  return rowToObject(stmt);
}

/**
 * 查询所有 API Key（元数据，不含 hash）
 */
export function listApiKeys() {
  const stmt = db.prepare(`
    SELECT id, key_id, label, role, perms, rate_limit, expires_at,
           last_used, created_at, revoked_at
    FROM api_keys ORDER BY created_at DESC
  `);
  return rowsToObjects(stmt);
}

/**
 * 更新最后使用时间
 */
export function touchApiKey(keyId) {
  exec(`UPDATE api_keys SET last_used=? WHERE key_id=?`, [Date.now(), keyId]);
}

/**
 * 吊销 API Key
 */
export function revokeApiKey(keyId) {
  exec(`UPDATE api_keys SET revoked_at=? WHERE key_id=?`, [Date.now(), keyId]);
}

/**
 * 删除 API Key（物理删除）
 */
export function deleteApiKey(keyId) {
  exec(`DELETE FROM api_keys WHERE key_id=?`, [keyId]);
}

// ─── User ─────────────────────────────────────────────

export function getUser(username) {
  const stmt = db.prepare(`SELECT * FROM users WHERE username=?`);
  stmt.bind([username]);
  return rowToObject(stmt);
}

export function createUser(username, passwordHash) {
  exec(`INSERT INTO users (username, password_hash, created_at) VALUES (?,?,?)`,
    [username, passwordHash, Date.now()]);
}

export function ensureDefaultAdmin() {
  const stmt = db.prepare(`SELECT * FROM users WHERE username='admin'`);
  stmt.step(); // 检查是否存在
  if (!stmt.get()[0]) { // id 为 NULL 表示没数据
    stmt.free();
    createUser('admin', 'relay-admin-2026-hash');
  } else {
    stmt.free();
  }
}

// ─── OTA 版本管理 ────────────────────────────────────

/**
 * 获取最新可用版本（按 device_type + min_version 过滤）
 * @param {string} currentVersion - Agent 当前版本
 * @param {string} deviceType     - 设备类型（如 jetson / rk3588）
 * @returns {object|null} 最新版本记录
 */
export function getLatestAgentVersion(currentVersion, deviceType = 'generic') {
  // 取出所有 stable + beta，且 min_version <= currentVersion 的记录
  // 按 release_date DESC 排序
  const stmt = db.prepare(`
    SELECT version, download_url, checksum_sha256, file_size,
           release_date, release_note, min_version, device_types, status
    FROM agent_versions
    WHERE status IN ('stable', 'beta')
      AND (min_version = '' OR ? >= min_version)
      AND device_types LIKE ?
    ORDER BY
      CASE status WHEN 'stable' THEN 0 ELSE 1 END,
      release_date DESC
    LIMIT 1
  `);
  // device_types JSON 数组包含 deviceType
  stmt.bind([currentVersion, `%${deviceType}%`]);
  return rowToObject(stmt);
}

/**
 * 注册新 OTA 版本（Relay 管理接口调用）
 */
export function upsertAgentVersion(data) {
  const now = Date.now();
  const cols = ['version', 'download_url', 'checksum_sha256', 'file_size',
    'release_date', 'release_note', 'min_version', 'device_types', 'status', 'created_at'];
  const vals = [
    data.version, data.download_url || '', data.checksum_sha256 || '',
    data.file_size || 0, data.release_date || now,
    data.release_note || '', data.min_version || '',
    JSON.stringify(data.device_types || []),
    data.status || 'stable', now
  ];
  try {
    exec(`INSERT INTO agent_versions (${cols.join(',')}) VALUES (${cols.map(() => '?').join(',')})`, vals);
  } catch {
    const sets = cols.filter(c => c !== 'version').map(c => `${c}=?`).join(',');
    const upVals = vals.filter((_, i) => cols[i] !== 'version');
    exec(`UPDATE agent_versions SET ${sets} WHERE version=?`, [...upVals, data.version]);
  }
}

/**
 * 列出所有 OTA 版本
 */
export function listAgentVersions() {
  const stmt = db.prepare(`
    SELECT version, download_url, checksum_sha256, file_size,
           release_date, release_note, min_version, device_types, status, created_at
    FROM agent_versions ORDER BY release_date DESC
  `);
  return rowsToObjects(stmt);
}

/**
 * 删除旧版本
 */
export function deleteAgentVersion(version) {
  exec(`DELETE FROM agent_versions WHERE version=?`, [version]);
}

/**
 * 更新版本状态（stable / beta / deprecated）
 */
export function setAgentVersionStatus(version, status) {
  exec(`UPDATE agent_versions SET status=? WHERE version=?`, [status, version]);
}
