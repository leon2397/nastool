"""
cli.py — 命令行入口

    nastool                                 本机检测（终端报告）
    nastool --profile verify                二手验机视角
    nastool -o all --out-dir reports        终端 + JSON + HTML
    nastool --list-checks                   查看全部检测项（也是路线图）
    nastool --only storage.* --only security.*
    nastool --save-history --compare latest 存历史并和上次对比

退出码：0 无严重问题 / 1 存在严重问题 / 2 参数或运行错误
（适合 cron 定时巡检：非 0 即告警）
"""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .checks import *  # noqa: F401,F403 - 导入即注册全部检查项
from .connectors import connector_names, get_connector
from .diff import diff_reports
from .engine import RunOptions, run
from .history import HistoryStore
from .model import CATEGORY_NAMES, CATEGORY_ORDER
from .profiles import profile_names
from .registry import all_meta, count_by_category
from .reporters.html_reporter import HTMLReporter
from .reporters.json_reporter import JSONReporter
from .reporters.terminal import TerminalReporter, render_diff

EXIT_OK = 0
EXIT_PROBLEM = 1
EXIT_ERROR = 2


def _force_utf8_stdio() -> None:
    """
    把 stdout / stderr 切到 UTF-8。

    **为什么必须做**：Windows 上标准输出的默认编码由**系统 locale** 决定——
    英文系统是 cp1252，中文系统是 cp936。两者都编不了本工具输出的中文，
    `print` 会抛 `UnicodeEncodeError`，进程当场崩掉：连第一行横幅都打不出来，
    stdout 一片空白，退出码 1。

    这不是理论问题——GitHub Actions 的 Windows runner 就是英文 locale，
    实测 5 个 Windows 格子全挂在同一处；而中文 Windows 用户根本碰不到，
    所以本地永远复现不了。

    `errors="replace"` 兜底：万一还有编不出来的字符，换成 � 而不是让程序挂掉。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue  # 测试里可能被替换成没有 reconfigure 的对象
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError, AttributeError):
            pass  # 改不了就算了，不能因为编码问题让工具起不来


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nastool",
        description=f"nastool v{__version__} — 通用 NAS 设备检测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  nastool                                   本机体检（终端报告）
  nastool --profile verify -o all           二手验机：三份报告一起出
  nastool --list-checks                     查看全部检测项
  nastool --only storage.* --only security.*  只查存储与安全
  nastool --save-history --compare latest   存历史并和上次对比
  nastool --push webhook --push-url URL     结果 POST 到自建接口

退出码: 0 无严重问题 · 1 存在严重问题 · 2 参数/运行错误
""",
    )

    g = parser.add_argument_group("检测范围")
    g.add_argument("--storage-path", default="",
                   help="要检测的数据路径（默认自动挑选 NAS 数据盘）")
    g.add_argument("--peer", action="append", default=[], metavar="HOST:PORT",
                   help="对端连通性检查，可重复或用逗号分隔")
    g.add_argument("-p", "--profile", default="nas", choices=profile_names(),
                   help="检测场景（默认 nas；verify 二手验机 / dev 开发机 / ai 推理设备）")
    g.add_argument("--only", action="append", default=[], metavar="PATTERN",
                   help="只执行匹配的检查项，支持通配（storage.* / *.smart_*）")
    g.add_argument("--skip", action="append", default=[], metavar="PATTERN",
                   help="跳过匹配的检查项")
    g.add_argument("--enable", action="append", default=[], choices=CATEGORY_ORDER,
                   help="在当前场景上追加分类（例如在 nas 场景下加 ai）")
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
    o.add_argument("-v", "--verbose", action="store_true",
                   help="显示全部检查项与每项证据")
    o.add_argument("--no-color", action="store_true", help="禁用彩色输出")
    o.add_argument("-q", "--quiet", action="store_true", help="不打印进度")

    h = parser.add_argument_group("历史与对比")
    h.add_argument("--save-history", action="store_true", help="把本次结果存入历史库")
    h.add_argument("--history-db", default="",
                   help="历史库路径（默认 ~/.nastool/history.db）")
    h.add_argument("--history", nargs="?", type=int, const=20, default=None,
                   metavar="N", help="列出最近 N 次记录后退出（默认 20）")
    h.add_argument("--compare", nargs="?", const="latest", default=None,
                   metavar="ID", help="与历史记录逐项对比（默认上次）")
    h.add_argument("--prune-history", type=int, default=None, metavar="DAYS",
                   help="删除超过 N 天的历史记录后退出")

    s = parser.add_argument_group("自描述")
    s.add_argument("--list-checks", action="store_true", help="列出全部检测项后退出")

    p = parser.add_argument_group("上报（可选，默认完全离线）")
    p.add_argument("--push", default="none", choices=["none"] + connector_names(),
                   help="上报通道（默认 none）")
    p.add_argument("--push-url", default="", help="webhook 接收地址")
    p.add_argument("--push-token", default="", help="webhook 鉴权 token")
    p.add_argument("--push-header", default="Authorization", help="token 放在哪个请求头")
    p.add_argument("--nas-host", default="127.0.0.1", help="AINAS 地址")
    p.add_argument("--nas-port", type=int, default=8000, help="AINAS 端口")
    p.add_argument("--device-name", default="", help="上报时的设备名（默认主机名）")

    parser.add_argument("--version", action="version", version=f"nastool {__version__}")
    return parser


