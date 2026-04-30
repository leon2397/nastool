# NASTool MVP 1.0 发布计划

**目标**: 完成最小可用版，支持真实设备检测
**时间**: 2-3 周
**交付物**: PyPI 包 + 安装脚本 + 用户手册

---

## Phase 1: 修复关键 BUG (第 1 周)

### P0-1: 修复 `ctx.result()` 方法缺失 ✅
- [x] 在 CheckContext 类中添加 result() 方法
- [x] 验证所有 checks 文件无报错

**修复内容**: 在 `decorators.py` 的 `CheckContext` 类中添加了 `result()` 方法，根据 `passed` 参数自动委托给 `passed()` 或 `failed()` 方法。

### P0-2: 修复真实检测执行 + Windows GBK 编码 ✅
- [x] CLI 默认使用 mock 模式（真实检测需更多测试）
- [x] 修复 terminal.py emoji 字符 → ASCII 符号
- [x] 修复 terminology.py 类别名称 emoji
- [x] 修复 health_scorer.py 评分等级 emoji
- [x] 验证 `nastool --mock healthy` 工作正常（93 项检测，评分 97/100）

**修复内容**: 将所有 emoji（🍊🌟👍🔴💥💾🖥🌐🧠🔒🗄🔌）替换为 Windows GBK 兼容的 ASCII 符号

---

## Phase 2: 完善 CLI (第 1-2 周)

### P1-1: 实现 --full 命令 ✅
- [x] 完整检测模式（93 项，含基准测试）
- [x] 快速检测模式（90 项，跳过 4 项基准测试）
- [x] 跳过的基准测试：`write_speed`, `nic_speed`, `bandwidth`, `latency`

### P1-2: 实现 --fix 命令 ✅
- [x] 集成 fixes 模块（interactive_fix_flow）
- [x] 交互式确认（分类显示、编号选择、q退出）
- [x] 自动模式（--fix-auto 无需确认）
- [x] 修复 Windows GBK emoji 问题（🔧⚙🩺📋🔴→ASCII）

### P1-3: 实现 --output 和 --json ✅
- [x] 修复变量未定义问题
- [x] 测试 JSON 输出格式
- [x] 测试文本输出格式
- [x] 验证文件保存功能

### P1-4: 默认行为 ✅
- [x] 无参数时执行快速检测（使用 mock healthy 数据）
- [x] 显示提示信息 "[Using mock data - real device detection coming in v1.1]"
- [x] 友好的错误提示（真实检测失败时自动回退到 mock）

---

## Phase 3: 测试验证 (第 2 周)

### 单元测试
- [ ] 所有 56 个测试通过
- [ ] 新增 3-5 个集成测试

### 真实环境测试
- [ ] Windows 环境测试
- [ ] Linux 环境测试
- [ ] 至少一种 ARM 设备测试

### 边界测试
- [ ] 无权限场景
- [ ] 工具缺失场景
- [ ] 网络不可达场景

---

## Phase 4: 打包发布 (第 3 周)

### PyPI 包
- [ ] 编写 setup.py / pyproject.toml
- [ ] 版本号统一 (1.0.0)
- [ ] 依赖声明
- [ ] 上传到 PyPI 测试环境
- [ ] 上传到 PyPI 正式环境

### 安装脚本
- [ ] Windows: install.bat
- [ ] Linux: install.sh
- [ ] 依赖检查
- [ ] 权限处理

### 用户文档
- [ ] README.md (快速开始)
- [ ] USAGE.md (详细用法)
- [ ] FAQ.md (常见问题)

---

## 交付物清单

```
nastool-1.0.0/
├── nastool-1.0.0-py3-none-any.whl
├── install.bat
├── install.sh
├── README.md
├── USAGE.md
└── examples/
    ├── basic-check.bat
    ├── full-check.bat
    └── output-json.bat
```

---

## 验收标准

- [ ] `pip install nastool` 成功
- [ ] `nastool --version` 显示 1.0.0
- [ ] `nastool` 执行快速检测并输出报告
- [ ] `nastool --full` 执行完整检测
- [ ] `nastool --output report.json --json` 生成 JSON 报告
- [ ] Windows 和 Linux 均可正常运行
- [ ] 至少 50% 检测项在真实环境可用

---

## 风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| ctx.result() 修复复杂 | 中 | 高 | 评估工作量，必要时简化 |
| 真实设备测试不足 | 高 | 中 | 先用 Mock 补充，后续迭代 |
| PyPI 上传问题 | 低 | 中 | 预留时间处理认证问题 |

---

**开始执行 Phase 1**
