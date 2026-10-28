#!/usr/bin/env python3
"""selfcheck — 把 docs/STANDARDS.md 的硬规则变成可执行的检查。

用法：
    python tools/selfcheck.py            # 全部检查
    python tools/selfcheck.py -v         # 显示每项的细节

退出码：0 全绿；1 有失败。

设计原则：只检查**能用 AST 或正则可靠判断**的事。查不出的（语义矛盾、注释撒谎）
不在本脚本职责内，靠评审。
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Pattern, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001 - 老版本 Python 没有该方法
    pass

README_FILES_EXCLUDE = ("reference/", "tmpr/", "reports/", "docsrun/")


# ── 基础设施 ─────────────────────────────────────────────────

class CheckResult:
    def __init__(self, name: str) -> None:
        self.name = name
        self.ok = True
        self.problems: List[str] = []
        self.notes: List[str] = []

    def fail(self, msg: str) -> None:
        self.ok = False
        self.problems.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def walk_md() -> List[Path]:
    out: List[Path] = []
    for base, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(base, ROOT).replace("\\", "/")
        if any(rel.startswith(x) or rel == x.rstrip("/") for x in
               ("reference", "tmpr", "reports", "docsrun", ".git", ".pytest_cache")):
            dirs[:] = []
            continue
        if "__pycache__" in rel:
            continue
        for fn in files:
            if fn.endswith(".md"):
                out.append(Path(base) / fn)
    return sorted(out)


def _internal_imports(pyfile: Path) -> Set[str]:
    """返回该文件 import 的内部模块名集合（model/registry/collect/...）。"""
    tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    found: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level >= 1 and node.module:
                found.add(node.module.split(".")[0])
            elif node.level == 0 and node.module:
                found.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
    return found


def _decorated_check_functions(pyfile: Path) -> List[Tuple[str, str]]:
    """返回 [(函数名, 函数源码)]，只取带 @check(...) 装饰器的。"""
    src = pyfile.read_text(encoding="utf-8")
    tree = ast.parse(src)
    out: List[Tuple[str, str]] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and getattr(dec.func, "id", "") == "check":
                seg = ast.get_source_segment(src, node) or ""
                out.append((node.name, seg))
                break
    return out


# ── 1. 分层依赖方向（STANDARDS §1）───────────────────────────

# 允许的内部依赖白名单。与 docs/STANDARDS.md §1 的表保持一致——改这里必须同时改文档。
LAYER_DEPS: Dict[str, Set[str]] = {
    "model": set(),
    "profiles": set(),
    "history": set(),
    "registry": {"model"},
    "diff": {"model"},
    "collect": set(),
    "context": {"collect", "profiles"},
    "scoring": {"model", "profiles"},
    "checks": {"model", "registry", "collect", "checks"},
    "reporters": {"model"},
    "connectors": set(),
    "engine": {"model", "registry", "profiles", "context", "scoring", "checks"},
    "cli": None,  # 允许全部
}
_TOP_FILES = {"model": "nastool/model.py", "registry": "nastool/registry.py",
              "profiles": "nastool/profiles.py", "context": "nastool/context.py",
              "engine": "nastool/engine.py", "scoring": "nastool/scoring.py",
              "history": "nastool/history.py", "diff": "nastool/diff.py",
              "cli": "nastool/cli.py"}
_SUBPKGS = ("checks", "collect", "reporters", "connectors")


def check_layers(res: CheckResult) -> None:
    for name, path in _TOP_FILES.items():
        allowed = LAYER_DEPS[name]
        got = _internal_imports(ROOT / path)
        bad = {g for g in got
               if g in LAYER_DEPS or g in _SUBPKGS} - (got if allowed is None else allowed)
        if allowed is None:
            bad = set()
        if bad:
            res.fail(f"{path} 依赖了不允许的模块: {sorted(bad)}")


# ── 2. 库代码裸 print（STANDARDS §5）────────────────────────

def check_print(res: CheckResult) -> None:
    for pyfile in sorted((ROOT / "nastool").rglob("*.py")):
        rel = pyfile.relative_to(ROOT).as_posix()
        if rel == "nastool/cli.py" or rel.startswith("nastool/reporters/"):
            continue  # cli 与报告器是合法输出点
        tree = ast.parse(pyfile.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "print"):
                res.fail(f"{rel}:{node.lineno} 库代码裸 print（会污染 -o json 的 stdout）")


# ── 3. 静默吞异常（STANDARDS §4）─────────────────────────────

def check_silent_except(res: CheckResult) -> None:
    for pyfile in sorted((ROOT / "nastool").rglob("*.py")):
        rel = pyfile.relative_to(ROOT).as_posix()
        src = pyfile.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            body = [s for s in node.body if not isinstance(s, ast.Expr)]
            if not (len(body) == 1 and isinstance(body[0], ast.Pass)):
                continue
            # 窄捕获 + 默认值是正当降级（如 UnicodeDecodeError 换编码、ValueError 用默认数）。
            # 只拦宽捕获且没有 noqa / 原因注释的静默吞。
            seg = ast.get_source_segment(src, node) or ""
            exc = node.type
            wide = (isinstance(exc, ast.Name)
                    and exc.id in ("Exception", "BaseException"))
            if wide and "noqa" not in seg:
                res.fail(f"{rel}:{node.lineno} except Exception 里只有 pass 且无 noqa/原因"
                         "（窄捕获+默认值可以；宽捕获必须带 # noqa 和原因注释）")


# ── 3b. 文件编码与行尾（STANDARDS §4）──────────────────────

def check_encoding(res: CheckResult) -> None:
    """
    仓库内文本文件必须是 UTF-8 + LF。

    背景：Windows 上的编辑器容易把文件写成 CRLF，而本项目主要部署在
    Linux NAS 上。`.gitattributes` 已声明 `eol=lf`，git 提交时会转换，
    但**工作区**会一直不一致——下次编辑又变回 CRLF，来回反复。
    """
    targets = []
    for sub in ("nastool", "tests", "tools"):
        targets += sorted((ROOT / sub).rglob("*.py"))
    targets += sorted((ROOT / "docs").rglob("*.md"))
    targets += [ROOT / "README.md", ROOT / "CHANGELOG.md", ROOT / "VERSION"]

    for f in targets:
        if not f.exists():
            continue
        raw = f.read_bytes()
        rel = f.relative_to(ROOT).as_posix()
        if raw.startswith(b"\xef\xbb\xbf"):
            res.fail(f"{rel} 带 UTF-8 BOM")
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as e:
            res.fail(f"{rel} 不是合法 UTF-8：{e}")
            continue
        if b"\r\n" in raw:
            n = raw.count(b"\r\n")
            res.fail(f"{rel} 含 {n} 处 CRLF，应统一为 LF")


# ── 4. 版本号三处一致（STANDARDS §8）────────────────────────

def check_versions(res: CheckResult) -> None:
    v_file = read("VERSION").strip()
    m = re.search(r'__version__\s*=\s*"([^"]+)"', read("nastool/__init__.py"))
    v_init = m.group(1) if m else ""
    m = re.search(r'^version\s*=\s*"([^"]+)"', read("pyproject.toml"), re.M)
    v_pyproject = m.group(1) if m else ""
    if not (v_file == v_init == v_pyproject):
        res.fail(f"版本不一致：VERSION={v_file} __init__={v_init} pyproject={v_pyproject}")
    else:
        res.note(f"版本 {v_file}")


# ── 5. REPORT_VERSION 与文档一致 ─────────────────────────────

def check_report_version(res: CheckResult) -> None:
    m = re.search(r'REPORT_VERSION\s*=\s*"([^"]+)"', read("nastool/model.py"))
    if not m:
        res.fail("model.py 里找不到 REPORT_VERSION")
        return
    ver = m.group(1)
    output_md = read("docs/OUTPUT.md")
    for pat in (r"\*\*`report_version: ([\d.]+)`", r"当前 `\"([\d.]+)\"`"):
        found = re.findall(pat, output_md)
        for v in found:
            if v != ver:
                res.fail(f"docs/OUTPUT.md 写的 report_version {v} 与 model.py 的 {ver} 不一致")


# ── 6. 文档链接与锚点 ────────────────────────────────────────

def _github_slug(text: str) -> str:
    """
    生成 GitHub 风格的标题锚点。

    与 GitHub 实际行为对齐的关键点：**emoji 及其后的空格被一起丢弃**。
    GitHub 先移除 emoji，再把剩余空格转成连字符，所以
    「✅ DEBT-001 多源数据」的锚点是 `debt-001-多源数据`，
    不是 `-debt-001-多源数据`。
    """
    t = text.strip().lower()
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    out = []
    after_emoji = False
    for ch in t:
        cp = ord(ch)
        is_emoji = (
            0x1F000 <= cp <= 0x1FAFF      # 彩色符号与图形
            or 0x2600 <= cp <= 0x27BF    # 杂项符号与箭头
            or 0xFE0F == cp              # 变体选择符
            or 0x2B00 <= cp <= 0x2BFF    # 箭头补充
        )
        if is_emoji:
            after_emoji = True
            continue
        if after_emoji:
            after_emoji = False
            if ch == " ":
                # emoji 后的空格直接丢弃，不产生连字符
                continue
        if ch.isalnum() or ch in " -_":
            out.append(ch)
    return "".join(out).replace(" ", "-")


def _anchors_of(path: Path) -> Set[str]:
    a: Set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            a.add(_github_slug(m.group(2)))
    return a


def check_links(res: CheckResult) -> None:
    md_files = walk_md()
    link_re = re.compile(r"\[([^\]]*)\]\(([^)#\s]+)(#[^)\s]*)?\)")
    anchor_cache: Dict[Path, Set[str]] = {}
    broken = 0
    for f in md_files:
        text = f.read_text(encoding="utf-8")
        for m in link_re.finditer(text):
            target, frag = m.group(2), m.group(3)
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            path = f if not target else (f.parent / target).resolve()
            if not path.exists():
                res.fail(f"{f.relative_to(ROOT)} -> 断链: {target}")
                broken += 1
                continue
            if frag:
                frag_id = frag[1:]
                if path not in anchor_cache:
                    anchor_cache[path] = _anchors_of(path)
                if frag_id not in anchor_cache[path]:
                    res.fail(f"{f.relative_to(ROOT)} -> 锚点不存在: {target}{frag}")
                    broken += 1
    res.note(f"扫描 {len(md_files)} 个 md 文件")


# ── 7. 文档关键数字与代码一致（STANDARDS §10）───────────────

def _count_fail_capable() -> int:
    n = 0
    for pyfile in (ROOT / "nastool" / "checks").glob("*.py"):
        for _name, seg in _decorated_check_functions(pyfile):
            if "Status.FAIL" in seg:
                n += 1
    return n


def _count_tests() -> int:
    n = 0
    for pyfile in (ROOT / "tests").glob("test_*.py"):
        n += len(re.findall(r"^def (test_\w+)", pyfile.read_text(encoding="utf-8"), re.M))
    return n


def _expected_values() -> Dict[str, int]:
    from nastool.model import CATEGORY_ORDER
    from nastool.registry import all_meta
    checks = len(all_meta())
    fail_capable = _count_fail_capable()
    return {
        "checks": checks,
        "categories": len(CATEGORY_ORDER),
        "fail_capable": fail_capable,
        "non_fail": checks - fail_capable,
        "tests": _count_tests(),
    }


# (文件, 正则, 捕获组对应的期望键)。所有匹配都必须与代码一致。
NUMBER_ASSERTS: List[Tuple[str, str, List[str]]] = [
    ("README.md", r"共 \*\*(\d+) 项\*\*，分 (\d+) 类", ["checks", "categories"]),
    ("README.md", r"# (\d+) 项测试", ["tests"]),
    ("docs/CHECKS.md", r"本文是 \*\*(\d+) 个检测项的权威说明", ["checks"]),
    ("docs/CHECKS.md", r"(\d+) 项中其余 (\d+) 项\*?\*?在设计上不可能给出 FAIL",
     ["checks", "non_fail"]),
    ("docs/CHECKS-ROADMAP.md", r"## 第一部分：当前实现（(\d+) 项）", ["checks"]),
    ("docs/ARCHITECTURE.md", r"checks/  \((\d+) 项判定\)", ["checks"]),
    ("docs/README.md", r"只有 (\d+) 项能产生「严重」", ["fail_capable"]),
    ("docs/DEVELOPMENT.md", r"# 全部 (\d+) 项", ["tests"]),
    ("docs/DEVELOPMENT.md", r"# (\d+) passed", ["tests"]),
]


def check_numbers(res: CheckResult) -> None:
    exp = _expected_values()
    res.note("真实值: " + ", ".join(f"{k}={v}" for k, v in exp.items()))
    for fname, pat, keys in NUMBER_ASSERTS:
        text = read(fname)
        for m in re.finditer(pat, text):
            for i, key in enumerate(keys, start=1):
                got = int(m.group(i))
                if got != exp[key]:
                    res.fail(f"{fname}: 写了 {got}，代码实际 {exp[key]}（{key}）")


# ── 8. 文档 --flag 与 argparse 一致 ──────────────────────────

# 文档里出现、但属于其他工具、提案中命令或占位符的参数。
# 新增未知项时先确认来源再加进来，并写明属于谁。
KNOWN_FOREIGN = {
    "--all": "git 的参数（git log --all）",
    "--config": "其他工具/示例",
    "--device": "其他工具/示例",
    "--format": "其他工具/示例",
    "--interval": "其他工具/示例",
    "--json": "smartctl 的参数",
    "--junit-xml": "pytest",
    "--privileged": "docker run",
    "--rm": "docker run",
    "--sdist": "python -m build 的参数",
    "--flag": "占位符示例",
    "--mock": "其他工具/示例",
    "--pid": "其他工具/示例",
    "--push-required": "提案中（Q-002）",
    "--query": "其他工具/示例",
    "--quick": "其他工具/示例",
    "--relay": "其他工具/示例",
    "--self-test": "提案中（DEBT-011）",
    "--show": "其他工具/示例",
    "--tag": "提案中（DEBT-008）",
    "--value": "其他工具/示例",
    "--xxx": "占位符示例",
}


def _cli_flags() -> Set[str]:
    from nastool.cli import _build_parser
    flags: Set[str] = set()
    for action in _build_parser()._actions:  # noqa: SLF001
        flags.update(a for a in action.option_strings if a.startswith("--"))
    return flags


def check_flags(res: CheckResult) -> None:
    known = _cli_flags()
    flag_re = re.compile(r"(?<![\w-])(--[a-z][a-z0-9-]*)")
    foreign: Set[str] = set()
    for f in walk_md():
        for m in flag_re.finditer(f.read_text(encoding="utf-8")):
            flag = m.group(1)
            if flag not in known:
                foreign.add(flag)
    unknown = foreign - set(KNOWN_FOREIGN)
    if unknown:
        res.fail(f"文档出现但 CLI 不存在的参数: {sorted(unknown)}"
                 f"（若是其他工具的参数，加进 KNOWN_FOREIGN）")
    else:
        res.note(f"CLI 参数 {len(known)} 个，文档额外引用 "
                 f"{len(foreign & set(KNOWN_FOREIGN))} 个外来参数")


# ── 9. profile 与分类定义一致（STANDARDS §1 的延伸）─────────

def check_profiles(res: CheckResult) -> None:
    from nastool.model import CATEGORY_ORDER
    from nastool.profiles import PROFILES
    for name, p in PROFILES.items():
        for cat in p.weights:
            if cat not in CATEGORY_ORDER:
                res.fail(f"profile {name}: weights 里的 '{cat}' 不在 CATEGORY_ORDER")
        for cat in p.active:
            if cat not in CATEGORY_ORDER:
                res.fail(f"profile {name}: active 里的 '{cat}' 不在 CATEGORY_ORDER")
    res.note(f"{len(PROFILES)} 个 profile")


# ── 10. memo 台账编号与交叉引用 ──────────────────────────────

_MEMO = {
    "debt": ("docs/memo/debt.md", re.compile(r"^### (?:✅ )?DEBT-(\d+)", re.M)),
    "gotcha": ("docs/memo/gotchas.md", re.compile(r"^## GOTCHA-(\d+)", re.M)),
    "question": ("docs/memo/open-questions.md", re.compile(r"^### Q-(\d+)", re.M)),
}


def check_memo(res: CheckResult) -> None:
    defined: Dict[str, Set[str]] = {}
    for key, (path, pat) in _MEMO.items():
        ids = pat.findall(read(path))
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            res.fail(f"{path} 重复编号: {sorted(dup)}")
        defined[key] = set(ids)

    # (?![\dx]) 排除 "GOTCHA-00x" 这类占位符写法
    ref_pats = {
        "debt": re.compile(r"\bDEBT-(\d+)(?![\dx])"),
        "gotcha": re.compile(r"\bGOTCHA-(\d+)(?![\dx])"),
        "question": re.compile(r"\bQ-(\d+)(?![\dx])"),
    }
    for f in walk_md():
        text = f.read_text(encoding="utf-8")
        for key, pat in ref_pats.items():
            for m in pat.finditer(text):
                rid = m.group(1)
                if rid not in defined.get(key, set()):
                    res.fail(f"{f.relative_to(ROOT)}: 引用了不存在的 "
                             f"{key.upper()}-{rid}")


# ── 11. 版本计划覆盖（memo 台账不得漏排期）─────────────────

def check_version_plan(res: CheckResult) -> None:
    plan_path = ROOT / "docs" / "VERSION-PLAN.md"
    if not plan_path.exists():
        res.fail("缺少 docs/VERSION-PLAN.md（技术债与未决问题必须在其中有归属）")
        return
    plan = plan_path.read_text(encoding="utf-8")

    debt_text = read("docs/memo/debt.md")
    all_debt = set(re.findall(r"^### (?:✅ )?DEBT-(\d+)", debt_text, re.M))
    done_debt = set(re.findall(r"^### ✅ DEBT-(\d+)", debt_text, re.M))
    open_debt = all_debt - done_debt

    q_text = read("docs/memo/open-questions.md")
    all_q = set(re.findall(r"^### (?:✅ )?Q-(\d+)", q_text, re.M))
    closed_q = set(re.findall(r"^### ✅ Q-(\d+)", q_text, re.M))
    open_q = all_q - closed_q

    plan_debt = set(re.findall(r"DEBT-(\d+)(?![\dx])", plan))
    plan_q = set(re.findall(r"\bQ-(\d+)(?![\dx])", plan))

    missing_debt = sorted(open_debt - plan_debt, key=int)
    missing_q = sorted(open_q - plan_q, key=int)
    if missing_debt:
        res.fail(f"技术债未在版本计划中排期: DEBT-{', DEBT-'.join(missing_debt)}")
    if missing_q:
        res.fail(f"未决问题未在版本计划中排期: Q-{', Q-'.join(missing_q)}")
    if not missing_debt and not missing_q:
        res.note(f"覆盖 {len(open_debt)} 条未修债 + {len(open_q)} 个开放问题")


# ── 12. 产品化规划与版本计划一致 ───────────────────────────

def check_product_plan(res: CheckResult) -> None:
    """
    产品化规划必须存在，且它引用的债/问题必须真的在版本计划里排了期。

    背景：产品化规划是"这产品长成什么样"，版本计划是"什么时候动手"。
    两份文档如果脱节，规划就变成没有人执行的愿望书——这正是本项目
    吃过亏的地方（前身项目的设计文档留下来了，代码内核却丢了）。
    """
    plan_path = ROOT / "docs" / "PRODUCT-PLAN.md"
    if not plan_path.exists():
        res.fail("缺少 docs/PRODUCT-PLAN.md（产品化规划是版本计划的上游）")
        return
    plan = plan_path.read_text(encoding="utf-8")

    version_plan_path = ROOT / "docs" / "VERSION-PLAN.md"
    version_plan = version_plan_path.read_text(encoding="utf-8")

    # 双向引用：缺一边就会各自漂移。
    # 必须检查**链接形式**而不是纯文本——文档里写一句「见 PRODUCT-PLAN.md」
    # 不算引用，读者点不过去。变异测试证明过这个区别。
    if not re.search(r"\[PRODUCT-PLAN\.md\]\(PRODUCT-PLAN\.md", version_plan):
        res.fail("docs/VERSION-PLAN.md 没有以链接形式引用 PRODUCT-PLAN.md"
                 "（两份规划会脱节）")
    if not re.search(r"\[VERSION-PLAN\.md\]\(VERSION-PLAN\.md", plan):
        res.fail("docs/PRODUCT-PLAN.md 没有以链接形式引用 VERSION-PLAN.md"
                 "（排期不在它那儿）")

    # 规划里引用的债与问题必须在版本计划中有归属
    plan_debt = set(re.findall(r"DEBT-(\d+)(?![\dx])", plan))
    plan_q = set(re.findall(r"\bQ-(\d+)(?![\dx])", plan))
    sched_debt = set(re.findall(r"DEBT-(\d+)(?![\dx])", version_plan))
    sched_q = set(re.findall(r"\bQ-(\d+)(?![\dx])", version_plan))

    orphan_debt = sorted(plan_debt - sched_debt, key=int)
    orphan_q = sorted(plan_q - sched_q, key=int)
    if orphan_debt:
        res.fail(f"产品化规划引用但未在版本计划排期: DEBT-{', DEBT-'.join(orphan_debt)}")
    if orphan_q:
        res.fail(f"产品化规划引用但未在版本计划排期: Q-{', Q-'.join(orphan_q)}")

    # LICENSE 必须在仓库里（产品化的法律基础）
    if not (ROOT / "LICENSE").exists():
        res.fail("缺少 LICENSE 文件（README 声明 MIT 但仓库无许可正本，见 DEBT-015）")

    if not orphan_debt and not orphan_q:
        res.note(f"规划覆盖 {len(plan_debt)} 条债 + {len(plan_q)} 个问题，"
                 f"全部已在版本计划排期")


# ── 主流程 ───────────────────────────────────────────────────

CHECKS: List[Tuple[str, Callable[[CheckResult], None]]] = [
    ("分层依赖方向", check_layers),
    ("库代码裸 print", check_print),
    ("静默吞异常", check_silent_except),
    ("文件编码与行尾", check_encoding),
    ("版本号三处一致", check_versions),
    ("REPORT_VERSION 一致", check_report_version),
    ("文档链接与锚点", check_links),
    ("文档数字与代码一致", check_numbers),
    ("文档 --flag 真实性", check_flags),
    ("profile 分类一致性", check_profiles),
    ("memo 台账编号与引用", check_memo),
    ("版本计划覆盖", check_version_plan),
    ("产品化规划一致", check_product_plan),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="nastool 开发规范自检")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    width = max(len(n) for n, _ in CHECKS)
    failed = 0
    print("nastool selfcheck")
    print("─" * (width + 12))
    for name, fn in CHECKS:
        res = CheckResult(name)
        try:
            fn(res)
        except Exception as e:  # noqa: BLE001 - 自检自身不许崩，错误要可见
            res.ok = False
            res.problems.append(f"检查器异常: {type(e).__name__}: {e}")
        mark = "OK  " if res.ok else "FAIL"
        print(f"  {mark}  {name.ljust(width)}", end="")
        if res.notes and args.verbose:
            print(f"   ({'; '.join(res.notes)})", end="")
        print()
        for p in res.problems:
            print(f"        - {p}")
        failed += 0 if res.ok else 1
    print("─" * (width + 12))
    total = len(CHECKS)
    print(f"  {total - failed}/{total} 通过" + ("" if failed else "，全部规范检查绿 ✅"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
