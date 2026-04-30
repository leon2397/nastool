# NASTool 项目备忘录

> 最后更新：2026-04-29 20:00
> 维护人：桔子2（AI 助手）
> 当前版本：v7.1.0-beta

---

## ⚠️ 项目定位（最重要，先读这里）

**nastools 双重属性，缺一不可：**

```
使命 1 — 工具属性（核心）
  → 免费、傻瓜、覆盖广的 ARM NAS 诊断工具
  → 打开工具就能知道 NAS 健不健康，不收费、不做平台

使命 2 — 部署属性（初心）
  → 帮助把 ARM NAS 管理系统一键部署到设备上
  → 检测是手段，部署是目的
```

| ✅ nastools 是 | ❌ nastools 不是 |
|---------------|----------------|
| Windows 上双击即用的工具 | Web 控制台 / SaaS / 企业级平台 |
| 免费，不收费 | 需要技术背景的命令行工具 |
| 检测 + 部署一体化 | 纯检测工具（不部署）|
| 覆盖群晖/威联通/RK3588/Jetson/昇腾等 | 只支持某一品牌 |
| 傻瓜界面，普通用户能用 | 企业级管理平台 |
| 轻量，单进程 < 70MB | — |

---

## 📌 当前版本

**v7.1.0-beta**（2026-04-29，专业诊断版本）

### 核心功能矩阵

| 阶段 | 版本 | 核心功能 | 状态 |
|------|------|----------|------|
| 第一阶段 | v4.2 | 设备管理系统、统一工具目录 | ✅ 完成 |
| 第二阶段 | v4.3 | 智能测试引擎、一键部署、报告管理 | ✅ 完成 |
| 第三阶段 | v4.4 | 交互式CLI、配置向导、友好错误处理 | ✅ 完成 |
| 第四阶段 | v4.5 | 检测器统一整合（92个检测器全部接入） | ✅ 完成 |
| 第五阶段 | v5.0 | 检测结果优化、Mock数据支持、健康评分 | ✅ 完成 |
| 第六阶段 | v6.0 | GUI产品化、离线安装包、定时扫描 | ✅ 完成 |
| 第七阶段 | v7.0 | PDF报告、修复引擎v2、版本检查机制 | ✅ 完成 |
| 第八阶段 | v7.2 | 收尾完善（BUG修复、CI/CD、设备扩展） | ⏳ 进行中 |

### 核心工具模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 设备管理 | `tools/device_manager.py` | 设备注册表、状态检查、局域网扫描 |
| 智能测试引擎 | `tools/test_engine.py` | 多模式测试、并行测试、自动报告 |
| 一键部署 | `tools/deploy/deploy_manager.py` | 单设备/批量部署、环境检查、卸载 |
| 报告管理 | `tools/report_manager.py` | SQLite存储、查询、对比、导出 |
| 性能监控 | `tools/performance_monitor.py` | CPU/内存/磁盘/网络实时监控 |
| 健康检查 | `tools/health_checker.py` | 系统健康诊断、阈值告警 |
| 对比分析 | `tools/comparison_analyzer.py` | 多报告对比、趋势分析 |
| 配置向导 | `tools/setup_wizard.py` | 首次配置引导、系统参数设置 |
| 统一检测器执行引擎 | `tools/unified_checker_executor.py` | 92个检测器统一调度 |
| 全面验证工具 | `tools/comprehensive_validate.py` | 文件完整性、语法、依赖检查 |

---

## 📅 版本演进

```
v1.0.0   2026-04-12   初始版本，基础检测+部署
v2.0.0   2026-04-12   多设备管理基础，远程中继
v3.0.0   2026-04-13   Relay Server + ARM Agent + Web Dashboard + USB Gadget
v4.0.0   2026-04-14   目录结构重构(25→12) / 代码重复清理(裸except 35→0)
v4.0.1   2026-04-14   代码质量 / docstring 补充
v4.0.2   2026-04-14   工具属性强化：35项检测 / 14个适配器 / 15种修复 / 评分系统
v4.1.0   2026-04-14   ARM Agent 部署能力强化
v4.2.0   2026-04-14   Relay v2.0 + WebSocket双通道 + 跨网远程管理
v4.3.0   2026-04-28   智能测试引擎 + 一键部署 + 报告管理
v4.4.0   2026-04-28   交互式CLI + 性能监控 + 健康检查 + 对比分析
v4.5.0   2026-04-29   **重大整合**: 92个检测器全部接入核心引擎
v5.0.0   2026-04-29   检测结果优化、Mock数据、健康评分系统
v6.0.0   2026-04-29   GUI产品化、离线安装包、定时扫描
v7.0.0   2026-04-29   PDF报告导出、修复引擎v2、版本检查机制
v7.1.0   2026-04-29   版本更新提示、离线超时自动跳过
v7.2.0   2026-05-XX   **收尾完成**: BUG修复、CI/CD、设备扩展至30+
```

