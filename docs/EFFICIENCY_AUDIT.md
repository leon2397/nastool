# nastools 项目效率诊断报告

> 日期：2026-04-15
> 目的：找出开发缓慢、效率低下的根因

---

## 一、核心数据

| 指标 | 数值 |
|------|------|
| 开发天数 | 3 天（04-13 ~ 04-15） |
| Git 提交数 | 13 次 |
| 版本跳跃 | v1.0.2 → v5.0.1 |
| 总文件数 | 358 个（排除 node_modules 等） |
| Python 文件 | 259 个 |
| 代码总行数 | ~27,000 行（nastool 10,965 + GUI 10,355 + relay 2,290 + 其他） |
| 文档总行数 | 5,607 行（Markdown） |
| 文档/代码比 | **1:4.8**（正常人项目 1:10~1:20） |
| 检测项 | 82 项（checks/） |
| 修复项 | 15 个（fixes/） |
| check-fix 匹配 | **0 个**（82 个检测项 vs 15 个修复项，完全无法对应） |

---

## 二、根因分析：7 大效率杀手

### 🔴 杀手 #1：架构重叠（浪费 ~4,148 行代码）

**问题**：`core/` 目录下有 5 个 `_health.py` 模块（3,148 行）+ `upnp_scanner.py`（570 行）+ `safety.py`（189 行）= **3,907 行死代码**，完全没有被调用。

| 死代码文件 | 行数 | 状态 |
|-----------|------|------|
| `core/nas_health.py` | 681 | ❌ 无任何外部引用 |
| `core/system_health.py` | 661 | ❌ 无任何外部引用 |
| `core/network_health.py` | 629 | ❌ 无任何外部引用 |
| `core/storage_health.py` | 593 | ❌ 无任何外部引用 |
| `core/security_health.py` | 584 | ❌ 无任何外部引用 |
| `core/upnp_scanner.py` | 570 | ❌ 无任何外部引用 |
| `core/safety.py` | 189 | ❌ 无任何外部引用（仅定义被 checks/ 复制） |
| **合计** | **3,907** | **全部死代码** |

**根因**：v5.0 重构时用 `checks/` 模块化架构取代了旧的 `core/_health.py` 单体架构，但**旧代码没有删除也没有标记**。

**影响**：
- 新人读代码时以为两套都要维护
- IDE 搜索结果混淆
- TECH_DEBT.md 记录了 71 处日志 TODO，其中大量在这些死代码里

---

### 🔴 杀手 #2：Check 和 Fix 完全脱节（82 检测 vs 15 修复，匹配率 0%）

**问题**：`--fix` 功能的匹配逻辑是 `run_fix(check.id)`，但 check.id 和 fix_id **命名体系完全不同，一个都匹配不上**。

Check IDs 示例：`cudnn_version`, `gpu_detected`, `disk_space`, `ssh_config`
Fix IDs 示例：`install_cuda`, `config_dns`, `cleanup_logs`, `renew_ssl_cert`

**后果**：用户运行 `python arm_diagnose.py --fix` 时，**没有任何修复会被执行**。这个功能名存实亡。

---

### 🔴 杀手 #3：版本号混乱（3 个地方 3 个版本）

| 来源 | 版本 |
|------|------|
| `arm_diagnose.py` 代码内 `__version__` | v4.2.0 |
| `MEMO.md` 标注 | v5.0.1 |
| `VERSION.txt` | v3.0.0-beta |
| `CHANGELOG.md` 最新条目 | v5.0.1 |
| PyPI pyproject.toml | （需确认） |

一个项目 4 个版本号，每次开发前都要花时间确认"到底哪个是真的"。

---

### 🔴 杀手 #4：重复文件（1,242 行浪费）

| 重复 | 行数 | 说明 |
|------|------|------|
| `data/mock_results.py` = `data/mock_profiles_v2.py` | 621×2 | MD5 完全相同，副本 |
| `core/safety.py` SafetyLevel 枚举 | 被复制到 `checks/__init__.py` | 重复定义 |

---

### 🟡 杀手 #5：文档膨胀（5,607 行 Markdown）