# ── 自描述 ──────────────────────────────────────────────────
def _disp_width(text: str) -> int:
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)


def _ljust(text: str, width: int) -> str:
    return text + " " * max(0, width - _disp_width(text))


def _print_checks() -> None:
    metas = all_meta()
    counts = count_by_category()
    print(f"\n  nastool {__version__} — 共 {len(metas)} 个检测项\n")

    for cat in CATEGORY_ORDER:
        items = [m for m in metas if m.category == cat]
        if not items:
            continue
        print(f"  {CATEGORY_NAMES.get(cat, cat)}（{counts.get(cat, 0)}）")
        for m in items:
            req = f"  依赖: {','.join(m.requires)}" if m.requires else ""
            plat = f"  平台: {','.join(m.platforms)}" if m.platforms else ""
            print(f"    {_ljust(m.id, 34)}{_ljust(m.title, 20)}{req}{plat}")
        print()


def _print_history(store: HistoryStore, limit: int) -> None:
    rows = store.list(limit=limit)
    if not rows:
        print("\n  还没有历史记录。用 --save-history 保存本次结果。\n")
        return
    print(f"\n  最近 {len(rows)} 次检测记录\n")
    print("    ID  时间                主机              场景     分数  等级  判定")
    for r in rows:
        score = "-" if r.score is None else str(r.score)
        judged = f"{r.judged}/{r.total}"
        print(f"  {r.id:>4}  {_ljust(r.ts, 20)}{_ljust(r.hostname[:14], 18)}"
              f"{_ljust(r.profile, 9)}{score:>4}  {_ljust(r.grade, 4)}{judged:>8}")
    print()


# ── 输出 ────────────────────────────────────────────────────
def _write_reports(output: str, report, args) -> list:
    written = []

    if output in ("terminal", "all"):
        TerminalReporter(verbose=args.verbose, color=not args.no_color).print(report)

    if output in ("json", "all"):
        jr = JSONReporter()
        path = args.output_file if (output == "json" and args.output_file) else \
            os.path.join(args.out_dir, "nastool_report.json")
        written.append(jr.dump(report, path))

    if output in ("html", "all"):
        hr = HTMLReporter()
        path = args.output_file if (output == "html" and args.output_file) else \
            os.path.join(args.out_dir, "nastool_report.html")
        written.append(hr.save(hr.build(report), path))

    return written


def _collect_peers(raw: list) -> list:
    peers = []
    for item in raw or []:
        for part in str(item).split(","):
            part = part.strip()
            if part:
                peers.append(part)
    return peers


def _make_progress(quiet: bool, verbose: bool = False):
    """进度输出：默认只报分类切换，避免几十行刷屏；-v 时逐项打印。"""
    if quiet:
        return None

    state = {"category": None}

    def progress(idx: int, total: int, meta) -> None:
        if verbose:
            print(f"  \033[96m▶\033[0m [{idx}/{total}] {meta.title}", flush=True)
            return
        if meta.category != state["category"]:
            state["category"] = meta.category
            print(f"  \033[96m▶\033[0m "
                  f"{CATEGORY_NAMES.get(meta.category, meta.category)}", flush=True)

    return progress


