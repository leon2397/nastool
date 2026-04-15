# nastool v3.0.4 升级计划

> 🍓 实用性优先 - 修复已知问题，提升用户体验

## 版本定位

**原则**：零新功能，修复 Bug + 提升实用性

**目标**：让工具更好用、更稳定、更易上手

---

## 当前问题诊断（v3.0.3）

| 问题 | 严重程度 | 影响 |
|------|----------|------|
| ❌ arm_diagnose.py 有 2 个 `__version__` | 高 | 版本号混乱 |
| ⚠️ config.py 有默认值但检查脚本误报 | 中 | 无实际影响 |
| ⚠️ requirements.txt 缺少 requests/uvicorn | 高 | pip install 后无法运行 |
| ⚠️ 89 处 print() 语句（非报告器） | 中 | 日志混杂 |
| ⚠️ 硬编码 NAS IP (120.77.249.3) 在参数默认值 | 低 | 已在 config.py，可优化 |
| ⚠️ CLI 参数 `--nas-host` 默认值硬编码 | 低 | 应引用 Config |

---

## P0 任务（必须完成）- 2 小时

### 1. 修复重复版本号定义

**问题**：`arm_diagnose.py` 第 32 行和第 37 行都有 `__version__`

**文件**：`arm_diagnose.py`

**修复**：
```python
# 删除第 37 行的重复定义
# __version__ = "3.0.2"  ← 删除这行

# 保留第 32 行
__version__ = "3.0.4"
```

**工作量**：5 分钟

---

### 2. 修复 requirements.txt

**问题**：缺少 `requests` 和 `uvicorn`

**文件**：`requirements.txt`

**修复**：
```
pyyaml>=6.0
requests>=2.28.0
fastapi>=0.100.0
uvicorn>=0.23.0
```

**工作量**：5 分钟

---

### 3. CLI 参数默认值引用 Config

**问题**：`--nas-host` 默认值硬编码 `"120.77.249.3"`

**文件**：`arm_diagnose.py`

**修复**：
```python
# 改造前
parser.add_argument("--nas-host", default="120.77.249.3",
                    help="NAS backend host (default: 120.77.249.3)")

# 改造后
parser.add_argument("--nas-host", default=Config.NAS_HOST,
                    help=f"NAS backend host (default: {Config.NAS_HOST})")
```

**工作量**：15 分钟

---

### 4. 版本号统一更新

**文件**：
- `arm_diagnose.py`: `__version__ = "3.0.4"`
- `pyproject.toml`: `version = "3.0.4"`
- `constants.py`: `__version__ = "3.0.4"`

**工作量**：5 分钟

---

## P1 任务（建议完成）- 3 小时

### 5. 诊断进度条优化

**问题**：诊断过程无实时进度反馈

**改进**：
```
🔍 Running diagnostics...

[1/28] System: Python version...          ✅ OK
[2/28] System: pip installed...           ✅ OK
[3/28] System: Memory check...            ✅ OK
[4/28] Network: DNS resolve...            ⚠️ WARN
[5/28] Network: Internet access...        ✅ OK
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Health Score: 85/100
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**文件**：`arm_diagnose.py` 主函数

**工作量**：1 小时

---

### 6. 错误信息更友好

**问题**：异常信息对用户不够友好

**改进**：
```python
# 改造前
raise NetworkError("Connection refused")

# 改造后
raise NetworkError(
    "无法连接到 NAS 后端",
    hint="请检查：\n"
         "  1. NAS 服务是否启动 (systemctl status ai-nas)\n"
         "  2. 网络是否通畅 (ping 192.168.1.100)\n"
         "  3. 端口是否开放 (telnet 192.168.1.100 8000)"
)
```

**文件**：`exceptions.py`

**工作量**：1 小时

---

### 7. 添加诊断结果保存功能

**问题**：诊断结果无法保存，每次重新运行

**改进**：
```bash
# 保存诊断结果
python3 arm_diagnose.py --output report.json
python3 arm_diagnose.py --output report.html

# 对比历史结果
python3 arm_diagnose.py --compare report.json
```

**文件**：
- `arm_diagnose.py`: 添加 `--output` 参数
- 新增 `reporters/file_reporter.py`

**工作量**：1 小时

---

## P2 任务（可选完成）- 2 小时

### 8. 添加配置验证命令

**改进**：
```bash
# 验证配置是否正确
python3 arm_diagnose.py --check-config

