// WebSocket 处理器
import { v4 as uuidv4 } from 'uuid';
import {
  upsertAgent, setAgentOffline, getAgentByKey, getAgentKey, getAgent,
  createSession, closeSession, getPendingCommands,
  createCommand, updateCommand, getCommand, saveReport,
  createFile, updateFileStatus, getFile, getAllAgents, getOnlineAgents,
  updateDeployment, getLatestAgentVersion
} from './db.js';

// Agent 连接池: device_id → { socket, session_id, ws_conn_id }
const agentPool = new Map();

// GUI 连接池: gui_session_id → { socket, device_ids: Set }
const guiPool = new Map();

// 文件请求追踪: file_request_id → gui_session_id
export const fileRequestMap = new Map();

// ─── 辅助函数 ───────────────────────────────────────────

export function sendJson(socket, data) {
  if (socket.readyState === 1) { // OPEN
    socket.send(JSON.stringify(data));
  }
}

function parsePayload(data) {
  try {
    return typeof data === 'string' ? JSON.parse(data) : data;
  } catch {
    return null;
  }
}

function now() {
  return Date.now();
}

// ─── Agent WebSocket 处理 ────────────────────────────────

export function handleAgentConnection(ws, req) {
  // 从 URL 解析 agent_key
  const url = new URL(req.url, 'http://localhost');
  const agentKey = url.searchParams.get('key');

  if (!agentKey) {
    ws.close(4001, 'Missing agent_key');
    return;
  }

  // 验证 agent_key (从 agent_keys 表查询)
  const agent = getAgentKey(agentKey);
  if (!agent) {
    ws.close(4002, 'Invalid agent_key');
    return;
  }

  const sessionId = `sess_${uuidv4()}`;
  const deviceId = agent.device_id;
  const connId = `conn_${uuidv4()}`;

  // 记录连接
  ws.deviceId = deviceId;
  ws.sessionId = sessionId;
  ws.connId = connId;

  // 注册 Agent
  upsertAgent({
    device_id: deviceId,
    device_name: agent.device_name,
    device_type: agent.device_type || '',
    version: agent.version || '',
    hostname: agent.hostname || '',
    ip_local: agent.ip_local || '',
    agent_key: agentKey,
    capabilities: agent.capabilities || '[]',
    os_info: agent.os_info || '',
    arch: agent.arch || '',
    python_version: agent.python_version || '',
    registered_at: now()
  });

  // 创建会话
  createSession(sessionId, deviceId, connId);
  agentPool.set(deviceId, { socket: ws, sessionId, connId, lastHeartbeat: now() });

  // 心跳
  ws.isAlive = true;
  ws.on('pong', () => { ws.isAlive = true; });

  // 注册确认
  sendJson(ws, {
    type: 'register_ack',
    id: uuidv4(),
    timestamp: now(),
    payload: {
      session_id: sessionId,
      server_version: '2.0.0',
      config: {
        heartbeat_interval: 30000,
        read_timeout: 90000,
        max_command_timeout: 300000
      }
    }
  });

  // 补发 pending 命令
  const pending = getPendingCommands(deviceId);
  for (const cmd of pending) {
    sendJson(ws, {
      type: 'command',
      id: uuidv4(),
      timestamp: now(),
      source: cmd.gui_session_id || 'relay',
      payload: {
        command_id: cmd.command_id,
        cmd: cmd.cmd,
        timeout_ms: cmd.timeout_ms,
        cwd: cmd.cwd,
        env: JSON.parse(cmd.env || '{}')
      }
    });
    // 标记为 sent
    updateCommand(cmd.command_id, 'sent', '', '', null, null);
  }

  // 广播设备上线给 GUI
  broadcastToGui(deviceId, { type: 'device_online', device_id: deviceId });

  // 消息处理
  ws.on('message', (raw) => {
    const msg = parsePayload(raw);
    if (!msg) return;
    handleAgentMessage(ws, msg);
  });

  ws.on('close', () => {
    setAgentOffline(deviceId);
    closeSession(sessionId);
    agentPool.delete(deviceId);
    broadcastToGui(deviceId, { type: 'device_offline', device_id: deviceId });
  });

  ws.on('error', (err) => {
    console.error(`Agent ${deviceId} error:`, err.message);
  });
}