---

## 📁 项目结构

```
D:\project\nastool7\
├── 📁 tools/                    # 核心工具目录（新增）
│   ├── device_manager.py        # 设备管理系统
│   ├── test_engine.py           # 智能测试引擎
│   ├── report_manager.py        # 报告管理系统
│   ├── performance_monitor.py   # 性能监控模块
│   ├── health_checker.py        # 健康检查模块
│   ├── comparison_analyzer.py   # 对比分析模块
│   ├── setup_wizard.py          # 配置向导
│   └── deploy/deploy_manager.py # 一键部署系统
├── 📁 diagnostics/              # 诊断测试脚本
├── 📁 network/                  # 网络工具
├── 📁 remote/                   # 远程测试工具
├── 📁 debug/                    # 调试工具
├── 📁 nastool-core/             # 核心检测模块（93项检测）
├── 📁 nastool-adapters/         # 设备适配器（SSH/USB/HTTP/昇腾/Jetson等）
├── 📁 nastool-common/           # 公共工具（logging/exception/config）
├── � nastool-cli/              # CLI入口
├── 📁 nastool-agent/            # ARM端Agent
├── 📁 config/                   # 配置文件（设备注册表）
├── 📁 data/                     # 数据存储（报告数据库）
├── 📁 docs/                     # 文档
├── 📁 archive/                  # 历史版本归档
└── 📝 nastool.py                # 主入口（交互式CLI）
```

---

## 🚀 快速命令

```bash
# 启动交互式主界面
python nastool.py

# 快速诊断（本地）
python tools/test_engine.py test local -m quick

# 完整诊断
python tools/test_engine.py test local -m full

# 网络专项诊断
python tools/test_engine.py test local -m network

# 批量测试
python tools/test_engine.py batch dev-001 dev-002 -m quick

# 性能监控（10秒）
python tools/performance_monitor.py start -d 10

# 健康检查
python tools/health_checker.py

# 查看设备列表
python tools/device_manager.py list

# 添加设备
python tools/device_manager.py add "设备名称" "192.168.1.xxx" -u root -pw password

# 查看报告列表
python tools/report_manager.py list

# 配置向导
python tools/setup_wizard.py

# 查看当前配置
python tools/setup_wizard.py --show

# ============ 检测器注册表（v4.5新增）============
# 查看所有检测器
python tools/checker_registry.py

# 执行指定类别检测
python tools/check_executor.py

# 执行系统检测
python -c "from tools.check_executor import CheckExecutor; e=CheckExecutor(); e.execute_category('system')"

# ============ 适配器注册表（v4.5新增）============
# 查看所有适配器
python tools/adapter_registry.py

# 执行适配器检测
python tools/adapter_executor.py
```

---

## 📊 当前功能状态（v7.1.0-beta）

```
设备管理系统      ✅ 完成（设备注册表、状态检查、局域网扫描）
智能测试引擎      ✅ 完成（多模式、并行测试、自动报告）
一键部署系统      ✅ 完成（单设备/批量、环境检查、卸载）
报告管理系统      ✅ 完成（SQLite存储、查询、对比、导出）
交互式CLI        ✅ 完成（菜单式界面、配置向导、友好错误）
性能监控          ✅ 完成（CPU/内存/磁盘/网络实时监控）
健康检查          ✅ 完成（系统健康诊断、阈值告警）
测试对比分析      ✅ 完成（多报告对比、趋势分析、智能建议）
统一检测器引擎    ✅ 完成（92个检测器统一调度，可用率100%）
数据融合引擎      ✅ 完成（异常值检测、置信度计算、一致性验证）
PDF报告导出      ✅ 完成（封面、评分、分类详情、建议）
修复引擎v2       ✅ 完成（快照、dry-run、结构化结果）
版本检查机制      ✅ 完成（首次运行提示、版本更新提示、离线跳过）
```

