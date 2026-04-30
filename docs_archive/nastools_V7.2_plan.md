# nastools V7.2 升级计划

> 版本日期：2026-04-29  
> 当前版本：v7.1.0-beta  
> 目标版本：v7.2.0  
> 主题：**收尾完成 — 完善所有未完成项**

---

## 一、未完成项汇总

### 1.1 待完成功能清单

| 优先级 | 功能项 | 所属版本 | 当前状态 | 说明 |
|--------|--------|----------|----------|------|
| **P0** | BUG-001 `--quick` 显示 `Passed: 0/0` | V7.1 | ❌ 未修复 | 核心功能缺陷 |
| **P0** | BUG-007 HTML报告未生成 | V7.1 | ❌ 未修复 | 报告功能缺陷 |
| **P1** | CI/CD 流水线 | V6.0 | ❌ 未开始 | GitHub Actions 自动测试+发布 |
| **P1** | 通用测试运行器 | V7.1 | ❌ 未开始 | 动态探测，不依赖模块名 |
| **P1** | 设备覆盖扩展（目标50+） | V5.0 | ⚠️ 进行中（12+） | 当前12个适配器 |
| **P2** | 日志完善（71处→19处） | V6.0 | ⚠️ 进行中 | 还需修复52处 |
| **P2** | API/架构文档 | V6.0 | ❌ 未开始 | 完善技术文档 |
| **P2** | Jetson 设备测试集 | V7.1 | ❌ 未开始 | JSON数据驱动测试 |
| **P2** | `--version` 输出增强 | V7.1 | ❌ 未开始 | 显示git hash/check count |
| **P2** | BUG分类标准化 | V7.1 | ❌ 未开始 | T-A/T-B/T-C/T-D分类 |

### 1.2 BUG 修复优先级

| BUG ID | 问题 | 分类 | 影响 |
|--------|------|------|------|
| BUG-001 | `--quick` 显示 `Passed: 0/0` | T-A | 用户看不到检测结果 |
| BUG-007 | HTML报告未生成 | T-A | 无法导出报告 |

---

## 二、V7.2 核心目标

```
"让 nastools 真正完整可用"
- 修复核心BUG，确保基本功能正常
- 建立测试体系，确保质量可追溯
- 完善文档，便于维护和扩展
- 扩展设备覆盖，支持更多ARM设备
```

---

## 三、功能规划

### P0 核心：BUG 修复

#### F1：修复 `--quick` 统计显示问题（BUG-001）

**问题**：`--quick` 输出 `Passed: 0/0`，实际运行了6个检查

**修复步骤**：
1. 读取 `utils/quick_diagnose.py` 的 `print_quick_report()` 函数
2. 读取 `checks/__init__.py` 的 `CheckSummary` 类定义
3. 确认 `passed/total` 统计字段来源
4. 写单元测试覆盖（`test_quick_diagnose.py`）
5. 修复后本地跑 `--quick` 验证

**改动范围**：
- `nastool-core/nastool_core/utils/quick_diagnose.py`
- `nastool-core/tests/test_quick_diagnose.py`（新增）

**工时**：2-3h

#### F2：修复 HTML 报告生成问题（BUG-007）

**问题**：`--quick --output /tmp/test.html --format html` 文件未生成

**修复步骤**：
1. 读取 `arm_diagnose.py` 中 `--output` 和 `--format` 参数处理逻辑
2. 读取 `reporters/file_reporter.py` 的 HTML 生成逻辑
3. 本地测试验证
4. 修复后本地+真机验证

**改动范围**：
- `nastool-core/nastool_core/reporters/file_reporter.py`
- `nastool-cli/nastool_cli/main.py`

**工时**：1-2h

---

### P1 核心：测试体系完善

#### F3：CI/CD 流水线

**目标**：GitHub Actions 自动测试 + 发布

**改动范围**：
- `.github/workflows/test.yml`（新增）
- `.github/workflows/release.yml`（新增）
- `pyproject.toml` 添加 test 依赖

**工时**：4-6h

#### F4：通用测试运行器

**目标**：动态探测，不依赖模块名

**改动范围**：
- `nastool-core/nastool_core/tests/test_runner.py`（新增）
- `nastool-core/tests/test_functional.py`（重写）