function handleAgentMessage(ws, msg) {
  const deviceId = ws.deviceId;
  if (!deviceId) return;

  switch (msg.type) {
    case 'heartbeat':
      agentPool.get(deviceId).lastHeartbeat = now();
      break;

    case 'response': {
      // 命令执行结果
      const { command_id, code, stdout, stderr, duration_ms } = msg.payload;
      const status = code === 0 ? 'completed' : 'failed';
      updateCommand(command_id, status, stdout || '', stderr || '', code, duration_ms);

      // 转发给 GUI
      const cmd = getCommand(command_id);
      if (cmd && cmd.gui_session_id) {
        const gui = guiPool.get(cmd.gui_session_id);
        if (gui) {
          sendJson(gui.socket, {
            type: 'response',
            id: msg.id || uuidv4(),
            timestamp: now(),
            source: deviceId,
            payload: {
              command_id,
              status,
              stdout,
              stderr,
              exit_code: code,
              duration_ms
            }
          });
        }
      }
      break;
    }

    case 'report': {
      // 检测报告
      const { report_id, overall_score, categories, items } = msg.payload;
      saveReport(report_id || uuidv4(), deviceId, overall_score, categories, items, now());

      // 广播给所有 GUI
      for (const [guiId, gui] of guiPool) {
        sendJson(gui.socket, {
          type: 'report',
          id: msg.id || uuidv4(),
          timestamp: now(),
          source: deviceId,
          payload: { overall_score, categories, items }
        });
      }
      break;
    }

    case 'log': {
      // 实时日志，转发给所有订阅了该设备的 GUI
      broadcastToGui(deviceId, {
        type: 'log',
        id: msg.id || uuidv4(),
        timestamp: now(),
        source: deviceId,
        payload: msg.payload
      });
      break;
    }

    case 'file_uploaded': {
      // 文件上传完成
      const { file_id, status, checksum_sha256 } = msg.payload;
      updateFileStatus(file_id, status);
      break;
    }

    case 'file_response': {
      // Agent 返回文件内容 → 转发给请求的 GUI
      const { file_request_id } = msg.payload;
      const guiId = fileRequestMap.get(file_request_id);
      if (guiId && guiPool.has(guiId)) {
        sendJson(guiPool.get(guiId).socket, {
          type: 'file_response',
          id: msg.id,
          timestamp: now(),
          source: deviceId,
          payload: msg.payload
        });
      }
      fileRequestMap.delete(file_request_id);
      break;
    }

    case 'deploy_progress': {
      // 部署进度 → 广播给 GUI
      const { deployment_id, step, progress, message } = msg.payload;
      // 查找该部署对应的 GUI
      broadcastToGui(deviceId, {
        type: 'deploy_progress',
        id: msg.id,
        timestamp: now(),
        source: deviceId,
        payload: { deployment_id, step, progress, message }
      });
      break;
    }

    case 'deploy_result': {
      // 部署结果 → 转发给 GUI
      const { deployment_id, success, version, message: resultMsg, duration_ms } = msg.payload;
      broadcastToGui(deviceId, {
        type: 'deploy_result',
        id: msg.id,
        timestamp: now(),
        source: deviceId,
        payload: { deployment_id, success, version, message: resultMsg, duration_ms }
      });
      // 更新部署状态
      updateDeployment(deployment_id, success ? 'completed' : 'failed', []);
      break;
    }

    case 'error': {
      // 错误上报
      console.error(`Agent ${deviceId} error:`, msg.payload);
      broadcastToGui(deviceId, {
        type: 'agent_error',
        source: deviceId,
        payload: msg.payload
      });
      break;
    }

    // ─── OTA 升级消息 ─────────────────────────────────
    case 'ota_check': {
      // Agent 询问最新版本 → 查询 db 返回 ota_version
      const { current_version } = msg.payload || {};
      const agentInfo = getAgent(deviceId);
      const deviceType = agentInfo?.device_type || 'generic';
      const latest = getLatestAgentVersion(current_version || '0', deviceType);
      sendJson(ws, {
        type: 'ota_version',
        id: uuidv4(),
        timestamp: now(),
        source: 'relay',
        payload: latest || {
          version: current_version || '0',
          download_url: '',
          checksum_sha256: '',
          file_size: 0,
          release_note: '已是最新版本',
          status: 'up_to_date'
        }
      });
      break;
    }

    case 'ota_progress': {
      // Agent 下载进度 → 广播给 GUI
      const { version, progress, speed, eta } = msg.payload || {};
      broadcastToGui(deviceId, {
        type: 'ota_progress',
        id: msg.id,
        timestamp: now(),
        source: deviceId,
        payload: { version, progress, speed, eta }
      });
      break;
    }

    case 'ota_result': {
      // Agent 升级结果
      const { success, version, message } = msg.payload || {};
      console.log(`[OTA] Agent ${deviceId} 升级结果: success=${success}, version=${version}`);
      broadcastToGui(deviceId, {
        type: 'ota_result',
        id: msg.id,
        timestamp: now(),
        source: deviceId,
        payload: { success, version, message }
      });
      break;
    }
  }
}

