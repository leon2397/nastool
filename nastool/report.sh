#!/bin/bash
# nastool 生成报告 - Linux Shell 脚本
# 版本: 3.0.6

echo "================================================"
echo "   nastool v3.0.6 - 生成报告"
echo "================================================"
echo

REPORT_FILE="report_$(date +%Y%m%d_%H%M).html"

python3 arm_diagnose.py --output "$REPORT_FILE" --format html

echo
echo "================================================"
echo " 报告已生成: $REPORT_FILE"
echo
echo " 用浏览器打开查看报告"
echo "================================================"
