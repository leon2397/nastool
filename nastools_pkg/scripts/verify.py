# -*- coding: utf-8 -*-
"""
scripts/verify.py — 部署后验证逻辑

功能：
1. 检查 systemd 服务状态
2. 检查进程是否运行
3. 检查端口是否监听
4. 检查 API 健康端点
5. 返回验证结果摘要
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re


# ══════════════════════════════════════════════════════════════════
# 常量
# ══════════════════════════════════════════════════════════════════

SERVICE_NAME = "ai-nas-arm"
DEFAULT_PORT = 9999
HEALTH_ENDPOINT = "/health"
VERIFY_TIMEOUT = 10  # 秒


# ══════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════


@dataclass
class VerifyResult:
    """单项验证结果"""

    name: str  # 验证项名称
    passed: bool  # 是否通过
    message: str  # 结果消息
    details: str = ""  # 详细信息


@dataclass
class VerifySummary:
    """验证结果摘要"""

    all_passed: bool
    results: List[VerifyResult]
    service_status: str  # active/inactive/failed/unknown
    port: int
    health_response: str  # 健康检查响应

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)


# ══════════════════════════════════════════════════════════════════
# 验证脚本生成器
# ══════════════════════════════════════════════════════════════════


def get_verify_script(port: int = DEFAULT_PORT) -> str:
    """
    生成验证脚本（在 ARM 设备上执行）

    返回 JSON 格式的验证结果
    """
    return f'''#!/bin/bash
# 部署后验证脚本
# 输出 JSON 格式结果

SERVICE="{SERVICE_NAME}"
PORT={port}

# 结果收集
declare -a RESULTS=()

# 辅助函数：添加结果
add_result() {{
    local name="$1"
    local passed="$2"
    local msg="$3"
    local details="$4"
    RESULTS+=("{{\\"name\\":\\"$name\\",\\"passed\\":$passed,\\"message\\":\\"$msg\\",\\"details\\":\\"$details\\"}}")
}}

# 1. 检查 systemd 服务状态
SERVICE_STATUS=$(systemctl is-active $SERVICE 2>/dev/null || echo "unknown")
case $SERVICE_STATUS in
    active)
        add_result "systemd服务" true "服务运行中" "systemctl is-active: active"
        ;;
    inactive)
        add_result "systemd服务" false "服务未运行" "systemctl is-active: inactive"
        ;;
    failed)
        add_result "systemd服务" false "服务启动失败" "systemctl is-active: failed"
        ;;
    *)
        add_result "systemd服务" false "服务未注册或未知状态" "systemctl is-active: $SERVICE_STATUS"
        ;;
esac

# 2. 检查进程
PROCESS_COUNT=$(pgrep -f "arm_server.py" 2>/dev/null | wc -l)
if [ "$PROCESS_COUNT" -gt 0 ]; then
    PID=$(pgrep -f "arm_server.py" | head -1)
    add_result "进程检查" true "进程运行中" "PID: $PID"
else
    add_result "进程检查" false "未找到进程" "pgrep arm_server.py: 无结果"
fi

# 3. 检查端口
PORT_CHECK=$(ss -tlnp 2>/dev/null | grep ":$PORT " || netstat -tlnp 2>/dev/null | grep ":$PORT ")
if [ -n "$PORT_CHECK" ]; then
    LISTEN_PROC=$(echo "$PORT_CHECK" | grep -oP 'pid=\\K[0-9]+' || echo "unknown")
    add_result "端口监听" true "端口 $PORT 正在监听" "监听进程 PID: $LISTEN_PROC"
else
    add_result "端口监听" false "端口 $PORT 未监听" "ss/netstat 无结果"
fi

# 4. 检查 API 健康端点
HEALTH_RESP=$(curl -s --connect-timeout 5 --max-time 10 "http://localhost:$PORT/health" 2>/dev/null)
CURL_EXIT=$?
if [ $CURL_EXIT -eq 0 ] && [ -n "$HEALTH_RESP" ]; then
    # 尝试解析 JSON
    if echo "$HEALTH_RESP" | grep -q '"status"'; then
        STATUS=$(echo "$HEALTH_RESP" | grep -oP '"status"\\s*:\\s*"\\K[^"]+' || echo "unknown")
        add_result "API健康检查" true "API 响应正常" "status: $STATUS"
    else
        add_result "API健康检查" true "API 有响应（非JSON）" "响应: ${{HEALTH_RESP:0:50}}"
    fi
else
    case $CURL_EXIT in
        7)  add_result "API健康检查" false "无法连接" "curl exit 7: Connection refused" ;;
        28) add_result "API健康检查" false "连接超时" "curl exit 28: Timeout" ;;
        *)  add_result "API健康检查" false "请求失败" "curl exit: $CURL_EXIT" ;;
    esac
fi

# 输出 JSON 结果
echo "{{"
echo "  \\"service_status\\": \\"$SERVICE_STATUS\\","
echo "  \\"port\\": $PORT,"
echo "  \\"results\\": ["
for i in "${{!RESULTS[@]}}"; do
    if [ $i -lt $((${{#RESULTS[@]}} - 1)) ]; then
        echo "    ${{RESULTS[$i]}},"
    else
        echo "    ${{RESULTS[$i]}}"
    fi
done
echo "  ]"
echo "}}"
'''


def get_quick_verify_script(port: int = DEFAULT_PORT) -> str:
    """
    快速验证脚本（仅检查关键项）
    用于部署后立即验证
    """
    return f'''#!/bin/bash
# 快速验证（部署后立即检查）
SERVICE="{SERVICE_NAME}"
PORT={port}

# 等待服务启动
sleep 2

# 检查服务状态
if systemctl is-active --quiet $SERVICE 2>/dev/null; then
    echo "SERVICE:ACTIVE"
else
    echo "SERVICE:INACTIVE"
    exit 1
fi

# 检查端口
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
    echo "PORT:LISTENING"
else
    echo "PORT:NOT_LISTEN"
    exit 1
fi

# 检查健康端点
HEALTH=$(curl -s --connect-timeout 5 --max-time 10 "http://localhost:$PORT/health" 2>/dev/null)
if [ -n "$HEALTH" ]; then
    echo "HEALTH:OK"
    echo "$HEALTH"
else
    echo "HEALTH:FAILED"
    exit 1
fi
'''


# ══════════════════════════════════════════════════════════════════
# 结果解析
# ══════════════════════════════════════════════════════════════════


def parse_verify_output(output: str, port: int = DEFAULT_PORT) -> VerifySummary:
    """
    解析验证脚本输出

    Args:
        output: 脚本执行的 stdout
        port: 期望的端口

    Returns:
        VerifySummary 对象
    """
    import json

    results = []
    service_status = "unknown"
    health_response = ""

    try:
        # 尝试解析 JSON
        data = json.loads(output)

        service_status = data.get("service_status", "unknown")

        for r in data.get("results", []):
            results.append(
                VerifyResult(
                    name=r.get("name", "?"),
                    passed=r.get("passed", False),
                    message=r.get("message", ""),
                    details=r.get("details", ""),
                )
            )

    except json.JSONDecodeError:
        # 降级：解析快速验证格式
        for line in output.strip().split("\n"):
            line = line.strip()
            if line.startswith("SERVICE:"):
                val = line.split(":")[1]
                results.append(
                    VerifyResult(
                        name="systemd服务",
                        passed=val == "ACTIVE",
                        message="服务运行中" if val == "ACTIVE" else "服务未运行",
                    )
                )
                service_status = val.lower()
            elif line.startswith("PORT:"):
                val = line.split(":")[1]
                results.append(
                    VerifyResult(
                        name="端口监听",
                        passed=val == "LISTENING",
                        message=f"端口 {port} 正在监听"
                        if val == "LISTENING"
                        else f"端口 {port} 未监听",
                    )
                )
            elif line.startswith("HEALTH:"):
                val = line.split(":")[1]
                results.append(
                    VerifyResult(
                        name="API健康检查",
                        passed=val == "OK",
                        message="API 响应正常" if val == "OK" else "API 无响应",
                    )
                )
            elif line.startswith("{"):
                # 可能是健康检查的 JSON 响应
                health_response = line

    # 确保至少有结果
    if not results:
        results.append(
            VerifyResult(
                name="验证脚本",
                passed=False,
                message="无法解析验证结果",
                details=output[:200],
            )
        )

    return VerifySummary(
        all_passed=all(r.passed for r in results),
        results=results,
        service_status=service_status,
        port=port,
        health_response=health_response,
    )


def parse_quick_verify_output(output: str) -> Tuple[bool, str]:
    """
    解析快速验证输出

    Returns:
        (是否全部通过, 状态描述)
    """
    lines = output.strip().split("\n")

    service_ok = False
    port_ok = False
    health_ok = False

    for line in lines:
        if line.startswith("SERVICE:ACTIVE"):
            service_ok = True
        elif line.startswith("PORT:LISTENING"):
            port_ok = True
        elif line.startswith("HEALTH:OK"):
            health_ok = True

    all_ok = service_ok and port_ok and health_ok

    if all_ok:
        msg = "验证通过：服务运行、端口监听、API 正常"
    else:
        parts = []
        if not service_ok:
            parts.append("服务未运行")
        if not port_ok:
            parts.append("端口未监听")
        if not health_ok:
            parts.append("API 无响应")
        msg = "验证失败：" + "、".join(parts)

    return all_ok, msg


# ══════════════════════════════════════════════════════════════════
# 诊断脚本
# ══════════════════════════════════════════════════════════════════


def get_diagnose_script(port: int = DEFAULT_PORT) -> str:
    """
    生成诊断脚本（验证失败时收集详细信息）
    """
    return f'''#!/bin/bash
# 验证失败诊断脚本

SERVICE="{SERVICE_NAME}"
PORT={port}

echo "=== 服务状态 ==="
systemctl status $SERVICE 2>/dev/null || echo "服务未注册"

echo ""
echo "=== 服务日志（最近 20 行）==="
journalctl -u $SERVICE -n 20 --no-pager 2>/dev/null || echo "无日志"

echo ""
echo "=== 进程检查 ==="
ps aux | grep -E "(arm_server|python.*$PORT)" | grep -v grep || echo "未找到相关进程"

echo ""
echo "=== 端口检查 ==="
ss -tlnp | grep -E "(:$PORT|State)" || echo "端口 $PORT 未监听"

echo ""
echo "=== 防火墙检查 ==="
if command -v ufw &>/dev/null; then
    ufw status | grep -E "($PORT|Status)" || echo "ufw 未配置"
elif command -v firewall-cmd &>/dev/null; then
    firewall-cmd --list-ports 2>/dev/null || echo "firewalld 未配置"
else
    echo "未检测到防火墙"
fi

echo ""
echo "=== 网络连接测试 ==="
curl -v --connect-timeout 5 "http://localhost:$PORT/health" 2>&1 | head -20

echo ""
echo "=== 配置文件检查 ==="
if [ -f /opt/ai-nas/config.yaml ]; then
    echo "config.yaml 存在"
    head -20 /opt/ai-nas/config.yaml
else
    echo "config.yaml 不存在"
fi

if [ -f /opt/ai-nas/ai-nas-arm.env ]; then
    echo "ai-nas-arm.env 内容:"
    cat /opt/ai-nas/ai-nas-arm.env
else
    echo "ai-nas-arm.env 不存在"
fi
'''