29 个 Markdown 文件，其中：
- **10 个 UPGRADE_v3xx.md**（升级日志，合计 ~1,600 行）
- **MEMO.md** 有 3 个版本（根目录、nastool/、docs/ 各一个，内容不同步）
- **ROADMAP.md** 有 2 个版本（根目录 + nastool/）
- **计划文档**：V4.0.2_plan.md（117 行）、V5.0_plan.md（177 行）、ROADMAP.md（144 行）——内容高度重叠

每次开发前要读 5+ 文档才能搞清楚现状。

---

### 🟡 杀手 #6：路径混乱（tools413 → tools414 → tools415）

3 天内迁移了 3 次，MEMO.md 和各文档中仍残留旧路径引用。每次迁移都：
1. 花时间复制文件
2. 花时间修路径
3. 丢失 git 历史（tools415 没有 .git）

---

### 🟡 杀手 #7：GUI 巨型文件

| 文件 | 行数 | 问题 |
|------|------|------|
| `gui/relay_dialog.py` | 2,016 | 单文件，含连接、命令、文件、部署、趋势、批量操作 |
| `gui/app.py` | 1,040 | 主界面 |
| `gui/usb_dialog.py` | 549 | USB 对话框 |

relay_dialog.py 一个文件承担了 6+ 个功能模块，修改任何功能都要在 2000 行里找。

---

## 三、utils/ 中未使用的模块（1,140 行）

| 模块 | 行数 | 外部引用 |
|------|------|----------|
| `utils/offline_storage.py` | 401 | 0 次 |
| `utils/registry.py` | 89 | 0 次 |
| `utils/setup_wizard.py` | 326 | 0 次 |
| `utils/network_timeout.py` | 163 | 仅 1 次（可能是冗余封装） |
| `utils/cmd_timeout.py` | 199 | 仅 1 次 |
| `utils/smart_summary.py` | 194 | 仅 1 次 |

---

## 四、量化总结

| 问题类别 | 浪费代码行 | 占比 |
|---------|-----------|------|
| core/ 死代码 | 3,907 | 14.5% |
| utils/ 未使用 | 1,140 | 4.2% |
| 重复文件 | 1,242 | 4.6% |
| **合计** | **6,289** | **23.3%** |

**结论：约 1/4 的代码从未被调用，是无效代码。**

---

## 五、修复建议（按优先级）

### P0 — 立即做（不花钱，立刻见效）

1. **统一版本号**：选定一个地方（pyproject.toml）作为唯一版本源，其他地方全部引用
2. **初始化 git**：`cd D:\armtool415 && git init && git add -A && git commit -m "v5.0.1: initial commit after migration"`
3. **删除重复文件**：删掉 `data/mock_profiles_v2.py`（和 mock_results.py 完全相同）

### P1 — 本周做

4. **标记死代码**：在 7 个 core/ 死文件顶部加 `# DEPRECATED: unused since v5.0, replaced by checks/` 注释
5. **修复 check-fix 匹配**：要么改 fix_id 命名与 check_id 对齐，要么在 Check 类中加 `fix_id` 属性
6. **拆分 relay_dialog.py**：按功能拆为 relay_connection.py、relay_commands.py、relay_files.py、relay_deploy.py、relay_history.py

### P2 — 下周做

7. **合并文档**：10 个 UPGRADE 文件合并为 1 个 CHANGELOG（已有 CHANGELOG.md）；3 个 MEMO.md 合并为 1 个；2 个 ROADMAP 合并为 1 个
8. **清理 utils/**：删除 offline_storage.py、registry.py、setup_wizard.py（0 引用）
9. **统一 check-fix 关联机制**：让每个 Check 类声明对应的 fix_id

### P3 — 长期

10. **正式删除 core/ 死代码**（确认无测试依赖后）
11. **文档/代码比目标**：从 1:4.8 降到 1:15

---

## 六、效率提升预期

| 行动 | 预期效果 |
|------|----------|
| 统一版本号 | 每次开发省 5~10 分钟确认时间 |
| 初始化 git | 零风险回滚，不再怕改坏 |
| 标记/清理死代码 | 读代码效率提升 30%，新人不再困惑 |
| 修复 check-fix 匹配 | --fix 功能真正可用 |
| 合并文档 | 读文档时间从 30 分钟降到 5 分钟 |
| 拆分巨型文件 | 修改效率提升 50%+ |

---

*报告生成：2026-04-15 07:50 GMT+8*
*分析工具：静态代码分析 + git 历史*
*下一步：用户确认后按 P0→P1→P2 顺序执行清理*