**工时**：4-6h

---

### P2 扩展：设备覆盖与文档

#### F5：设备覆盖扩展

**目标**：从12+扩展到30+设备适配器

**新增设备**：
| 品牌 | 新增数量 | 优先级 |
|------|----------|--------|
| 华硕 Asustor | 4 | P2 |
| 铁威马 TerraMaster | 4 | P2 |
| WD My Cloud | 2 | P3 |
| OrangePi | 3 | P3 |
| 其他 ARM SBC | 5 | P3 |

**工时**：8-12h

#### F6：日志完善

**目标**：完成剩余52处日志缺失修复

**工时**：4h

#### F7：API/架构文档

**目标**：完善技术文档

**文档结构**：
- `docs/API.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPER_GUIDE.md`

**工时**：6-8h

#### F8：Jetson 设备测试集

**目标**：JSON数据驱动测试

**工时**：3-4h

#### F9：`--version` 输出增强

**目标**：显示 git hash + check count

**工时**：2h

#### F10：BUG 分类标准化

**目标**：统一 BUG 分类体系（T-A/T-B/T-C/T-D）

**工时**：2h

---

## 四、执行顺序与依赖关系

```
Week 1（Day 1-2）：
├── F1 修复 --quick 统计显示（BUG-001）
└── F2 修复 HTML 报告生成（BUG-007）
    │
    ▼
Week 1（Day 3-4）：
├── F9 --version 输出增强
└── F10 BUG分类标准化
    │
    ▼
Week 2（Day 5-7）：
└── F3 CI/CD 流水线
    │
    ├──► F4 通用测试运行器
    │
    └──► F8 Jetson 设备测试集
        │
        ▼
Week 3-4：
├── F5 设备覆盖扩展
├── F6 日志完善
└── F7 API/架构文档
```

**总计工时**：约 35-45h

---

## 五、验收标准

| 验收项 | 标准 | 对应功能 |
|--------|------|----------|
| `--quick` 输出 | 正确显示检查统计 | F1 |
| HTML报告 | 成功生成文件 | F2 |
| CI/CD | main分支push自动测试 | F3 |
| 测试运行器 | 通过registry动态运行检查 | F4 |
| 设备覆盖 | ≥30个适配器 | F5 |
| 日志完善 | 71处全部修复 | F6 |
| 文档 | API/ARCHITECTURE/DEVELOPER_GUIDE 齐全 | F7 |
| Jetson测试集 | JSON数据驱动测试通过 | F8 |
| `--version` | 显示git hash/check count | F9 |
| BUG分类 | TEST_BUGS模板更新 | F10 |

---

## 六、风险与备选方案

| 风险 | 影响 | 备选方案 |
|------|------|----------|
| CI/CD 配置复杂 | P1功能延迟 | 先实现测试流水线，发布流水线延后 |
| 设备覆盖扩展工作量大 | P2功能延迟 | 优先完成主流品牌（华硕/铁威马） |
| 日志修复遗漏 | 技术债务累积 | 按模块分批修复，每批验证 |

---

## 七、交付物清单

| 交付物 | 对应功能 |
|--------|----------|
| `--quick` 正确显示检查统计 | F1 |
| `--format html` 正确生成报告 | F2 |
| `.github/workflows/test.yml` | F3 |
| `.github/workflows/release.yml` | F3 |
| `test_runner.py` | F4 |
| 新增设备适配器（华硕/铁威马等） | F5 |
| 日志完善（71处） | F6 |
| `docs/API.md` | F7 |
| `docs/ARCHITECTURE.md` | F7 |
| `docs/DEVELOPER_GUIDE.md` | F7 |
| `tests/devices/expected_results/*.json` | F8 |
| `--version` 输出增强 | F9 |
| BUG分类模板更新 | F10 |
| 更新 CHANGELOG.md | 发布准备 |

---

**总结**：V7.2 版本聚焦于**修复核心BUG**和**完善测试体系**，确保 nastools 真正完整可用。通过建立 CI/CD 流水线和通用测试运行器，为后续版本迭代奠定坚实基础。

---

*文档更新：2026-04-29*
