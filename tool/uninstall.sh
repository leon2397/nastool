#!/bin/bash
# NASTool v4.2 本地测试卸载脚本
# 此脚本仅清理tool目录下的测试文件，不会影响系统

echo "================================================"
echo "🗑️ NASTool v4.2 测试卸载脚本"
echo "================================================"

TOOL_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

echo ""
echo "⚠️ 即将删除以下目录:"
echo "   $TOOL_DIR"
echo ""
echo "此操作将删除:"
echo "   - 测试脚本 (local_test.py)"
echo "   - 测试报告 (test_report.json)"
echo ""
echo "注意: 此操作不会影响系统文件或NASTool核心模块"
echo ""

read -p "确认卸载? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔄 开始卸载..."
    
    # 删除测试文件
    rm -f "$TOOL_DIR/local_test.py"
    echo "   ✅ 删除 local_test.py"
    
    rm -f "$TOOL_DIR/test_report.json"
    echo "   ✅ 删除 test_report.json"
    
    # 检查目录是否为空
    if [ -z "$(ls -A "$TOOL_DIR")" ]; then
        rmdir "$TOOL_DIR"
        echo "   ✅ 删除空目录 tool/"
    fi
    
    echo ""
    echo "✅ 卸载完成!"
    echo "================================================"
else
    echo ""
    echo "❌ 取消卸载"
    echo "================================================"
fi
