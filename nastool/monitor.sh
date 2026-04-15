#!/bin/bash
# nastool 启动监控 - Linux Shell 脚本
# 版本: 3.0.6

echo "================================================"
echo "   nastool v3.0.6 - 启动监控"
echo "================================================"
echo
echo " 监控模式将在后台运行，定期检查设备状态"
echo " 按 Ctrl+C 停止监控"
echo

python3 arm_diagnose.py --monitor
