# nastools V6.0 升级计划

> 版本日期：2026-04-15
> 当前版本：v5.0.2
> 目标版本：v6.0.0

---

## 一、现状分析

### 1.1 组件现状

| 组件 | 当前版本 | 代码规模 | 状态 |
|------|----------|----------|------|
| **nastool** 诊断引擎 | v5.0.2 | 158文件，~5000行 | 🟢 成熟 |
| **Relay Server** 中继 | v2.0.0 | 4文件, ~600行 | 🟡 基础可用 |
| **ARM Agent** | v2.0.0 | ~600行 | 🟡 基础可用 |
| **nastools_pkg** Windows GUI | v1.2 | 32文件, ~2000行 | 🟡 基础可用 |
| **Web Dashboard** | v1.0 | ~500行 | 🔴 未完成 |

### 1.2 术语翻译覆盖率

| 指标 | 数值 | 状态 |
|------|------|------|
| 总检测项 | 82 | — |
| 有术语翻译 | 82 | ✅ **100% 覆盖** |
| 有健康评分权重 | 82 | ✅ **100% 覆盖** |

> 来源：`_check_exact.py` 验证（2026-04-15）

### 1.3 技术债务（来自 TECH_DEBT.md）

| 债务 | 优先级 | 工时 |
|------|--------|------|
| 日志记录点缺失（71处） | P2 | ~4h |
| 核心模块 docstring 缺失 | P2 | ~3h |
| 测试覆盖率 <10% | P1 | ~16h |
| Relay 路径验证缺失 | P1 | ~2h |
| 文档缺失（API/架构/开发指南）| P1 | ~8h |
| GUI 测试缺失 | P2 | ~8h |

### 1.4 版本演进

```
v4.0.0  架构重构 ✅
v4.0.1  代码质量 ✅
v4.0.2  工具属性强化 ✅（82项检测）
v4.1.0  部署能力强化 ✅（Relay+Agent）
v4.2.0  跨网远程管理 ✅（WebSocket中继）
v5.0.0  82项检测验证 ✅
v5.0.1  Mock数据支持 ✅
v5.0.2  健康评分/术语翻译优化 ✅
─── 当前：v5.0.2 ───
v5.0.3  USB连接验证 ⬜
v5.0.4  SSH连接验证 ⬜
v5.0.5  Relay连接验证 ⬜
v5.0.6  设备覆盖扩展 ⬜
v5.0.7  修复功能验证 ⬜
v5.0.8  报告优化 ⬜
─── V6.0 目标 ───
```

---

## 二、V6.0 核心目标

| 目标 | 说明 | 优先级 |
|------|------|--------|
| **GUI 产品化** | Tkinter → PyInstaller 单文件可执行，0门槛分发 | P0 |
| **离线安装包** | 无网络也能安装和使用 nastools | P1 |
| **定时扫描** | 自动周期检测 + 报告推送 | P1 |
| **测试覆盖率** | 单元测试覆盖率 >60% | P1 |
| **CI/CD 流水线** | GitHub Actions 自动测试 + 发布 | P2 |

---

## 三、P0 任务详解

### 3.1 GUI 产品化

**目标**：生成单文件 Windows 可执行文件，用户双击即用

#### 技术方案

| 组件 | 选型 |
|------|------|
| 打包工具 | **PyInstaller**（无需 VS Build Tools）|
| 依赖管理 | `requirements-gui.txt` |
| 图标 | 生成自定义 .ico 文件 |
| 加密 | `--key` 保护关键代码（可选）|

#### nastools_pkg 重构