// ─── GUI WebSocket 处理 ─────────────────────────────────

export function handleGuiConnection(ws, req, jwtPayload) {
  const guiSessionId = `gui_${uuidv4()}`;
  ws.guiSessionId = guiSessionId;
  ws.devices = new Set();

  guiPool.set(guiSessionId, { socket: ws, devices: ws.devices });

  // 连接确认
  sendJson(ws, {
    type: 'connected',
    id: uuidv4(),
    timestamp: now(),
    payload: {
      gui_session_id: guiSessionId,
      server_version: '2.0.0',
      online_devices: getOnlineAgents().map(a => a.device_id)
    }
  });

  ws.on('message', (raw) => {
    const msg = parsePayload(raw);
    if (!msg) return;
    handleGuiMessage(ws, msg);
  });

  ws.on('close', () => {
    guiPool.delete(guiSessionId);
  });

  ws.on('error', (err) => {
    console.error(`GUI ${guiSessionId} error:`, err.message);
  });
}

function handleGuiMessage(ws, msg) {
  const guiSessionId = ws.guiSessionId;

  switch (msg.type) {
    case 'heartbeat':
      sendJson(ws, { type: 'heartbeat_ack', timestamp: now() });
      break;

    case 'subscribe': {
      // 订阅设备更新
      const { device_id } = msg.payload;
      ws.devices.add(device_id);
      break;
    }

    case 'unsubscribe': {
      const { device_id } = msg.payload;
      ws.devices.delete(device_id);
      break;
    }

    case 'command': {
      // 下发命令到 Agent
      const { target, payload } = msg;
      const agent = agentPool.get(target);

      if (!agent) {
        // Agent 不在线，存入队列
        createCommand(
          payload.command_id, target, guiSessionId,
          payload.cmd, payload.timeout_ms || 30000,
          payload.cwd || '', payload.env || {}
        );
        sendJson(ws, {
          type: 'command_queued',
          id: msg.id,
          timestamp: now(),
          payload: {
            command_id: payload.command_id,
            device_id: target,
            status: 'queued'
          }
        });
      } else {
        // Agent 在线，立即转发
        createCommand(
          payload.command_id, target, guiSessionId,
          payload.cmd, payload.timeout_ms || 30000,
          payload.cwd || '', payload.env || {}
        );
        updateCommand(payload.command_id, 'sent', '', '', null, null);
        sendJson(agent.socket, {
          type: 'command',
          id: msg.id,
          timestamp: now(),
          source: guiSessionId,
          payload
        });
        sendJson(ws, {
          type: 'command_sent',
          id: msg.id,
          timestamp: now(),
          payload: {
            command_id: payload.command_id,
            device_id: target,
            status: 'sent'
          }
        });
      }
      break;
    }

    case 'file': {
      // 文件传输：转发给 Agent
      const { target, payload } = msg;
      const agent = agentPool.get(target);

      if (!agent) {
        sendJson(ws, {
          type: 'error',
          id: msg.id,
          timestamp: now(),
          payload: { code: 'DEVICE_OFFLINE', message: '设备不在线' }
        });
        return;
      }

      createFile(
        payload.file_id, target, payload.name,
        payload.size, payload.path, payload.mode || '0644', payload.checksum_sha256 || ''
      );

      sendJson(agent.socket, {
        type: 'file',
        id: msg.id,
        timestamp: now(),
        source: guiSessionId,
        payload
      });

      sendJson(ws, {
        type: 'file_sent',
        id: msg.id,
        timestamp: now(),
        payload: { file_id: payload.file_id, status: 'transferred' }
      });
      break;
    }

    case 'file_request': {
      // GUI 请求 Agent 下载文件
      const { target, payload } = msg;
      const agent = agentPool.get(target);

      if (!agent) {
        sendJson(ws, {
          type: 'error',
          id: msg.id,
          timestamp: now(),
          payload: { code: 'DEVICE_OFFLINE', message: '设备不在线' }
        });
        return;
      }

      // 追踪请求方 GUI
      fileRequestMap.set(payload.file_request_id, guiSessionId);

      sendJson(agent.socket, {
        type: 'file_request',
        id: msg.id,
        timestamp: now(),
        source: guiSessionId,
        payload
      });
      break;
    }

    case 'deploy': {
      // 下发部署指令
      const { target, payload } = msg;
      const agent = agentPool.get(target);

      if (!agent) {
        sendJson(ws, {
          type: 'error',
          id: msg.id,
          timestamp: now(),
          payload: { code: 'DEVICE_OFFLINE', message: '设备不在线' }
        });
        return;
      }

      sendJson(agent.socket, {
        type: 'deploy',
        id: msg.id,
        timestamp: now(),
        source: guiSessionId,
        payload
      });
      break;
    }

    case 'disconnect_device': {
      const { target } = msg;
      const agent = agentPool.get(target);
      if (agent) {
        sendJson(agent.socket, {
          type: 'disconnect',
          id: msg.id,
          timestamp: now(),
          payload: { reason: msg.payload?.reason || 'user_requested' }
        });
      }
      break;
    }
  }
}

