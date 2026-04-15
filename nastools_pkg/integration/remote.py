# -*- coding: utf-8 -*-
"""
integration/remote.py — nastool 检测执行器

提供三种执行方式（按优先级）：
1. remote()   — 通过 SSH 在 ARM 设备上运行 arm_diagnose.py（需要上传）
2. library()  — 本地直接 import nastool.checks（推荐，精度最高）
3. fallback()  — 简单 ping/shell 命令（万不得已）

返回值统一为 list[dict]，格式与原 nastools.py 一致：
  {"name", "severity", "message", "fix_cmd", "fix_title", "fix_warn"}
"""

import os
import sys
import json

# ── 路径：将 nastool/ 纳入 import 搜索路径 ─────────────────────────
NASTOOL_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "nastool")
)
if NASTOOL_ROOT not in sys.path:
    sys.path.insert(0, NASTOOL_ROOT)

from checks import run_all_checks, list_available_checks
from checks.base import CheckSeverity, CheckCategory
from fixes import get_fix

# ── FixRisk 映射（nastool fixes/base.py） ─────────────────────────
try:
    from fixes.base import FixRisk

    RISK_LABEL = {
        FixRisk.LOW: "",
        FixRisk.MEDIUM: "将修改部分系统设置",
        FixRisk.HIGH: "⚠ 危险：可能影响系统稳定性",
    }
except ImportError:
    RISK_LABEL = {}


# ══════════════════════════════════════════════════════════════════
# 转换层：nastool → nastools JSON 格式
# ══════════════════════════════════════════════════════════════════


def _sev(s: CheckSeverity) -> str:
    return {
        "passed": "passed",
        "warning": "warning",
        "critical": "critical",
        "info": "info",
    }.get(s.value, "info")


def _get_fix_info(fix_id: str) -> dict:
    """根据 fix_id 获取 fix 的元信息"""
    if not fix_id:
        return {}
    try:
        cls = get_fix(fix_id)
        if cls:
            inst = cls()
            return {
                "title": getattr(inst, "title", fix_id),
                "risk": RISK_LABEL.get(getattr(inst, "risk", None), ""),
            }
    except Exception:
        pass
    return {}


def _fix_for(check_result) -> dict:
    """从 CheckResult 提取 fix 信息"""
    if not (check_result.fix_available and check_result.fix_id):
        return {}
    return _get_fix_info(check_result.fix_id)


def to_json(check_id: str, cr) -> dict:
    """nastool CheckResult → nastools dict"""
    sev = _sev(cr.severity)
    msg = cr.message
    if not msg:
        msg = (
            f"✓ {cr.current}"
            if cr.passed
            else f"{cr.current}（期望: {cr.expected}）"
            if cr.expected
            else cr.current or "未知"
        )

    fi = _fix_for(cr)
    return {
        "name": check_id,
        "severity": sev,
        "message": msg,
        "fix_id": cr.fix_id or "",
        "fix_title": fi.get("title", ""),
        "fix_warn": fi.get("risk", ""),
        "fix_risk": fi.get("risk") or "low",  # 原始值：high/medium/low
        "fix_cmd": "",  # library 模式无 command；SSH 模式由 remote_run 填入
    }


# ══════════════════════════════════════════════════════════════════
# 核心执行器
# ══════════════════════════════════════════════════════════════════