```
nastools_pkg/
├── main.py              # 入口（已存在）
├── gui/
│   ├── app.py           # 主窗口（~430行）
│   ├── theme.py         # 深色主题（已存在）
│   ├── usb_dialog.py     # USB连接（已存在）
│   ├── relay_dialog.py  # Relay连接（已存在）
│   ├── backup_dialog.py  # 本地备份（已存在）
│   ├── rollback_dialog.py # 回滚（已存在）
│   ├── nas_health_dialog.py  # NAS健康（新增）
│   ├── network_health_dialog.py  # 网络（新增）
│   ├── storage_health_dialog.py  # 存储（新增）
│   ├── system_health_dialog.py  # 系统（新增）
│   └── upnp_dialog.py   # UPnP扫描（新增）
├── core/
│   ├── ssh.py           # SSH连接（已存在）
│   ├── adb.py          # ADB连接（新增）
│   └── safety.py        # 安全检查（已存在）
├── integration/
│   └── remote.py        # 远程执行（已存在）
├── scripts/
│   ├── deploy.py        # 部署（已存在）
│   ├── uninstall.py     # 卸载（已存在）
│   └── verify.py        # 验证（已存在）
└── utils/
    ├── notifications.py  # 通知（已存在 tkinter）
    └── detect_history.py # 历史（已存在）
```

#### PyInstaller 配置文件

```python
# nastools_pkg.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 包含配置文件和资源
        ('../nastools/config', 'nastools/config'),
        ('../nastools/profiles', 'nastools/profiles'),
        ('gui/theme.py', 'gui'),
    ],
    hiddenimports=[
        'tkinter', 'paramiko', 'yaml', 'pygments',
        'nastools.config', 'nastools.logger',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['test'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='nastools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # GUI程序，无控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='gui/icon.ico', # 自定义图标
)
```

#### 一键打包脚本

```powershell
# build_gui.ps1
$ErrorActionPreference = "Stop"

Write-Host "=== nastools GUI 打包 ===" -ForegroundColor Cyan

# 1. 安装依赖
pip install pyinstaller paramiko pyyaml pygments

# 2. 下载 nastools 源码（如需要）
# git clone https://github.com/leon2397/nastools.git nastools_src

# 3. 复制 nastools 源码到 nastools_pkg/nastools/
# Copy-Item -Recurse ../nastools nastools_pkg/

# 4. 运行 PyInstaller
pyinstaller nastools_pkg.spec --clean --noconfirm

# 5. 打包 ZIP
Compress-Archive -Path dist/nastools.exe -DestinationPath nastools-v6.0.exe.zip -Force

Write-Host "打包完成: dist/nastools.exe" -ForegroundColor Green
Write-Host "SHA256: $(Get-FileHash dist/nastools.exe -Algorithm SHA256 | Select -ExpandProperty Hash)"
```

#### 打包后的使用流程

```
用户操作：
1. 下载 nastools-v6.0.exe.zip
2. 解压
3. 双击 nastools.exe
4. 输入设备 IP / 用户名 / 密码
5. 点击「连接」→ 开始诊断
```

**预计工作量：8h**

---

## 四、P1 任务详解

### 4.1 离线安装包

**目标**：无网络环境也能安装

#### 方案：包含全部依赖的压缩包

| 依赖 | Windows | Linux | macOS |
|------|---------|-------|-------|
| Python | ✅ 内嵌 Python | ✅ 内嵌 Python | ⬜ |
| paramiko | ✅ 预编译 wheel | ✅ 预编译 wheel | ⬜ |
| nastools 源码 | ✅ 包含 | ✅ 包含 | ⬜ |
| 配置文件模板 | ✅ 包含 | ✅ 包含 | ✅ |

#### 离线包结构

```
nastools-v6.0-offline-win64.zip  (~80MB)
├── nastools.exe          # 打包好的可执行文件
├── nastools_pkg/
│   └── nastools/         # 内嵌 nastools 源码
├── config.yaml.example    # 配置模板
├── docs/
│   ├── README.md         # 快速开始
│   └── USER_GUIDE.md     # 用户手册
└── CHANGELOG.md
```

**预计工作量：4h**

### 4.2 日志记录完善（71处债务）

**目标**：每个 `except` 块都有日志记录