# 输出示例
✅ NAS Backend: http://192.168.1.100:8000 (connected)
✅ Web Dashboard: http://0.0.0.0:8080
✅ Log Level: INFO
✅ Thresholds configured
```

**工作量**：30 分钟

---

### 9. 添加快速诊断模式

**改进**：
```bash
# 快速诊断（仅检查关键项）
python3 arm_diagnose.py --quick

# 仅检查系统
python3 arm_diagnose.py --only system

# 仅检查网络
python3 arm_diagnose.py --only network,storage
```

**工作量**：30 分钟

---

### 10. 添加健康趋势跟踪

**改进**：
```bash
# 查看健康分数历史
python3 arm_diagnose.py --history

# 输出示例
Date        Health Score   Status
2026-04-10  85            Good
2026-04-11  82            Warning
2026-04-12  78            Warning ⬇️
```

**工作量**：1 小时

---

## 文件变更清单

### 修改文件

| 文件 | 变更内容 |
|------|----------|
| `arm_diagnose.py` | 修复版本号、CLI 默认值引用 Config、进度条优化 |
| `requirements.txt` | 添加 requests、uvicorn |
| `pyproject.toml` | 版本号 3.0.4 |
| `constants.py` | 版本号 3.0.4 |
| `exceptions.py` | 添加 hint 属性，友好错误信息 |
| `CHANGELOG.md` | v3.0.4 变更日志 |

### 新增文件

| 文件 | 说明 |
|------|------|
| `reporters/file_reporter.py` | 文件报告输出 |
| `data/history.json` | 健康历史数据 |

---

## 时间估算

| 优先级 | 任务 | 工时 |
|--------|------|------|
| P0 | 重复版本号修复 | 5 分钟 |
| P0 | requirements.txt 修复 | 5 分钟 |
| P0 | CLI 默认值优化 | 15 分钟 |
| P0 | 版本号统一更新 | 5 分钟 |
| **P0 小计** | | **30 分钟** |
| P1 | 进度条优化 | 1 小时 |
| P1 | 错误信息友好化 | 1 小时 |
| P1 | 结果保存功能 | 1 小时 |
| **P1 小计** | | **3 小时** |
| P2 | 配置验证命令 | 30 分钟 |
| P2 | 快速诊断模式 | 30 分钟 |
| P2 | 健康趋势跟踪 | 1 小时 |
| **P2 小计** | | **2 小时** |
| **总计** | | **5.5 小时** |

---

## 发布检查清单

### P0 必须完成
- [ ] arm_diagnose.py 删除重复 `__version__`
- [ ] requirements.txt 添加 requests、uvicorn
- [ ] CLI 参数默认值引用 Config
- [ ] 所有文件版本号更新为 3.0.4
- [ ] CHANGELOG 更新
- [ ] 基本功能测试通过

### P1 建议完成
- [ ] 诊断进度条优化
- [ ] 错误信息友好化
- [ ] 结果保存功能

### P2 可选完成
- [ ] 配置验证命令
- [ ] 快速诊断模式
- [ ] 健康趋势跟踪

---

## 不做的事

- ❌ 新增检查项
- ❌ 新增修复脚本
- ❌ 新增设备配置
- ❌ 新增 Web 功能
- ❌ 新增 API 端点
- ❌ 架构重构
- ❌ 性能优化

---

## 升级收益

### 用户体验
- ✅ 安装后可直接运行（依赖完整）
- ✅ 进度实时反馈
- ✅ 错误信息更友好
- ✅ 结果可保存、可对比

### 代码质量
- ✅ 版本号统一
- ✅ 配置引用规范
- ✅ 减少硬编码

### 实用性
- ✅ 快速诊断模式
- ✅ 健康趋势跟踪
- ✅ 配置验证

---

## 与 v3.0.3 对比

| 维度 | v3.0.3 | v3.0.4 |
|------|--------|--------|
| 版本号 | ⚠️ 重复定义 | ✅ 统一 |
| 依赖项 | ⚠️ 缺少 requests/uvicorn | ✅ 完整 |
| CLI 默认值 | ⚠️ 硬编码 | ✅ 引用 Config |
| 进度反馈 | ⚠️ 无 | ✅ 实时进度条 |
| 错误信息 | ⚠️ 技术性 | ✅ 友好提示 |
| 结果保存 | ❌ 不支持 | ✅ JSON/HTML |

---

## 执行顺序

1. **立即执行 P0**（30 分钟内完成）
   - 修复 Bug，确保基本可用

2. **后续执行 P1**（3 小时内完成）
   - 提升用户体验

3. **可选执行 P2**（按需）
   - 增强实用性

---

*计划日期：2026-04-12*
*版本目标：v3.0.4*
*核心目标：好用、实用*
