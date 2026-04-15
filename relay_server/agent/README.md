# nastools ARM Agent

WebSocket 客户端，连接 Relay Server 实现远程管理。

## 版本

**v2.1.0** — 指数退避抖动重连 · 网络预检 · OTA 热升级 · systemd 自启

## 快速开始

```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 一键安装（自动注册）
sudo python3 installer.py \
  --auto \
  --relay-url "ws://120.77.249.3:18888" \
  --device-name "我的NAS" \
  --device-type "jetson" \
  --install-service
```

## 一键安装（已有 agent_key）

```bash
sudo python3 installer.py \
  --relay-url "ws://120.77.249.3:18888" \
  --agent-key "ak_xxxxxxxxxxxx" \
  --device-name "我的NAS" \
  --device-type "jetson" \
  --install-service
```

## 手动启动

```bash
python3 agent.py --config config.yaml

# 查看版本
python3 agent.py --version
# nastools-arm-agent 2.1.0
```

## 配置文件

`config.yaml` — YAML 格式，支持以下节：

```yaml
relay:
  url: "ws://120.77.249.3:18888"
  agent_key: "ak_xxxxxxxxxxxx"

device:
  id: ""                    # 留空自动生成
  name: "我的NAS"
  type: "jetson"            # synology / qnap / jetson / rk3588 / pi5 / sophon / generic
  capabilities: [storage, network, system]

# 重连策略（v7.1 新增）
reconnect:
  base_delay: 1             # 初始延迟（秒）
  max_delay: 60             # 最大延迟（秒）
  jitter: 0.2               # ±20% 随机抖动

# 网络预检（v7.1 新增）
network:
  ping_before_connect: true # 连接前测 socket 可达性
  connect_timeout: 10       # 连接超时（秒）

# OTA 升级（v7.1 新增）
ota:
  enabled: true
  check_interval: 3600      # 检查间隔（秒）
  download_dir: "/tmp/nastool-ota"

diagnose:
  on_start: false
  interval: 3600            # 定期诊断间隔

log:
  level: "INFO"
  file: ""                  # 空则输出到控制台
```

## 功能

| 功能 | 状态 | 说明 |
|------|------|------|
| WebSocket 连接 Relay | ✅ | ws://120.77.249.3:18888 |
| 设备注册与心跳 | ✅ | 30s 间隔 |
| 命令执行与上报 | ✅ | 支持 cwd/env |
| 文件传输 | ✅ | base64 编码 |
| 检测报告上报 | ✅ | JSON 格式 |
| 断线自动重连 | ✅ | 指数退避 + 抖动 |
| 网络预检 | ✅ | 连接前测可达性 |
| OTA 热升级 | ✅ | 检查 → 下载 → 重启 |
| systemd 自启 | ✅ | Watchdog 5min |
| 定期诊断 | ✅ | 后台循环 |

## systemd 服务

```bash
# 查看状态
systemctl status nastool-agent

# 查看实时日志
journalctl -u nastool-agent -f

# 重启
systemctl restart nastool-agent

# 卸载
sudo python3 installer.py --uninstall
```

## OTA 升级流程

```
Agent 启动
  ↓
连接 Relay，发送 ota_check {current_version: "2.0.0"}
  ↓
Relay 返回 ota_version（包含 download_url）
  ↓
有新版本？ → 下载 → SHA256 校验 → systemctl restart
  ↓
Agent 重启后以新版本运行
```

## 与 nastool 集成

```python
# agent.py 中调用诊断模块
from arm_diagnose import run_full_diagnosis

report = run_full_diagnosis()
await agent.send_report(report)
```

## 日志

- **systemd**: `journalctl -u nastool-agent -f`
- **控制台**: 直接运行 `python3 agent.py`
- **文件**: 在 config.yaml 中设置 `log.file`

## Agent CLI 参数

```bash
--config PATH          配置文件路径（默认 config.yaml）
--relay-url URL        覆盖配置文件中的 Relay URL
--agent-key KEY        覆盖配置文件中的 Agent Key
--device-id ID         覆盖设备 ID
--device-name NAME     覆盖设备名称
--run-diagnose         启动时执行一次诊断
--version, -v          输出版本号并退出
```
