# -*- coding: utf-8 -*-
"""
scripts/uninstall.py — 完善的卸载逻辑

功能：
1. 安全卸载（保留数据和配置）
2. 完全卸载（删除所有内容）
3. 卸载前确认清单
4. 卸载后验证
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


# ══════════════════════════════════════════════════════════════════
# 常量
# ══════════════════════════════════════════════════════════════════

SERVICE_NAME = "ai-nas-arm"
INSTALL_DIR = "/opt/ai-nas"
BACKUP_DIR = "/opt/ai-nas/backups"
DATA_DIRS = ["/nas", "/opt/ai-nas/data"]


# ══════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════


@dataclass
class UninstallPreview:
    """卸载预览信息"""

    service_installed: bool
    service_active: bool
    install_dir_exists: bool
    backup_count: int
    data_dir_exists: bool
    data_size: str
    config_exists: bool

    # 文件清单
    files_to_remove: List[str]
    dirs_to_remove: List[str]

    @property
    def has_content(self) -> bool:
        """是否有内容需要卸载"""
        return (
            self.service_installed or self.install_dir_exists or self.backup_count > 0
        )


# ══════════════════════════════════════════════════════════════════
# 预览脚本
# ══════════════════════════════════════════════════════════════════


def get_preview_script() -> str:
    """
    生成预览脚本（收集卸载前信息）

    Returns:
        在 ARM 设备上执行的脚本
    """
    return f'''#!/bin/bash
# 卸载预览脚本

SERVICE="{SERVICE_NAME}"
INSTALL_DIR="{INSTALL_DIR}"
BACKUP_DIR="{BACKUP_DIR}"

echo "=== 服务状态 ==="
if systemctl is-active --quiet $SERVICE 2>/dev/null; then
    echo "SERVICE_ACTIVE:yes"
else
    echo "SERVICE_ACTIVE:no"
fi

if [ -f /etc/systemd/system/$SERVICE.service ]; then
    echo "SERVICE_INSTALLED:yes"
else
    echo "SERVICE_INSTALLED:no"
fi

echo ""
echo "=== 安装目录 ==="
if [ -d "$INSTALL_DIR" ]; then
    echo "INSTALL_DIR_EXISTS:yes"
    echo "INSTALL_SIZE:$(du -sh $INSTALL_DIR 2>/dev/null | cut -f1)"
    
    # 列出主要文件
    echo "FILES:"
    find "$INSTALL_DIR" -maxdepth 1 -type f -name "*.py" 2>/dev/null | while read f; do
        echo "  $(basename $f): $(stat -c%s $f 2>/dev/null || stat -f%z $f) bytes"
    done
else
    echo "INSTALL_DIR_EXISTS:no"
fi

echo ""
echo "=== 备份目录 ==="
if [ -d "$BACKUP_DIR" ]; then
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.bak.* 2>/dev/null | wc -l)
    echo "BACKUP_COUNT:$BACKUP_COUNT"
    if [ $BACKUP_COUNT -gt 0 ]; then
        echo "BACKUP_SIZE:$(du -sh $BACKUP_DIR 2>/dev/null | cut -f1)"
    fi
else
    echo "BACKUP_COUNT:0"
fi

echo ""
echo "=== 数据目录 ==="
DATA_EXISTS=no
DATA_SIZE="0"
for d in {" ".join(DATA_DIRS)}; do
    if [ -d "$d" ]; then
        DATA_EXISTS=yes
        SIZE=$(du -sh "$d" 2>/dev/null | cut -f1)
        echo "DATA_DIR:$d:$SIZE"
    fi
done
echo "DATA_EXISTS:$DATA_EXISTS"

echo ""
echo "=== 配置文件 ==="
if [ -f "$INSTALL_DIR/config.yaml" ]; then
    echo "CONFIG_EXISTS:yes"
else
    echo "CONFIG_EXISTS:no"
fi
'''


def parse_preview_output(output: str) -> UninstallPreview:
    """解析预览脚本输出"""
    lines = output.strip().split("\n")

    service_installed = False
    service_active = False
    install_dir_exists = False
    backup_count = 0
    data_dir_exists = False
    data_size = "0"
    config_exists = False
    files_to_remove = []
    dirs_to_remove = []

    for line in lines:
        line = line.strip()

        if line.startswith("SERVICE_INSTALLED:"):
            service_installed = line.split(":")[1] == "yes"
        elif line.startswith("SERVICE_ACTIVE:"):
            service_active = line.split(":")[1] == "yes"
        elif line.startswith("INSTALL_DIR_EXISTS:"):
            install_dir_exists = line.split(":")[1] == "yes"
        elif line.startswith("BACKUP_COUNT:"):
            backup_count = int(line.split(":")[1])
        elif line.startswith("DATA_EXISTS:"):
            data_dir_exists = line.split(":")[1] == "yes"
        elif line.startswith("DATA_DIR:"):
            parts = line.split(":")
            if len(parts) >= 3:
                dirs_to_remove.append(parts[1])
                data_size = parts[2]
        elif line.startswith("CONFIG_EXISTS:"):
            config_exists = line.split(":")[1] == "yes"
        elif line.startswith("  "):
            # 文件列表
            parts = line.split(":")
            if len(parts) >= 1:
                files_to_remove.append(parts[0].strip())

    return UninstallPreview(
        service_installed=service_installed,
        service_active=service_active,
        install_dir_exists=install_dir_exists,
        backup_count=backup_count,
        data_dir_exists=data_dir_exists,
        data_size=data_size,
        config_exists=config_exists,
        files_to_remove=files_to_remove,
        dirs_to_remove=dirs_to_remove,
    )


# ══════════════════════════════════════════════════════════════════
# 卸载脚本
# ══════════════════════════════════════════════════════════════════


def get_uninstall_script(mode: str = "safe", keep_backups: bool = True) -> str:
    """
    生成卸载脚本

    Args:
        mode: "safe" - 保留数据和配置
              "full" - 删除所有内容
        keep_backups: 是否保留备份文件

    Returns:
        在 ARM 设备上执行的脚本
    """

    if mode == "safe":
        return f'''#!/bin/bash
# nastools v1.1 — 安全卸载（保留数据和配置）
set -e

SERVICE="{SERVICE_NAME}"
INSTALL_DIR="{INSTALL_DIR}"
BACKUP_DIR="{BACKUP_DIR}"

echo "═══════════════════════════════════════"
echo " nastools v1.1 — 安全卸载"
echo "═══════════════════════════════════════"
echo "  模式: 保留数据和配置"
echo ""

# 1. 停止服务
echo "[1/4] 停止服务..."
if systemctl is-active --quiet $SERVICE 2>/dev/null; then
    systemctl stop $SERVICE
    echo "      ✓ 服务已停止"
else
    echo "      - 服务未运行"
fi

# 2. 禁用并删除 systemd 服务
echo "[2/4] 移除 systemd 服务..."
if [ -f /etc/systemd/system/$SERVICE.service ]; then
    systemctl disable $SERVICE 2>/dev/null || true
    rm -f /etc/systemd/system/$SERVICE.service
    systemctl daemon-reload
    echo "      ✓ 服务已移除"
else
    echo "      - 服务未注册"
fi

# 3. 删除程序文件（保留配置和备份）
echo "[3/4] 清理程序文件..."
if [ -d "$INSTALL_DIR" ]; then
    # 删除 Python 文件
    find "$INSTALL_DIR" -maxdepth 1 -name "*.py" -type f -delete 2>/dev/null || true
    # 删除环境文件
    rm -f "$INSTALL_DIR"/*.env 2>/dev/null || true
    # 删除 __pycache__
    rm -rf "$INSTALL_DIR"/__pycache__ 2>/dev/null || true
    echo "      ✓ 程序文件已删除"
else
    echo "      - 安装目录不存在"
fi

# 4. 验证卸载
echo "[4/4] 验证卸载..."
if systemctl is-active --quiet $SERVICE 2>/dev/null; then
    echo "      ⚠ 服务仍在运行"
else
    echo "      ✓ 服务已停止"
fi

if [ -f "$INSTALL_DIR/arm_server.py" ]; then
    echo "      ⚠ arm_server.py 仍存在"
else
    echo "      ✓ 程序文件已删除"
fi

echo ""
echo "═══════════════════════════════════════"
echo " ✓ 安全卸载完成"
echo "═══════════════════════════════════════"
echo ""
echo "  保留内容:"
echo "    - 配置文件: $INSTALL_DIR/config.yaml"
echo "    - 备份目录: $BACKUP_DIR"
echo "    - 数据目录: /nas"
echo ""
echo "  如需完全删除，使用: --mode full"
'''

    else:  # mode == "full"
        return f'''#!/bin/bash
# nastools v1.1 — 完全卸载（删除所有内容）
# ⚠ 此操作不可恢复！

SERVICE="{SERVICE_NAME}"
INSTALL_DIR="{INSTALL_DIR}"
BACKUP_DIR="{BACKUP_DIR}"

echo "═══════════════════════════════════════"
echo " nastools v1.1 — 完全卸载"
echo "═══════════════════════════════════════"
echo "  ⚠ 警告: 将删除所有内容，包括数据"
echo ""

# 1. 停止服务
echo "[1/5] 停止服务..."
if systemctl is-active --quiet $SERVICE 2>/dev/null; then
    systemctl stop $SERVICE
    echo "      ✓ 服务已停止"
fi

# 2. 禁用并删除 systemd 服务
echo "[2/5] 移除 systemd 服务..."
if [ -f /etc/systemd/system/$SERVICE.service ]; then
    systemctl disable $SERVICE 2>/dev/null || true
    rm -f /etc/systemd/system/$SERVICE.service
    systemctl daemon-reload
    echo "      ✓ 服务已移除"
fi

# 3. 删除安装目录
echo "[3/5] 删除安装目录..."
if [ -d "$INSTALL_DIR" ]; then
    SIZE=$(du -sh "$INSTALL_DIR" 2>/dev/null | cut -f1)
    rm -rf "$INSTALL_DIR"
    echo "      ✓ 已删除 $INSTALL_DIR ($SIZE)"
fi

# 4. 删除数据目录
echo "[4/5] 删除数据目录..."
for d in {" ".join(DATA_DIRS)}; do
    if [ -d "$d" ]; then
        SIZE=$(du -sh "$d" 2>/dev/null | cut -f1)
        rm -rf "$d"
        echo "      ✓ 已删除 $d ($SIZE)"
    fi
done

# 5. 验证卸载
echo "[5/5] 验证卸载..."
REMAINING=0

if systemctl is-active --quiet $SERVICE 2>/dev/null; then
    echo "      ⚠ 服务仍在运行"
    REMAINING=$((REMAINING + 1))
fi

if [ -d "$INSTALL_DIR" ]; then
    echo "      ⚠ 安装目录仍存在"
    REMAINING=$((REMAINING + 1))
fi

if [ $REMAINING -eq 0 ]; then
    echo "      ✓ 完全卸载成功"
fi

echo ""
echo "═══════════════════════════════════════"
echo " ✓ 完全卸载完成"
echo "═══════════════════════════════════════"
echo ""
echo "  已删除:"
echo "    - 服务: $SERVICE"
echo "    - 安装目录: $INSTALL_DIR"
echo "    - 数据目录: /nas"
echo "    - 所有备份文件"
echo ""
echo "  如需重新安装，请使用部署功能"
'''


# ══════════════════════════════════════════════════════════════════
# 卸载后验证脚本
# ══════════════════════════════════════════════════════════════════


def get_verify_uninstall_script() -> str:
    """验证卸载是否成功"""
    return f'''#!/bin/bash
# 卸载验证脚本

SERVICE="{SERVICE_NAME}"
INSTALL_DIR="{INSTALL_DIR}"

ISSUES=0

echo "=== 卸载验证 ==="

# 检查服务
if systemctl is-active --quiet $SERVICE 2>/dev/null; then
    echo "ISSUE: 服务仍在运行"
    ISSUES=$((ISSUES + 1))
else
    echo "OK: 服务已停止"
fi

if [ -f /etc/systemd/system/$SERVICE.service ]; then
    echo "ISSUE: systemd 服务文件仍存在"
    ISSUES=$((ISSUES + 1))
else
    echo "OK: systemd 服务已移除"
fi

# 检查程序文件
if [ -f "$INSTALL_DIR/arm_server.py" ]; then
    echo "ISSUE: arm_server.py 仍存在"
    ISSUES=$((ISSUES + 1))
else
    echo "OK: 程序文件已删除"
fi

# 检查进程
if pgrep -f "arm_server.py" >/dev/null 2>&1; then
    echo "ISSUE: 进程仍在运行"
    ISSUES=$((ISSUES + 1))
else
    echo "OK: 无残留进程"
fi

echo ""
if [ $ISSUES -eq 0 ]; then
    echo "RESULT:SUCCESS"
else
    echo "RESULT:FAILED"
    echo "ISSUES:$ISSUES"
fi
'''


def parse_verify_uninstall_output(output: str) -> Tuple[bool, List[str]]:
    """
    解析卸载验证输出

    Returns:
        (是否成功, 问题列表)
    """
    lines = output.strip().split("\n")
    issues = []
    success = False

    for line in lines:
        line = line.strip()
        if line.startswith("ISSUE:"):
            issues.append(line.split(":")[1].strip())
        elif line == "RESULT:SUCCESS":
            success = True
        elif line == "RESULT:FAILED":
            success = False

    return success, issues
