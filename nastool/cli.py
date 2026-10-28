"""
cli.py — 命令行入口

    nastool                       # 在本机跑完整检测，输出终端报告
    nastool -o all                # 同时输出终端 + JSON + HTML
    nastool --storage-path /volume1 --peer 192.168.1.10:445
    nastool --push webhook --push-url https://example.com/hook

退出码：0 健康 / 1 存在严重问题 / 2 参数或运行错误
（适合放进 cron / 定时巡检：非 0 即告警）
"""
import argparse
import os
import sys

from . import __version__
from .connectors import get_connector, connector_names
from .core.runner import RunOptions, run_diagnostics
from .reporters.html_reporter import HTMLReporter
from .reporters.json_reporter import JSONReporter
from .reporters.terminal import TerminalReporter

EXIT_OK = 0
EXIT_PROBLEM = 1
EXIT_ERROR = 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nastool",
        description=f"nastool v{__version__} — 通用 NAS 设备检测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  nastool                                  本机完整检测（终端报告）
  nastool -o all --out-dir ./reports       终端 + JSON + HTML 三份报告
  nastool --no-speed-test                  跳过读写测速（更快）
  nastool --storage-path /volume1          指定要体检的数据盘
  nastool --peer 192.168.1.10:445          顺手测对端 SMB 是否可达
  nastool --push webhook --push-url URL    把结果 POST 到你的接口
  nastool --push ainas --nas-host 127.0.0.1  登记到 AINAS 设备列表（可选）
""",
    )

    g = parser.add_argument_group("检测范围")
    g.add_argument("--storage-path", default="",
                   help="要检测的数据路径（默认自动挑选 NAS 数据盘）")
    g.add_argument("--peer", action="append", default=[], metavar="HOST:PORT",
                   help="对端连通性检查，可重复或用逗号分隔")
    g.add_argument("--no-speed-test", action="store_true", help="跳过读写速度测试")
    g.add_argument("--no-smart", action="store_true", help="跳过 SMART 检测")
    g.add_argument("--no-ai", action="store_true", help="跳过 AI 算力与推理测试")
    g.add_argument("--no-internet", action="store_true", help="跳过外网连通性检查")

    o = parser.add_argument_group("报告输出")
    o.add_argument("-o", "--output", default="terminal",
                   choices=["terminal", "json", "html", "all"],
                   help="输出格式（默认 terminal）")
    o.add_argument("--out-dir", default=".", help="报告文件保存目录（默认当前目录）")
    o.add_argument("--output-file", default="", help="指定单个输出文件路径")
    o.add_argument("-v", "--verbose", action="store_true", help="输出更多细节")
    o.add_argument("--no-color", action="store_true", help="禁用彩色输出")
    o.add_argument("-q", "--quiet", action="store_true", help="不打印进度")

    p = parser.add_argument_group("上报（可选）")
    p.add_argument("--push", default="none", choices=["none"] + connector_names(),
                   help="上报通道（默认 none，不联网）")
    p.add_argument("--push-url", default="", help="webhook 接收地址")
    p.add_argument("--push-token", default="", help="webhook 鉴权 token")
    p.add_argument("--push-header", default="Authorization", help="token 放在哪个请求头")
    p.add_argument("--nas-host", default="127.0.0.1", help="AINAS 地址（--push ainas 时用）")
    p.add_argument("--nas-port", type=int, default=8000, help="AINAS 端口")
    p.add_argument("--device-name", default="", help="上报时的设备名（默认主机名）")

    parser.add_argument("--version", action="version",
                        version=f"nastool {__version__}")
    return parser


def _collect_peers(raw: list) -> list:
    peers = []
    for item in raw or []:
        for part in str(item).split(","):
            part = part.strip()
            if part:
                peers.append(part)
    return peers


def _make_progress(quiet: bool):
    if quiet:
        return None

    def progress(msg: str) -> None:
        print(f"  \033[96m▶\033[0m {msg}", flush=True)

    return progress


def _write_reports(output: str, result, args) -> list:
    """按格式输出；返回生成的文件路径列表。"""
    written = []

    if output in ("terminal", "all"):
        rep = TerminalReporter(verbose=args.verbose, color=not args.no_color)
        rep.full(result).print()

    if output in ("json", "all"):
        jr = JSONReporter()
        jr.build(result)
        path = args.output_file if (output == "json" and args.output_file) else \
            os.path.join(args.out_dir, "nastool_report.json")
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        jr.dump(path)
        written.append(path)

    if output in ("html", "all"):
        hr = HTMLReporter()
        html = hr.build(result)
        path = args.output_file if (output == "html" and args.output_file) else \
            os.path.join(args.out_dir, "nastool_report.html")
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        hr.save(html, path)
        written.append(path)

    return written


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    if args.push != "none":
        if args.push == "webhook" and not args.push_url:
            print("错误：--push webhook 需要同时提供 --push-url", file=sys.stderr)
            return EXIT_ERROR

    if not args.quiet:
        print(f"\n  nastool v{__version__} — 通用 NAS 设备检测\n")

    options = RunOptions(
        storage_path=args.storage_path,
        peers=_collect_peers(args.peer),
        do_speed_test=not args.no_speed_test,
        do_smart=not args.no_smart,
        do_ai=not args.no_ai,
        do_internet_check=not args.no_internet,
        verbose=args.verbose,
    )

    try:
        result = run_diagnostics(options, progress=_make_progress(args.quiet))
    except Exception as e:  # noqa: BLE001 - 顶层兜底，保证退出码可判
        print(f"\n检测失败：{e}", file=sys.stderr)
        return EXIT_ERROR

    if not args.quiet:
        print(f"\n  \033[92m✓\033[0m 检测完成（{result.meta.duration_s}s）\n")

    written = _write_reports(args.output, result, args)
    if written and args.output != "json":
        for path in written:
            print(f"  📄 {path}")

    # 上报
    if args.push != "none":
        ok, msg = False, "未执行"
        try:
            if args.push == "webhook":
                connector = get_connector(
                    "webhook", url=args.push_url, token=args.push_token,
                    header_name=args.push_header,
                )
            else:
                connector = get_connector(
                    "ainas", host=args.nas_host, port=args.nas_port,
                    device_name=args.device_name,
                )
            payload = JSONReporter().build(result)
            ok, msg = connector.push(payload) if connector else (False, "未知通道")
        except Exception as e:  # noqa: BLE001
            ok, msg = False, f"上报异常：{e}"
        print(f"\n  {'✓' if ok else '✗'} {msg}")

    return EXIT_OK if result.overall_ok else EXIT_PROBLEM
