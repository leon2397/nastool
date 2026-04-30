#!/usr/bin/env python3
"""
nastool v4.0 - Command Line Interface

重构后的入口文件，负责命令解析和分发。实际逻辑在 commands/ 目录下。
"""

import sys
import argparse

# 版本
__version__ = "4.0.0"

# 导入所有命令（自动注册）
from nastool_cli.commands import CommandRegistry
from nastool_cli.commands.diagnose import DiagnoseCommand
from nastool_cli.commands.device import DeviceCommand


def create_parser() -> argparse.ArgumentParser:
    """创建参数解析器"""
    parser = argparse.ArgumentParser(
        prog="nastool",
        description="NASTool v4.0 - ARM Device Diagnostic Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nastool diagnose                    # Quick diagnosis
  nastool diagnose --full             # Full diagnosis
  nastool device list                 # List devices
  nastool device add 192.168.1.100    # Add device
  
For more help: nastool <command> --help
        """.strip()
    )
    
    parser.add_argument("--version", action="version", version=f"nastool {__version__}")
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # 动态注册所有命令
    for cmd_name in CommandRegistry.list_commands():
        cmd = CommandRegistry.get(cmd_name)
        if cmd and cmd.name == cmd_name:  # 避免名称重复注册
            cmd_parser = subparsers.add_parser(
                cmd.name,
                help=cmd.help,
                aliases=cmd.aliases
            )
            cmd.add_arguments(cmd_parser)
    
    return parser


def main() -> int:
    """主入口"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 没有子命令时默认执行 diagnose
    if not args.command:
        args.command = "diagnose"
        # 添加 diagnose 的默认参数
        args.full = False
        args.mock = None
        args.output = None
        args.json = False
        args.no_color = False
        args.target = None
        args.parallel = 10
    
    # 获取并执行命令
    cmd = CommandRegistry.get(args.command)
    if cmd:
        return cmd.execute(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