修复原则：
```python
# ❌ 之前
except Exception as e:
    pass  # TODO: 添加日志

# ✅ 修复后
except Exception as e:
    logger.warning(f"Failed to check network: {e}")
    return CheckResult(
        id="network_latency",
        status=CheckSeverity.WARNING,
        value=None,
        detail=str(e)
    )
```

按文件批量修复：
```
core/network_health.py    → 10处
core/security_health.py    → 6处
core/ai_accel.py          → 5处
core/device.py            → 5处
core/nas_health.py         → 5处
core/system_health.py     → 5处
core/storage.py           → 4处
core/storage_health.py    → 3处
fixes/system/check_versions.py → 6处
profiles/loader.py         → 6处
adapters/*.py             → 5处
其他                        → 6处
```

**预计工作量：4h**

### 4.3 定时扫描功能

**目标**：自动周期性运行诊断，异常时告警

#### 技术方案

```python
# nastool/scheduler.py
import sched, time, threading
from datetime import datetime, timedelta

class NastoolScheduler:
    """定时扫描调度器"""

    def __init__(self, interval_hours: int = 24):
        self.interval = interval_hours * 3600  # 秒
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.running = False

    def start(self):
        """启动定时扫描"""
        self.running = True
        self._schedule_next()
        threading.Thread(target=self.scheduler.run, daemon=True).start()

    def stop(self):
        """停止定时扫描"""
        self.running = False
        self.scheduler.cancel()

    def _schedule_next(self):
        """调度下一次扫描"""
        self.scheduler.enter(self.interval, 1, self._run_scan, ())

    def _run_scan(self):
        """执行一次扫描"""
        from nastool.arm_diagnose import run_all_checks
        results = run_all_checks(mode='quick')

        # 检查评分
        score = health_scorer.calculate_score(results)

        if score < 60:
            self._send_alert(score, results)

        if self.running:
            self._schedule_next()

    def _send_alert(self, score, results):
        """发送告警"""
        # 支持多渠道
        logger.error(f"健康评分低于60分: {score}/100")
        # TODO: 支持邮件/钉钉/微信推送
```

#### CLI 集成

```bash
# 每天凌晨3点自动扫描
nastools --schedule daily

# 每6小时扫描一次
nastools --schedule interval --interval 6

# 扫描完成后发送报告到邮箱
nastools --schedule daily --notify-email admin@example.com

# Webhook 推送
nastools --schedule daily --webhook https://your-webhook.com/alert
```

**预计工作量：8h**

### 4.4 单元测试体系

**目标**：测试覆盖率 >60%，核心模块 >80%

#### 现有测试（需清理）

| 测试文件 | 问题 |
|----------|------|
| `tests/test_ai_accel.py` | 仅1个测试，存根 |
| `tests/test_checks_ai.py` | 3个测试 |
| `tests/test_checks_nas.py` | 2个测试 |
| `tests/test_checks_security.py` | 4个测试 |
| `tests/test_core.py` | 3个测试 |
| `tests/test_exceptions.py` | 4个测试 |
| `tests/test_fixes_all.py` | 7个测试 |
| `tests/test_functional.py` | 13个测试 |
| `tests/test_health_scorer.py` | 8个测试 |

#### 新增测试

```python
# tests/test_checks_full.py
# 82项检测全部跑一遍（快速模式）
# 使用 Mock 数据，验证每项返回 CheckResult

# tests/test_terminology.py
# 验证术语翻译完整性（82项全覆盖）

# tests/test_health_score.py
# 验证每种情况（通过/警告/失败）评分正确

# tests/test_relay_protocol.py
# Agent ↔ Relay WebSocket 协议测试

# tests/test_gui_unit.py
# GUI 组件单元测试（不含 tkinter 交互）

# tests/test_fix_safety.py
# 修复前备份测试
# 修复后回滚测试
```

