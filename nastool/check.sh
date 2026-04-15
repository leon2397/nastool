#!/bin/bash
# nastool 快速诊断 - Linux Shell 脚本
# 版本: 3.0.6

echo "================================================"
echo "   nastool v3.0.6 - 快速诊断"
echo "================================================"
echo

python3 arm_diagnose.py --quick

echo
echo "================================================"
echo " 诊断完成！"
echo
echo " 更多选项："
echo "   ./fix.sh     - 自动修复问题"
echo "   ./report.sh  - 生成 HTML 报告"
echo "   ./monitor.sh - 启动监控"
echo "================================================"
