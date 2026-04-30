# nastool-agent

后台代理服务模块，提供设备监控和管理功能。

## 功能

- 设备状态监控
- 自动诊断
- 远程管理
- 实时通知
- 任务调度

## 目录结构

- `nastool_agent/`
  - `__main__.py` - 主入口
  - `agent.py` - 代理核心
  - `server.py` - WebSocket服务器
  - `scheduler.py` - 任务调度器
  - `notifier.py` - 通知模块

## 安装

```bash
pip install -e .
```

## 依赖

- `websockets` - WebSocket服务器
- `psutil` - 系统信息采集
- `pyyaml` - 配置文件解析

## 使用示例

### 启动代理服务

```bash
# 基本启动
python -m nastool_agent

# 指定端口和密钥
python -m nastool_agent --port 8000 --agent-key your_secure_key

# 后台运行
nohup python -m nastool_agent > agent.log 2>&1 &
```

### 配置文件

创建 `agent_config.yaml`：

```yaml
# 代理配置
agent:
  port: 8000
  host: 0.0.0.0
  agent_key: your_secure_key
  debug: false

# 监控配置
monitoring:
  enabled: true
  interval: 60  # 秒
  checks:
    - system
    - storage
    - network

# 通知配置
notifications:
  enabled: true
  channels:
    - type: email
      config:
        smtp_server: smtp.example.com
        smtp_port: 587
        username: user@example.com
        password: password
        recipients:
          - admin@example.com

# 任务配置
tasks:
  - name: daily_diagnosis
    schedule: "0 0 * * *"  # 每天凌晨执行
    command: diagnose
  - name: weekly_cleanup
    schedule: "0 0 * * 0"  # 每周日执行
    command: cleanup
```

### 客户端连接

```python
import websocket
import json

# 连接到代理
ws = websocket.create_connection(
    "ws://localhost:8000",
    header={"Agent-Key": "your_secure_key"}
)

# 发送诊断命令
ws.send(json.dumps({
    "command": "diagnose",
    "params": {
        "categories": ["system", "storage"]
    }
}))

# 接收响应
response = ws.recv()
result = json.loads(response)
print("诊断结果:", result)

# 关闭连接
ws.close()
```

## API 接口

### WebSocket API

- **diagnose** - 执行诊断
  - 参数: `categories` - 检查类别列表
  - 返回: 诊断结果

- **status** - 获取设备状态
  - 返回: 设备状态信息

- **execute** - 执行命令
  - 参数: `command` - 命令字符串
  - 返回: 命令执行结果

- **config** - 获取/设置配置
  - 参数: `action` - get/set, `key` - 配置键, `value` - 配置值
  - 返回: 配置信息

- **tasks** - 管理任务
  - 参数: `action` - list/add/remove, `task` - 任务信息
  - 返回: 任务状态

### HTTP API

- `GET /api/health` - 健康检查
- `GET /api/status` - 设备状态
- `POST /api/diagnose` - 执行诊断
- `POST /api/execute` - 执行命令
- `GET /api/config` - 获取配置
- `PUT /api/config` - 更新配置

## 安全配置

### 推荐安全设置

1. **使用安全密钥**：设置强密码作为 agent_key
2. **限制访问**：在防火墙中限制访问端口
3. **使用HTTPS**：配置TLS/SSL
4. **定期更新**：及时更新代理软件
5. **权限控制**：以非root用户运行

### 安全注意事项

- 不要在生产环境中使用默认密钥
- 不要将密钥硬编码在代码中
- 定期更换密钥
- 监控异常访问

## 任务调度

### 内置任务

- `daily_diagnosis` - 每日诊断
- `weekly_cleanup` - 每周清理
- `monthly_report` - 月度报告

### 自定义任务

```yaml
tasks:
  - name: custom_task
    schedule: "*/30 * * * *"  # 每30分钟执行
    command: "echo 'Hello from agent'"
  - name: backup
    schedule: "0 2 * * *"  # 每天凌晨2点执行
    command: "rsync -av /data /backup"
```

## 监控功能

### 监控项目

- CPU使用率
- 内存使用
- 磁盘空间
- 网络流量
- 系统负载
- 进程状态

### 告警规则

```yaml
monitoring:
  alerts:
    - metric: cpu_usage
      threshold: 90
      operator: gt
      message: CPU使用率超过90%
    - metric: disk_usage
      threshold: 80
      operator: gt
      message: 磁盘使用率超过80%
```

## 性能优化

- **资源监控**：合理设置监控间隔
- **任务调度**：避免任务集中执行
- **内存管理**：定期清理内存
- **网络优化**：使用心跳机制减少网络流量

## 故障排除

### 常见问题

1. **连接失败**：检查网络连接和防火墙设置
2. **认证失败**：检查agent_key是否正确
3. **性能问题**：调整监控间隔和任务调度
4. **内存泄漏**：检查是否有内存泄漏问题

### 日志查看

```bash
# 查看代理日志
tail -f agent.log

# 查看系统日志
journalctl -u nastool-agent
```

## 部署方式

### 系统服务

创建系统服务文件 `/etc/systemd/system/nastool-agent.service`：

```ini
[Unit]
Description=NASTool Agent
After=network.target

[Service]
Type=simple
User=nobody
WorkingDirectory=/path/to/nastool-agent
ExecStart=/usr/bin/python -m nastool_agent
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
systemctl enable nastool-agent

# 启动服务
systemctl start nastool-agent

# 查看状态
systemctl status nastool-agent
```

## 许可证

MIT