#### CI/CD 集成

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e .[test]
      - run: pytest nastools/tests/ -v --cov=nastools --cov-report=xml
      - uses: codecov/codecov-action@v4
```

**预计工作量：16h**

### 4.5 文档完善

**缺口**：
- API 文档（`docs/API.md`）
- 架构文档（`docs/ARCHITECTURE.md`）
- 开发指南（`docs/DEVELOPER_GUIDE.md`）

#### API.md 结构

```markdown
# nastools API 文档

## CLI 接口

### nastools [OPTIONS]

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--mode MODE` | 运行模式 | quick |
| `--output FILE` | 输出文件 | - |
| `--format FORMAT` | 输出格式 | terminal |
| `--nas NAS_TYPE` | NAS 类型 | auto |
| `--mock PROFILE` | 模拟数据 | - |

## Python 接口

### nastool.arm_diagnose

```python
from nastool.arm_diagnose import run_all_checks, run_quick_checks
results = run_all_checks(mode='full')
```

### nastool.config

```python
from nastool.config import Config
config = Config.from_yaml('config.yaml')
```
```

#### ARCHITECTURE.md 结构

```markdown
# nastools 架构文档

## 系统架构

[ASCII 图]

## 模块关系

- arm_diagnose.py → checks/ → fixes/ → reporters/
- nastools_pkg/ → remote.py → nastool/
- relay_server/ → Agent ↔ GUI

## 数据流

1. 用户输入（CLI/GUI/Relay）
2. 配置加载（config.py）
3. 设备适配（adapters/）
4. 检测执行（checks/）
5. 评分计算（health_scorer.py）
6. 结果展示（reporters/）
```

**预计工作量：8h**

---

## 五、P2 任务详解

### 5.1 CI/CD 发布流水线

**目标**：push 到 main 分支自动发布

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install pyinstaller paramiko pyyaml
      - run: pyinstaller nastools_pkg.spec
      - run: Compress-Archive dist/nastools.exe nastools-${{ github.ref_name }}.zip
      - uses: softprops/action-gh-release@v1
        with:
          files: nastools-*.zip