// ─── 广播辅助 ────────────────────────────────────────────

function broadcastToGui(targetDeviceId, message) {
  for (const [guiId, gui] of guiPool) {
    if (gui.devices.has(targetDeviceId)) {
      sendJson(gui.socket, message);
    }
  }
}

// ─── 心跳检测 ───────────────────────────────────────────

export function startHeartbeat(pino) {
  const interval = setInterval(() => {
    for (const [deviceId, agent] of agentPool) {
      if (!agent.socket.isAlive) {
        agent.socket.terminate();
        setAgentOffline(deviceId);
        closeSession(agent.sessionId);
        agentPool.delete(deviceId);
        broadcastToGui(deviceId, { type: 'device_offline', device_id: deviceId });
        pino.warn({ deviceId }, 'Agent heartbeat timeout, disconnected');
        continue;
      }
      agent.socket.isAlive = false;
      agent.socket.ping();
    }
  }, 30000);

  return () => clearInterval(interval);
}

// ─── 状态查询（供 REST API 使用）────────────────────────

export function getRelayState() {
  return {
    agents_online: agentPool.size,
    gui_online: guiPool.size,
    agent_pool: [...agentPool.keys()],
  };
}

export function isAgentOnline(deviceId) {
  return agentPool.has(deviceId);
}

export function getAgentSocket(deviceId) {
  return agentPool.get(deviceId);
}
