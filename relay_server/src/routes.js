// REST API 路由
import { v4 as uuidv4 } from 'uuid';
import {
  getAllAgents, getAgent, deleteAgent,
  getCommandsByDevice, getCommand,
  getLatestReport, getReports,
  getFile, getDeployment, createDeployment, updateDeployment,
  createAgentKey, getAgentKey, revokeAgentKey,
  getOnlineAgents,
  createFile as dbCreateFile
} from './db.js';

import { isAgentOnline, getAgentSocket, getRelayState } from './ws_handler.js';
import { sendJson, fileRequestMap } from './ws_handler.js';

// ─── 设备管理 ────────────────────────────────────────────

export async function registerDeviceRoutes(fastify) {

  // 获取设备列表
  fastify.get('/devices', async (req, reply) => {
    const agents = getAllAgents();
    const onlineIds = new Set([...getRelayState().agent_pool]);
    return {
      devices: agents.map(a => ({
        device_id: a.device_id,
        device_name: a.device_name,
        device_type: a.device_type,
        version: a.version,
        status: onlineIds.has(a.device_id) ? 'online' : 'offline',
        hostname: a.hostname,
        ip_local: a.ip_local,
        last_seen: a.last_seen,
        registered_at: a.registered_at,
        capabilities: JSON.parse(a.capabilities || '[]'),
        group: a.group || 'default'
      })),
      total: agents.length,
      online: [...onlineIds].filter(id => agents.some(a => a.device_id === id)).length
    };
  });

  // 获取单个设备
  fastify.get('/devices/:deviceId', async (req, reply) => {
    const agent = getAgent(req.params.deviceId);
    if (!agent) {
      reply.code(404);
      return { error: 'Device not found' };
    }
    const online = isAgentOnline(req.params.deviceId);
    return {
      ...agent,
      status: online ? 'online' : 'offline',
      capabilities: JSON.parse(agent.capabilities || '[]'),
    };
  });

  // 删除设备
  fastify.delete('/devices/:deviceId', async (req, reply) => {
    const agent = getAgent(req.params.deviceId);
    if (!agent) {
      reply.code(404);
      return { error: 'Device not found' };
    }
    deleteAgent(req.params.deviceId);
    return { success: true, message: 'Device removed' };
  });

  // ─── 命令管理 ──────────────────────────────────────────

  // 下发命令
  fastify.post('/devices/:deviceId/commands', async (req, reply) => {
    const { deviceId } = req.params;
    const { cmd, timeout_ms = 30000, cwd = '', env = {} } = req.body || {};

    if (!cmd) {
      reply.code(400);
      return { error: 'cmd is required' };
    }

    const commandId = `cmd_${uuidv4().replace(/-/g, '').slice(0, 16)}`;
    const agentOnline = isAgentOnline(deviceId);

    // 导入 db 模块来创建命令
    const { createCommand, updateCommand: dbUpdateCommand } = await import('./db.js');
    createCommand(commandId, deviceId, null, cmd, timeout_ms, cwd, env);

    if (agentOnline) {
      const agent = getAgentSocket(deviceId);
      dbUpdateCommand(commandId, 'sent', '', '', null, null);
      sendJson(agent.socket, {
        type: 'command',
        id: uuidv4(),
        timestamp: Date.now(),
        source: 'rest_api',
        payload: { command_id: commandId, cmd, timeout_ms, cwd, env }
      });
    }

    return {
      command_id: commandId,
      device_id: deviceId,
      status: agentOnline ? 'sent' : 'queued',
      created_at: Date.now()
    };
  });

  // 查询命令结果
  fastify.get('/devices/:deviceId/commands/:commandId', async (req, reply) => {
    const cmd = getCommand(req.params.commandId);
    if (!cmd) {
      reply.code(404);
      return { error: 'Command not found' };
    }
    return {
      command_id: cmd.command_id,
      device_id: cmd.device_id,
      status: cmd.status,
      cmd: cmd.cmd,
      stdout: cmd.stdout,
      stderr: cmd.stderr,
      exit_code: cmd.exit_code,
      duration_ms: cmd.duration_ms,
      created_at: cmd.created_at,
      completed_at: cmd.completed_at
    };
  });

  // 命令历史
  fastify.get('/devices/:deviceId/commands', async (req, reply) => {
    const { limit = 50, offset = 0, status } = req.query;
    const cmds = getCommandsByDevice(req.params.deviceId, Number(limit), Number(offset), status);
    return {
      commands: cmds.map(c => ({
        command_id: c.command_id,
        status: c.status,
        cmd: c.cmd,
        exit_code: c.exit_code,
        duration_ms: c.duration_ms,
        created_at: c.created_at,
        completed_at: c.completed_at
      })),
      total: cmds.length
    };
  });

  // ─── 报告管理 ─────────────────────────────────────────

  // 最新报告
  fastify.get('/devices/:deviceId/reports/latest', async (req, reply) => {
    const report = getLatestReport(req.params.deviceId);
    if (!report) {
      reply.code(404);
      return { error: 'No report found' };
    }
    return {
      device_id: report.device_id,
      report_id: report.report_id,
      reported_at: report.reported_at,
      overall_score: report.overall_score,
      categories: JSON.parse(report.categories || '{}'),
      items: JSON.parse(report.items || '[]')
    };
  });

  // 历史报告
  fastify.get('/devices/:deviceId/reports', async (req, reply) => {
    const { limit = 20 } = req.query;
    const reports = getReports(req.params.deviceId, Number(limit));
    return {
      reports: reports.map(r => ({
        report_id: r.report_id,
        overall_score: r.overall_score,
        reported_at: r.reported_at,
        categories: JSON.parse(r.categories || '{}')
      })),
      total: reports.length
    };
  });

  // ─── 部署管理 ─────────────────────────────────────────

  // 触发部署
  fastify.post('/devices/:deviceId/deploy', async (req, reply) => {
    const { deviceId } = req.params;
    const { version = 'latest', config = {} } = req.body || {};

    if (!isAgentOnline(deviceId)) {
      reply.code(400);
      return { error: 'Device is offline' };
    }

    const deploymentId = `dep_${uuidv4().replace(/-/g, '').slice(0, 16)}`;
    createDeployment(deploymentId, deviceId, version, config);

    const agent = getAgentSocket(deviceId);
    sendJson(agent.socket, {
      type: 'deploy',
      id: uuidv4(),
      timestamp: Date.now(),
      payload: { deployment_id: deploymentId, version, config }
    });

    return {
      deployment_id: deploymentId,
      device_id: deviceId,
      status: 'deploying',
      created_at: Date.now()
    };
  });

  // 部署状态
  fastify.get('/devices/:deviceId/deploy/:deploymentId/status', async (req, reply) => {
    const dep = getDeployment(req.params.deploymentId);
    if (!dep) {
      reply.code(404);
      return { error: 'Deployment not found' };
    }
    return {
      deployment_id: dep.deployment_id,
      device_id: dep.device_id,
      version: dep.version,
      status: dep.status,
      logs: JSON.parse(dep.logs || '[]'),
      created_at: dep.created_at,
      completed_at: dep.completed_at
    };
  });

  // ─── 文件传输 ──────────────────────────────────────────

  // 上传文件到设备
  fastify.post('/devices/:deviceId/files', async (req, reply) => {
    const { deviceId } = req.params;
    const { name, path = '/tmp/', mode = '0644', content_base64, checksum_sha256 = '' } = req.body || {};

    if (!name || !content_base64) {
      reply.code(400);
      return { error: 'name and content_base64 are required' };
    }

    if (!isAgentOnline(deviceId)) {
      reply.code(400);
      return { error: 'Device is offline' };
    }

    const fileId = `file_${uuidv4().replace(/-/g, '').slice(0, 16)}`;
    dbCreateFile(fileId, deviceId, name, Buffer.from(content_base64, 'base64').length, path, mode, checksum_sha256);

    const agent = getAgentSocket(deviceId);
    sendJson(agent.socket, {
      type: 'file',
      id: uuidv4(),
      timestamp: Date.now(),
      payload: {
        file_id: fileId,
        name,
        path,
        mode,
        content_base64,
        checksum_sha256
      }
    });

    return {
      file_id: fileId,
      device_id: deviceId,
      status: 'transferring',
      created_at: Date.now()
    };
  });

  // 请求设备下载文件（返回给 GUI）
  fastify.post('/devices/:deviceId/files/download', async (req, reply) => {
    const { deviceId } = req.params;
    const { path, encoding = 'base64' } = req.body || {};

    if (!path) {
      reply.code(400);
      return { error: 'path is required' };
    }

    if (!isAgentOnline(deviceId)) {
      reply.code(400);
      return { error: 'Device is offline' };
    }

    const fileRequestId = `freq_${uuidv4().replace(/-/g, '').slice(0, 16)}`;
    // 追踪请求方（通过 relay 前缀识别 REST API 请求）
    fileRequestMap.set(fileRequestId, `relay_${deviceId}`);

    const agent = getAgentSocket(deviceId);
    sendJson(agent.socket, {
      type: 'file_request',
      id: uuidv4(),
      timestamp: Date.now(),
      source: 'rest_api',
      payload: { file_request_id: fileRequestId, path, encoding }
    });

    // REST API 同步等待（最多 30s）
    return new Promise((resolve, reject) => {
      let timeout = setTimeout(() => {
        fileRequestMap.delete(fileRequestId);
        reject({ code: 504, message: 'Device timeout' });
      }, 30000);

      // 临时监听 file_response（通过 Agent 发回）
      // 注：REST API 同步等待需要特殊处理，这里简化为返回已转发
      resolve({
        file_request_id: fileRequestId,
        device_id: deviceId,
        status: 'requesting',
        message: '请求已下发，请通过 WebSocket 接收响应'
      });
    });
  });

  // ─── Agent Key 管理 ───────────────────────────────────

  // 生成 agent_key
  fastify.post('/keys/generate', async (req, reply) => {
    const { label = '' } = req.body || {};
    const agentKey = `ak_${uuidv4().replace(/-/g, '')}`;
    createAgentKey(agentKey, label);
    return { agent_key: agentKey, label, created_at: Date.now() };
  });

  // 撤销 agent_key
  fastify.delete('/keys/:agentKey', async (req, reply) => {
    const key = getAgentKey(req.params.agentKey);
    if (!key) {
      reply.code(404);
      return { error: 'Key not found or already revoked' };
    }
    revokeAgentKey(req.params.agentKey);
    return { success: true };
  });

  // ─── OTA 版本管理 ─────────────────────────────────────

  // 获取最新版本（Agent 调用，device_type 可选）
  fastify.get('/ota/version', async (req, reply) => {
    const { current_version = '0', device_type = 'generic' } = req.query;
    const { getLatestAgentVersion } = await import('./db.js');
    const latest = getLatestAgentVersion(String(current_version), String(device_type));
    if (!latest) {
      return {
        version: String(current_version),
        status: 'up_to_date',
        download_url: '',
        message: '已是最新版本'
      };
    }
    return {
      ...latest,
      is_newer: latest.version !== current_version
    };
  });

  // 列出所有 OTA 版本（仅 admin）
  fastify.get('/ota/versions', async (req, reply) => {
    const { getLatestAgentVersion, listAgentVersions } = await import('./db.js');
    const versions = listAgentVersions();
    return { versions, total: versions.length };
  });

  // 发布新版本（仅 admin）
  fastify.post('/ota/versions', async (req, reply) => {
    const { version, download_url, checksum_sha256, file_size,
            release_note, min_version, device_types, status = 'stable' } = req.body || {};
    if (!version || !download_url) {
      reply.code(400);
      return { error: 'version 和 download_url 必填' };
    }
    const { upsertAgentVersion } = await import('./db.js');
    upsertAgentVersion({
      version, download_url, checksum_sha256: checksum_sha256 || '',
      file_size: Number(file_size) || 0,
      release_note: release_note || '',
      min_version: min_version || '',
      device_types: device_types || ['generic'],
      status
    });
    return { success: true, version, created_at: Date.now() };
  });

  // 删除版本
  fastify.delete('/ota/versions/:version', async (req, reply) => {
    const { deleteAgentVersion } = await import('./db.js');
    deleteAgentVersion(req.params.version);
    return { success: true };
  });

  // 废弃版本
  fastify.patch('/ota/versions/:version/status', async (req, reply) => {
    const { status } = req.body || {};
    const { setAgentVersionStatus } = await import('./db.js');
    setAgentVersionStatus(req.params.version, status);
    return { success: true };
  });

  // ─── 系统状态 ─────────────────────────────────────────

  // Relay 状态
  fastify.get('/relay/status', async (req, reply) => {
    const state = getRelayState();
    const agents = getAllAgents();
    return {
      status: 'healthy',
      version: '2.0.0',
      connections: {
        agents: state.agents_online,
        gui_clients: state.gui_online
      },
      queue: {
        pending_commands: 0
      },
      devices: {
        total: agents.length,
        online: state.agents_online,
        offline: agents.length - state.agents_online
      },
      online_device_ids: state.agent_pool
    };
  });

}