```

### 5.2 多平台支持

| 平台 | GUI | CLI | Relay Agent |
|------|-----|-----|-------------|
| Windows | ✅ PyInstaller | ✅ | ✅ Python |
| Linux | ✅ Tkinter | ✅ | ✅ |
| macOS | ⬜ | ✅ | ⬜ |
| Web | ⬜ | — | ✅ (Relay Server) |

#### macOS GUI 打包

```bash
# build_macos.sh
pyinstaller nastools_pkg.spec --platform macos
```

### 5.3 报告增强

- **邮件报告**：HTML 报告发送邮件
- **PDF 导出**：优化 `report_exporters.py` 生成 PDF
- **对比视图**：两台设备报告并排对比

### 5.4 Relay Server 健壮性

| 问题 | 修复 |
|------|------|
| 数据库路径验证 | 启动时验证路径，不存在则报错 |
| 空 agent_key 表 | 启动时创建默认 key |
| 心跳超时 | 精确的 90s 超时检测 |
| 日志格式统一 | pino JSON 格式，便于监控 |

---

## 六、V6.0 版本规划

### 6.1 功能清单

| # | 功能 | 优先级 | 工时 |
|---|------|--------|------|
| 1 | PyInstaller GUI 打包 | P0 | 8h |
| 2 | 离线安装包 | P1 | 4h |
| 3 | 日志完善（71处）| P1 | 4h |
| 4 | 定时扫描 | P1 | 8h |
| 5 | 单元测试体系 | P1 | 16h |
| 6 | 文档完善 | P1 | 8h |
| 7 | CI/CD 流水线 | P2 | 6h |
| 8 | 多平台支持 | P2 | 4h |
| 9 | 报告增强 | P2 | 6h |
| 10 | Relay 健壮性 | P2 | 4h |
| **合计** | | | **68h** |

### 6.2 里程碑

| 阶段 | 内容 | 预计时间 |
|------|------|----------|
| **v5.3** | GUI PyInstaller 打包 | 2天 |
| **v5.4** | 离线安装包 + 日志完善 | 2天 |
| **v5.5** | 定时扫描 + Relay健壮性 | 2天 |
| **v5.6** | 单元测试体系 | 3天 |
| **v5.7** | 文档完善 + CI/CD | 2天 |
| **v6.0.0** | 发布 | 1天 |
| **总计** | | **~12天** |

### 6.3 验收标准

| 验收项 | 标准 |
|--------|------|
| GUI 打包 | 双击 nastools.exe 正常运行 ✅ |
| 离线安装 | 无网络环境解压即用 ✅ |
| 测试覆盖 | pytest 覆盖率 >60% ✅ |
| CI/CD | main 分支 push 自动构建 ✅ |

---

## 七、技术债务清理清单

### 7.1 立即处理（V5.3）

| # | 债务 | 文件 | 数量 |
|---|------|------|------|
| 1 | 日志缺失 | 多个 core/*.py | 71处 |

### 7.2 下一步处理（V5.4-V5.8）

| # | 债务 | 优先级 |
|---|------|--------|
| 4 | docstring 缺失 | P2 |
| 5 | GUI 测试缺失 | P2 |
| 6 | API 文档缺失 | P1 |
| 7 | 架构文档缺失 | P1 |
| 8 | Relay 路径验证 | P1 |

---

## 八、附录

### 8.1 V6.0 目录结构

```
D:\armtool415\
├── nastools/                 # 诊断引擎
│   ├── checks/              # 82项检测
│   │   ├── system/
│   │   ├── network/
│   │   ├── storage/
│   │   ├── ai/
│   │   ├── security/
│   │   ├── nas/
│   │   └── usb/
│   ├── fixes/               # 修复模块
│   ├── adapters/            # 设备适配器
│   ├── utils/
│   │   ├── terminology.py   # V6.0: 82项全覆盖
│   │   └── health_scorer.py # V6.0: 82项全覆盖
│   ├── scheduler.py         # V6.0: 定时扫描
│   └── arm_diagnose.py
│
├── nastools_pkg/             # Windows GUI（V6.0: PyInstaller）
│   ├── gui/
│   │   ├── app.py
│   │   └── *.py             # 7个对话框
│   ├── core/
│   ├── integration/
│   ├── scripts/
│   ├── utils/
│   ├── main.py
│   └── nastools_pkg.spec    # V6.0: PyInstaller 配置
│
├── relay_server/             # 中继服务器
│   ├── src/                  # V6.0: 健壮性改进
│   ├── agent/                # ARM Agent
│   └── web_dashboard/        # V6.0: 完成
│
├── docs/
│   ├── API.md               # V6.0: 新增
│   ├── ARCHITECTURE.md      # V6.0: 新增
│   ├── DEVELOPER_GUIDE.md   # V6.0: 新增
│   └── UPGRADE_v6.0.md
│
├── .github/
│   └── workflows/
│       ├── test.yml         # V6.0: 新增
│       └── release.yml      # V6.0: 新增
│
└── tests/                    # V6.0: 扩展到 20+
    ├── test_checks_full.py  # V6.0: 新增
    ├── test_terminology.py  # V6.0: 新增
    ├── test_health_score.py # V6.0: 新增
    ├── test_relay_protocol.py  # V6.0: 新增
    └── conftest.py          # 已存在
```

### 8.2 版本号对应

| 组件 | V5.0.x | V6.0 |
|------|---------|------|
| nastool | 5.0.2 | 6.0.0 |
| nastools_pkg | 1.2 | 2.0.0 |
| relay_server | 2.0.0 | 3.0.0 |
| ARM Agent | 2.0.0 | 3.0.0 |
| Web Dashboard | — | 1.0.0 |

> **注意**：V6.0 统一套件版本号为 **6.0.0**