---

## 🚩 V7.2 升级计划

**目标**：收尾完成，完善所有未完成项

| 优先级 | 任务 | 状态 | 说明 |
|--------|------|------|------|
| P0 | 修复 BUG-001（`--quick` 统计显示） | ⏳ | 核心功能缺陷 |
| P0 | 修复 BUG-007（HTML报告未生成） | ⏳ | 报告功能缺陷 |
| P1 | CI/CD 流水线（GitHub Actions） | ❌ | 自动测试+发布 |
| P1 | 通用测试运行器 | ❌ | 动态探测，不依赖模块名 |
| P1 | 设备覆盖扩展（12+→30+） | ⏳ | 华硕/铁威马/WD等 |
| P2 | 日志完善（剩余52处） | ⏳ | 完善错误日志 |
| P2 | API/架构文档 | ❌ | 完善技术文档 |
| P2 | Jetson 设备测试集 | ❌ | JSON数据驱动测试 |
| P2 | `--version` 输出增强 | ❌ | 显示git hash/check count |
| P2 | BUG分类标准化 | ❌ | T-A/T-B/T-C/T-D分类 |

**计划文件**：`docs_archive/nastools_V7.2_plan.md`

---

## � 测试模式说明

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| `quick` | 快速模式，只运行核心检测项 | 快速获取系统状态 |
| `full` | 完整模式，运行所有检测项 | 全面系统诊断 |
| `network` | 网络专项，专注网络诊断 | 网络问题排查 |
| `hardware` | 硬件专项，专注硬件诊断 | 硬件问题排查 |

---

## 🛡️ 安全架构

> 最高准则：**零破坏、零篡改、所有操作可撤销**

### 禁止清单 FORBIDDEN_FIXES

代码级硬编码屏蔽，不可绕过：

| 类别 | fix_id | 原因 |
|------|--------|------|
| 网络配置 | config_dns, config_network, config_firewall | 可能导致设备断连 |
| 用户管理 | disable_root_login, create_user, delete_user | 可能锁死管理员 |
| CUDA/驱动 | install_cuda, install_gpu_driver | 风险极高 |
| 破坏性 | format_disk, wipe_data, factory_reset | 数据永久丢失 |

### 风险等级定义

| 等级 | 说明 | 允许自动执行 |
|------|------|-------------|
| `low` | 无系统破坏风险（清理临时文件） | ✅ |
| `medium` | 有限风险（清理 Docker 镜像） | ❌ 需确认 |
| `high` | 显著风险（修改配置、安装软件包） | ❌ 需确认+备份 |
| `danger` | 破坏性操作（磁盘、网络、驱动） | ❌ 且禁止清单屏蔽 |

---

## 🔐 安全注意

- **AGENT_KEY / RELAY_HOST**：必须从 `os.environ.get()` 读取
- **禁止提交硬编码凭证**：一律使用环境变量
- 运行 E2E 测试：`AGENT_KEY=xxx RELAY_HOST=120.77.249.3 python e2e_test.py`

---

## 📖 文档索引

| 文件 | 位置 | 说明 |
|------|------|------|
| IMPROVEMENT_PLAN.md | docs/ | 改进建议和升级计划 |
| TEST_BUGS.md | docs/ | BUG记录 |
| FILE_STRUCTURE_V4.2.md | / | 文件结构分析 |
| PROJECT_STATUS_V4.2.md | / | 项目状态报告 |
| docs_archive/ | docs_archive/ | 历史文档归档 |

---

## � 已知限制

| 项目 | 说明 |
|------|------|
| 配置系统统一 | 未完全实现统一配置中心 |
| RK3588 NPU检测 | NPU/RKNN/驱动检测待完善 |
| USB即插即用 | 未实现 |
| PyPI发布 | 未完成 |
| 插件系统 | 未实现 |

---

*MEMO.md 由桔子2维护，如有出入请以最新源码为准。*
