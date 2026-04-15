#!/usr/bin/env python3
"""
nastools ARM Agent 安装脚本 v2.1
一键安装并配置 Agent，支持 systemd 自启 + OTA 升级

用法:
  # 自动注册（推荐）
  sudo python3 installer.py --auto \
    --relay-url "ws://120.77.249.3:18888" \
    --device-name "我的NAS" \
    --device-type "jetson"

  # 已有 agent_key
  sudo python3 installer.py \
    --relay-url "ws://120.77.249.3:18888" \
    --agent-key "ak_xxxxxxxxxxxx" \
    --device-name "我的NAS" \
    --device-type "jetson"

  # 安装 systemd 自启
  sudo python3 installer.py --install-service ...
"""

import os
import platform
import subprocess
import sys
import shutil
from pathlib import Path


def run(cmd, check=False):
    return subprocess.run(cmd, shell=True, check=check)


def is_root():
    return os.geteuid() == 0 if hasattr(os, "geteuid") else False


def install_dependencies():
    """安装 Python 依赖"""
    print("📦 安装依赖...")
    for dep in ["websockets>=12.0", "pyyaml>=6.0"]:
        r = run(f'{sys.executable} -m pip install {dep}')
        tag = "✅" if r.returncode == 0 else "⚠️ "
        print(f"   {tag} {dep}")


def create_config(relay_url, agent_key, device_name, device_type):
    """创建 config.yaml（含 v7.1 OTA + 重连 + 网络预检配置）"""
    import uuid
    cfg_path = Path(__file__).parent / "config.yaml"
    device_id = f"{platform.node()}-{uuid.uuid4().hex[:8]}"
    
    # 优先用 AgentConfig（需要 yaml）
    try:
        from config import AgentConfig
        cfg = AgentConfig()
        cfg.relay_url = relay_url
        cfg.agent_key = agent_key
        cfg.device_name = device_name
        cfg.device_type = device_type
        cfg.device_id = device_id
        cfg.capabilities = ["storage", "network", "system"]
        cfg.save(str(cfg_path))
        print(f"✅ 配置已保存: {cfg_path}")
        return
    except ImportError:
        pass
    
    # Fallback: 纯文本 YAML
    yaml_text = f'''# nastools ARM Agent v2.1 — {device_name}
relay:
  url: "{relay_url}"
  agent_key: "{agent_key}"

device:
  id: "{device_id}"
  name: "{device_name}"
  type: "{device_type}"
  capabilities:
    - storage
    - network
    - system

timing:
  heartbeat_interval: 30000
  read_timeout: 90000

reconnect:
  base_delay: 1
  max_delay: 60
  jitter: 0.2

network:
  ping_before_connect: true
  connect_timeout: 10

ota:
  enabled: true
  check_interval: 3600
  download_dir: "/tmp/nastool-ota"

diagnose:
  on_start: false
  interval: 3600

log:
  level: "INFO"
'''
    cfg_path.write_text(yaml_text, encoding="utf-8")
    print(f"✅ 配置已保存: {cfg_path}")


def create_systemd_service(service_name="nastool-agent"):
    """生成 systemd Unit 文件内容（不写入系统，需要 root 权限）"""
    if platform.system() != "Linux":
        return None
    agent_dir = Path(__file__).parent.resolve()
    return f'''[Unit]
Description=nastools ARM Agent v2.1
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={agent_dir}
ExecStart={sys.executable} {agent_dir}/agent.py --config {agent_dir}/config.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=nastool-agent
Environment="OTA_DIR=/tmp/nastool-ota"
WatchdogSec=300

[Install]
WantedBy=multi-user.target
'''


def install_service(service_name="nastool-agent"):
    """安装 systemd 服务（需要 root）"""
    if platform.system() != "Linux":
        print("⏭️  systemd 仅支持 Linux"); return False
    if not is_root():
        print("⚠️  需要 root: sudo python3 installer.py --install-service"); return False
    
    unit = create_systemd_service(service_name)
    if not unit:
        return False
    
    path = Path(f"/etc/systemd/system/{service_name}.service")
    try:
        path.write_text(unit, encoding="utf-8")
        run("systemctl daemon-reload")
        run(f"systemctl enable {service_name}")
        print(f"✅ 服务已创建并启用: /etc/systemd/system/{service_name}.service")
        return True
    except Exception as e:
        print(f"❌ systemd 安装失败: {e}"); return False


def uninstall_service(service_name="nastool-agent"):
    """卸载 systemd 服务"""
    if platform.system() != "Linux" or not is_root():
        return
    run(f"systemctl stop {service_name}", check=False)
    run(f"systemctl disable {service_name}", check=False)
    Path(f"/etc/systemd/system/{service_name}.service").unlink(missing_ok=True)
    run("systemctl daemon-reload")
    print(f"✅ {service_name} 已卸载（配置保留）")


def pre_register(relay_url, device_name, device_type):
    """调用 Relay /keys/generate API 预注册设备"""
    try:
        import urllib.request, json
        base = relay_url.replace("ws://", "http://").replace("wss://", "https://").rstrip("/")
        req = urllib.request.Request(
            f"{base}/keys/generate",
            data=json.dumps({"label": f"{device_name} ({platform.node()})"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        key = result.get("agent_key")
        if key:
            print(f"✅ 已预注册，agent_key: {key[:18]}...")
            return key
    except Exception as e:
        print(f"⚠️  预注册失败: {e}，请手动申请 agent_key")
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)
    g = parser.add_argument_group("必填参数")
    g.add_argument("--relay-url", help="Relay Server URL (ws://... 或 http://...)")
    g.add_argument("--agent-key", help="Agent Key（已有 key 时填此参数）")
    g.add_argument("--device-name", default="My NAS", help="设备名称")
    g.add_argument("--device-type", default="generic",
        help="类型: synology, qnap, jetson, rk3588, pi5, sophon, generic")
    g = parser.add_argument_group("可选参数")
    g.add_argument("--auto", action="store_true", help="自动注册（无需 agent-key）")
    g.add_argument("--install-service", action="store_true", help="安装 systemd 自启")
    g.add_argument("--uninstall", action="store_true", help="卸载 Agent")
    g.add_argument("--start", action="store_true", help="安装后立即启动")
    args = parser.parse_args()
    
    if args.uninstall:
        uninstall_service(); return
    
    if not args.relay_url:
        print("❌ 缺少 --relay-url"); sys.exit(1)
    if not args.agent_key and not args.auto:
        print("❌ 缺少 --agent-key（可改用 --auto）"); sys.exit(1)
    
    print("=" * 55)
    print("  nastools ARM Agent v2.1 安装")
    print("=" * 55)
    
    install_dependencies()
    
    key = args.agent_key
    if args.auto and not key:
        key = pre_register(args.relay_url, args.device_name, args.device_type)
        if not key:
            print("❌ 自动注册失败，请检查 Relay 在线状态")
            sys.exit(1)
    
    create_config(args.relay_url, key, args.device_name, args.device_type)
    
    if args.install_service:
        ok = install_service()
        if ok and args.start:
            run("systemctl start nastool-agent")
            print("✅ 服务已启动: systemctl status nastool-agent")
    
    print()
    print("=" * 55)
    print("  ✅ 安装完成！")
    print("=" * 55)
    print("  启动: python3 agent.py --config config.yaml")
    print("  服务: systemctl start nastool-agent")


if __name__ == "__main__":
    main()