# ── 主入口 ──────────────────────────────────────────────────
def main(argv=None) -> int:
    _force_utf8_stdio()
    args = _build_parser().parse_args(argv)

    if args.list_checks:
        _print_checks()
        return EXIT_OK

    if args.push != "none" and args.push == "webhook" and not args.push_url:
        print("错误：--push webhook 需要同时提供 --push-url", file=sys.stderr)
        return EXIT_ERROR

    store = None
    need_store = args.save_history or args.compare is not None \
        or args.history is not None or args.prune_history is not None
    if need_store:
        try:
            store = HistoryStore(args.history_db or os.path.expanduser(
                "~/.nastool/history.db"))
        except Exception as e:  # noqa: BLE001
            print(f"错误：无法打开历史库：{e}", file=sys.stderr)
            return EXIT_ERROR

    if args.history is not None:
        _print_history(store, args.history)
        return EXIT_OK

    if args.prune_history is not None:
        removed = store.prune(args.prune_history)
        print(f"\n  已删除 {removed} 条超过 {args.prune_history} 天的记录\n")
        return EXIT_OK

    if not args.quiet:
        print(f"\n  nastool v{__version__} — 通用 NAS 设备检测"
              f"（场景 {args.profile}）\n")

    options = RunOptions(
        storage_path=args.storage_path,
        peers=_collect_peers(args.peer),
        do_speed_test=not args.no_speed_test,
        do_smart=not args.no_smart,
        do_ai=not args.no_ai,
        do_internet_check=not args.no_internet,
        verbose=args.verbose,
        profile=args.profile,
        only=list(args.only),
        skip=list(args.skip),
        enable=list(args.enable),
    )

    try:
        report = run(options, progress=_make_progress(args.quiet, args.verbose))
    except Exception as e:  # noqa: BLE001 - 顶层兜底，保证退出码可判
        print(f"\n检测失败：{e}", file=sys.stderr)
        return EXIT_ERROR

    if not args.quiet:
        print(f"\n  \033[92m✓\033[0m 检测完成（{report.meta.duration_s}s）\n")

    written = _write_reports(args.output, report, args)
    for path in written:
        print(f"  📄 {path}")

    # ── 历史与对比 ──
    if store is not None:
        prev = None
        if args.compare is not None:
            try:
                if args.compare == "latest":
                    prev = store.load(hostname=report.meta.hostname)
                else:
                    prev = store.load(run_id=int(args.compare))
            except ValueError:
                print(f"错误：--compare 需要记录 ID 或 latest", file=sys.stderr)
                return EXIT_ERROR

        if args.save_history or args.compare is not None:
            run_id = store.save(report)
            if not args.quiet:
                print(f"  🗂  已存历史（ID {run_id}）")

        if args.compare is not None:
            if prev is None:
                print("\n  没有可对比的历史记录（首次保存）。\n")
            else:
                if prev.get("meta", {}).get("fingerprint") and \
                        prev["meta"]["fingerprint"] != report.meta.fingerprint:
                    print("  ⚠ 历史记录的设备指纹与本次不同，对比结果可能无意义\n")
                result = diff_reports(prev, report.to_dict())
                print(render_diff(result, color=not args.no_color))

    # ── 上报 ──
    if args.push != "none":
        ok, msg = False, "未执行"
        try:
            if args.push == "webhook":
                connector = get_connector(
                    "webhook", url=args.push_url, token=args.push_token,
                    header_name=args.push_header)
            else:
                connector = get_connector(
                    "ainas", host=args.nas_host, port=args.nas_port,
                    device_name=args.device_name)
            payload = report.to_dict()
            ok, msg = connector.push(payload) if connector else (False, "未知通道")
        except Exception as e:  # noqa: BLE001
            ok, msg = False, f"上报异常：{e}"
        print(f"\n  {'✓' if ok else '✗'} {msg}")

    return EXIT_OK if report.healthy else EXIT_PROBLEM
