#!/bin/bash
# nastool 一键启动 - Linux Shell 脚本
# 版本: 3.0.6

while true; do
    clear
    echo
    echo "  ================================================================"
    echo "     nastool v3.0.6 - ARM 设备诊断工具"
    echo "  ================================================================"
    echo
    echo "   请选择操作："
    echo
    echo "   [1] 快速检查     - 30秒快速诊断（推荐新手）"
    echo "   [2] 完整诊断     - 深度检查所有项目"
    echo "   [3] 自动修复     - 自动修复检测到的问题"
    echo "   [4] 生成报告     - 导出 HTML/JSON 报告"
    echo "   [5] 启动监控     - 持续监控设备状态"
    echo "   [6] 配置向导     - 首次使用配置"
    echo "   [7] 查看帮助     - 显示完整使用说明"
    echo
    echo "   [0] 退出"
    echo
    echo "  ================================================================"
    read -p "请输入选项 [0-6]: " choice
    
    case $choice in
        1)
            clear
            echo
            echo "  执行快速诊断..."
            echo
            python3 arm_diagnose.py --quick
            read -p "按回车继续..."
            ;;
        2)
            clear
            echo
            echo "  执行完整诊断..."
            echo
            python3 arm_diagnose.py --full
            read -p "按回车继续..."
            ;;
        3)
            clear
            echo
            echo "  执行自动修复..."
            echo
            python3 arm_diagnose.py --fix --auto
            read -p "按回车继续..."
            ;;
        4)
            clear
            echo
            echo "  生成诊断报告..."
            echo
            REPORT_FILE="report_$(date +%Y%m%d_%H%M).html"
            python3 arm_diagnose.py --output "$REPORT_FILE" --format html
            echo
            echo "  报告已生成: $REPORT_FILE"
            read -p "按回车继续..."
            ;;
        5)
            clear
            echo
            echo "  启动监控模式..."
            echo "  按 Ctrl+C 停止"
            echo
            python3 arm_diagnose.py --monitor
            ;;
        6)
            clear
            echo
            echo "  启动配置向导..."
            echo
            python3 arm_diagnose.py --setup
            read -p "按回车继续..."
            ;;
        7)
            clear
            echo
            echo "  ================================================================"
            echo "   使用说明"
            echo "  ================================================================"
            echo
            echo "  命令行用法："
            echo "    python3 arm_diagnose.py              # 快速诊断"
            echo "    python3 arm_diagnose.py --full       # 完整诊断"
            echo "    python3 arm_diagnose.py --fix        # 修复问题"
            echo "    python3 arm_diagnose.py --output report.html --format html"
            echo
            echo "  快捷脚本："
            echo "    ./check.sh    - 快速诊断"
            echo "    ./fix.sh      - 自动修复"
            echo "    ./report.sh   - 生成报告"
            echo "    ./monitor.sh  - 启动监控"
            echo
            echo "  更多信息请查看 README.md"
            echo
            read -p "按回车继续..."
            ;;
        0)
            echo
            echo "  感谢使用 nastool！"
            echo
            sleep 1
            exit 0
            ;;
        *)
            ;;
    esac
done