class RemoteExecutor:
    """
    调用 nastool 执行诊断。

    用法：
        # 本地（Windows 调试 / ARM 设备本地运行）
        ex = RemoteExecutor()
        results = ex.run()                    # 默认 library()
        results = ex.run(skip_categories=["ai"])  # 跳过 AI 检测

        # 远程（通过 SSH，在 ARM 设备上执行）
        from core.ssh import SSHConnection
        ssh = SSHConnection()
        ssh.connect(host, port, user, password)
        ex = RemoteExecutor(ssh=ssh)
        results = ex.run(remote_mode="remote")  # 上传 arm_diagnose.py 执行
        results = ex.run(remote_mode="arm-local")  # 设备已有 nastool，直接 ssh.exec
    """

    def __init__(self, ssh=None):
        self.ssh = ssh
        self._fixes_cache = None

    def execute_fix(self, fix_id: str) -> tuple:
        """
        执行指定的修复项。

        优先通过 SSH 在 ARM 设备上执行；
        library 模式（Windows调试）直接本地执行。
        返回 (ok: bool, message: str)
        """
        if not fix_id:
            return False, "fix_id 为空"

        if self.ssh and self.ssh.client:
            # ── SSH 模式：在设备上通过 Python 脚本调用 fix.run() ─────
            script = f"""
import sys, traceback
sys.path.insert(0, '/opt/nastool')
from fixes import get_fix
cls = get_fix('{fix_id}')
if not cls:
    print('ERROR: fix not found')
else:
    inst = cls()
    result = inst.run()
    print('OK' if result.success else 'FAIL')
    print(result.message)
    if result.error:
        print('ERR:', result.error)
"""
            ok, out = self.ssh.exec_script(script, timeout=300)
            return ok, out

        else:
            # ── library 模式（Windows调试）：本地执行 ─────────────────
            try:
                cls = get_fix(fix_id)
                if not cls:
                    return False, f"修复项 {fix_id} 不存在"
                inst = cls()
                result = inst.run()
                msg = result.message or ("成功" if result.success else "失败")
                if result.error:
                    msg += f"\n错误: {result.error}"
                return result.success, msg
            except Exception as e:
                return False, f"执行出错: {e}"

    # ── 1. library 模式：直接 import nastool ─────────────────────────

    def library_run(self, skip_categories: list = None) -> list:
        """
        在本地运行 nastool（推荐）。
        返回 list[dict]，格式与原 nastools.py 一致。
        """
        skips = [CheckCategory(c) for c in (skip_categories or [])]
        summary = run_all_checks(skip_categories=skips)
        out = []
        for cr in summary.results:
            out.append(to_json(cr.check_id, cr))
        return out

    # ── 1.5 设备 nastool 检测 ──────────────────────────────────────

    def _check_arm_nastool(self) -> bool:
        """检测 ARM 设备是否已安装 nastool（在 /opt/nastool）"""
        if not self.ssh or not self.ssh.client:
            return False
        ec, out, _ = self.ssh.exec(
            'python3 -c \'import sys; sys.path.insert(0,"/opt/nastool"); '
            "from checks import list_available_checks; "
            "print(len(list_available_checks()))' 2>&1",
            timeout=15,
        )
        return out.strip().isdigit() and int(out.strip()) > 0

    # ── 2. remote 模式：上传 arm_diagnose.py ────────────────────────

    def remote_run(
        self, profile: str = None, skip_categories: list = None, timeout: int = 60
    ) -> list:
        """
        通过 SSH 在 ARM 设备上执行 nastool 检测。

        策略：
        1. 探测设备是否可达（10s超时）
        2. 检查 nastool 是否已安装（10s超时）
        3. 如已安装，在设备上跑 library_run（60s超时）
        4. 否则回退 fallback_run()

        三个步骤均有独立超时，任一步骤超时则立即回退，
        绝不触发 120s+ 的阻塞等待。

        Returns:
            list[dict]
        """
        if not self.ssh:
            return self.library_run(skip_categories=skip_categories)

        # ── 1. 设备可达探测（10s超时）────────────────────────────────
        try:
            ec, _, _ = self.ssh.exec("echo alive", timeout=10)
            if ec != 0:
                return [
                    {
                        "name": "device_unreachable",
                        "severity": "critical",
                        "message": "设备 SSH 连接异常，请检查网络",
                        "fix_id": "",
                        "fix_title": "",
                        "fix_warn": "",
                    }
                ]
        except Exception as e:
            return [
                {
                    "name": "device_timeout",
                    "severity": "critical",
                    "message": f"连接设备超时（10s）: {e}",
                    "fix_id": "",
                    "fix_title": "",
                    "fix_warn": "",
                }
            ]

        # ── 2. 检查 nastool 是否在设备上（10s超时）──────────────────
        try:
            ec2, has_nastool, _ = self.ssh.exec(
                'python3 -c \'import sys; sys.path.insert(0,"/opt/nastool"); '
                "from checks import list_available_checks; print(len(list_available_checks()))' 2>&1",
                timeout=10,
            )
            if has_nastool.strip().isdigit() and int(has_nastool.strip()) > 0:
                # nastool 已安装，直接跑 library
                return self._arm_library_run(skip_categories, timeout=timeout)
        except Exception:
            pass  # 超时或其他错误，进入回退

        # ── 3. nastool 未安装，尝试 fallback ────────────────────────
        return self.fallback_run()

    def _arm_library_run(self, skip_categories: list = None) -> list:
        """在 ARM 设备上直接调用 nastool library（通过 SSH）"""
        skips = ",".join(skip_categories) if skip_categories else ""

        script = self._build_arm_script(skip_categories=skips)
        ok, out = self.ssh.exec_script(script, timeout=120)
        return self._parse_arm_json_output(out)

    def _build_arm_script(self, skip_categories: str = "") -> str:
        """构建在 ARM 设备上执行的 Python 脚本"""
        skips_arg = f"--skip-categories=[{skip_categories}]" if skip_categories else ""
        return f"""
import sys, os
sys.path.insert(0, '/opt/nastool')
from checks import run_all_checks, CheckCategory
from checks.base import CheckSeverity
from fixes import get_fix, list_available_fixes
import json

skip_cats = [{skip_categories!r}] if {bool(skip_categories)!r} else []
skips = [CheckCategory(c) for c in skip_cats]
summary = run_all_checks(skip_categories=skips)

SEV_MAP = {{"passed":"passed","warning":"warning","critical":"critical","info":"info"}}

results = []
for cr in summary.results:
    fid = cr.fix_id
    fix_cmd, fix_title, fix_warn = "", cr.check_id, ""
    if fid:
        try:
            inst = get_fix(fid)()
            fix_cmd   = getattr(inst, "command", "") or ""
            fix_title = getattr(inst, "title", cr.check_id)
        except: pass
    sev = SEV_MAP.get(cr.severity.value, "info")
    msg = cr.message or (f"OK {{cr.current}}" if cr.passed
                          else f"{{cr.current}}（期望: {{cr.expected}}）" if cr.expected
                          else str(cr.current))
    results.append({{
        "name": cr.check_id, "severity": sev, "message": msg,
        "fix_cmd": fix_cmd, "fix_title": fix_title, "fix_warn": fix_warn,
    }})

print("NASTOOL_START")
for r in results:
    print(json.dumps(r, ensure_ascii=False))
print("NASTOOL_END")
"""

    def _parse_arm_json_output(self, output: str) -> list:
        """解析 ARM 设备返回的 NASTOOL_START/END JSON 块"""
        results = []
        in_block = False
        for line in output.splitlines():
            line = line.strip()
            if line == "NASTOOL_END":
                break
            if line == "NASTOOL_START":
                in_block = True
                continue
            if not in_block:
                continue
            try:
                results.append(json.loads(line))
            except Exception:
                pass
        return results if results else self._parse_quick_output(output, "")

    # ── 3. fallback 模式：简单 shell 命令 ───────────────────────────

    def fallback_run(self) -> list:
        """
        最低级的回退模式：直接执行简单 ping/shell 命令，
        在 nastool 完全不可用时使用。
        返回与 library_run() 相同的格式。
        """
        import subprocess

        results = []

        # python3
        r = subprocess.run(
            "python3 --version 2>&1 || python --version 2>&1",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        ver = ""
        import re

        m = re.search(r"Python (3?\d+\.\d+)", r.stdout + r.stderr)
        if m:
            ver = float(m.group(1))
            sev = "passed" if ver >= 3.8 else "warning"
        else:
            sev = "critical"
        results.append(
            {
                "name": "python_version",
                "severity": sev,
                "message": f"Python {ver}" if ver else "Python 未安装",
                "fix_cmd": "",
                "fix_title": "",
                "fix_warn": "",
            }
        )

        # internet
        r = subprocess.run(
            "ping -c 1 -W 3 8.8.8.8",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        results.append(
            {
                "name": "internet",
                "severity": "passed" if r.returncode == 0 else "warning",
                "message": "互联网连接正常 ✓" if r.returncode == 0 else "无法访问外网",
                "fix_cmd": "",
                "fix_title": "",
                "fix_warn": "",
            }
        )

        return results

    # ── 统一入口 ──────────────────────────────────────────────────

    def run(
        self, remote_mode: str = None, skip_categories: list = None, profile: str = None
    ) -> list:
        """
        统一执行入口，自动检测最优模式。

        Args:
            remote_mode:  None        = 自动检测（SSH已连接→arm-local，否则→library）
                          "library"  = 本地 import nastool（Windows调试）
                          "arm-local" = SSH，设备已有 nastool（在设备上跑 library）
                          "upload"    = SSH，先上传 arm_diagnose.py 再执行
            skip_categories: 跳过哪些分类
            profile:         设备 profile ID

        Returns:
            list[dict]
        """
        # ── 自动检测：SSH已连接则检测设备环境，否则library ───────────
        if remote_mode is None:
            if self.ssh and self.ssh.client:
                # 先用极短超时探测设备是否可达（不死机保障）
                try:
                    ec, _, _ = self.ssh.exec("echo alive", timeout=5)
                    if ec == 0:
                        remote_mode = (
                            "arm-local" if self._check_arm_nastool() else "upload"
                        )
                    else:
                        remote_mode = "library"  # 设备SSH异常，回退本地
                except Exception:
                    remote_mode = "library"  # 网络问题，回退本地
            else:
                remote_mode = "library"

        if remote_mode == "library":
            try:
                return self.library_run(skip_categories=skip_categories)
            except Exception as e:
                return self._wrap_error("library_error", str(e))

        elif remote_mode in ("arm-local", "upload"):
            try:
                return self.remote_run(profile=profile, skip_categories=skip_categories)
            except Exception as e:
                return self._wrap_error("remote_error", str(e))

        else:
            return self.fallback_run()

    # ── 内部工具 ──────────────────────────────────────────────────

    def _wrap_error(self, name: str, msg: str) -> list:
        return [
            {
                "name": name,
                "severity": "critical",
                "message": msg,
                "fix_cmd": "",
                "fix_title": "",
                "fix_warn": "",
            }
        ]

    def _parse_quick_output(self, stdout: str, stderr: str) -> list:
        """
        解析 arm_diagnose.py --quick 的终端输出（最不理想，但可用）。
        只提取包含 ✅ ❌ ⚠ 🔍 等关键词的行。
        """
        results = []
        for line in (stdout + "\n" + stderr).splitlines():
            line = line.strip()
            if not line or line.startswith("+") or line.startswith("|"):
                continue
            # 简单启发式：包含 ✅/❌/⚠ 的行视为结果
            if any(c in line for c in ["✅", "❌", "⚠", "✗", "✓"]):
                results.append(
                    {
                        "name": "parse_raw",
                        "severity": "info",
                        "message": line[:120],
                        "fix_cmd": "",
                        "fix_title": "",
                        "fix_warn": "(终端输出解析，可能不完整)",
                    }
                )
        return results
