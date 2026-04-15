# nastool v3.0.5 升级计划 — 稳定性优先

**目标**：工具不崩溃、不挂起、不静默失败

**原则**：零新功能，专注稳定性

---

## 诊断结果

| 问题 | 数量 | 严重性 |
|------|------|--------|
| 裸 except | 0 | ✅ 已消除 |
| print() 残留 | 167 | ⚠️ 高 |
| 外部依赖未保护 | 4 | ⚠️ 高 |
| 资源泄漏风险 | 0 | ✅ 已消除 |
| 硬编码公网IP | 7 | ⚠️ 中 |
| 网络请求无超时 | 多处 | ⚠️ 中 |
| 外部命令无超时 | 多处 | ⚠️ 中 |

---

## P0 任务（必须修复，3小时）

### P0.1 print() 完全替换为 logger（2小时）

**原因**：
- print() 无法控制级别
- 输出不可关闭/重定向
- 生产环境不适用

**范围**：
```
arm_diagnose.py: 51 处
quick_diagnose.py: 17 处
history.py: 17 处
progress.py: 16 处
terminal.py: 12 处
其他文件: 54 处
```

**策略**：
- 信息输出 → `logger.info()`
- 错误输出 → `logger.error()`
- 调试输出 → `logger.debug()`
- 保留：终端报告器中的 `print()`（用户可见输出）

### P0.2 外部依赖导入保护（1小时）

**问题文件**：
- yaml 导入：4 个文件未保护

**修复**：
```python
# 之前
import yaml

# 之后
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not installed, config file support disabled")
```

**影响模块**：
- `config.py` - 配置加载
- `profiles/loader.py` - 设备配置
- `utils/config_validator.py` - 配置验证
- `utils/history.py` - 历史记录

---

## P1 任务（提高健壮性，2小时）

### P1.1 网络请求超时设置（1小时）

**问题**：requests 调用无超时 → 可能永久挂起

**修复**：
```python
# 之前
response = requests.get(url)

# 之后
response = requests.get(url, timeout=10)
```

**检查范围**：
- `api/__init__.py`
- `nas_integration/client.py`
- `core/network.py`
- `utils/config_validator.py`

### P1.2 外部命令超时设置（1小时）

**问题**：subprocess 调用无超时 → 可能永久挂起

**修复**：
```python
# 之前
result = subprocess.run(cmd, capture_output=True)

# 之后
result = subprocess.run(cmd, capture_output=True, timeout=30)
```

**检查范围**：
- `checks/**/*.py` - 所有检查器
- `fixes/**/*.py` - 所有修复器
- `core/device.py` - 设备检测

---

## P2 任务（可选，1小时）

### P2.1 硬编码 IP 清理（30分钟）

**问题**：7 处硬编码公网 IP

**策略**：
- 移除或改为 `Config.XXX`

### P2.2 优雅降级机制（30分钟）

**功能**：当关键依赖缺失时，提供降级方案

**示例**：
- 无 psutil → 基础设备检测仍可用
- 无 yaml → 仅用环境变量配置
- 无 colorama → 无颜色输出

---

## 发布检查清单

- [ ] 所有 print() 替换为 logger（保留 terminal.py）
- [ ] 外部依赖导入全部保护
- [ ] 网络请求全部设置超时
- [ ] 外部命令全部设置超时
- [ ] 硬编码 IP 清理
- [ ] Python 语法检查通过
- [ ] CHANGELOG 更新
- [ ] 版本号 → 3.0.5

---

## 不做的清单

❌ 新增检查项
❌ 新增修复脚本
❌ 新增 CLI 参数
❌ 新增功能模块
❌ API 变更

---

## 预期成果

**升级前**：
- 167 个 print() 无法控制
- 缺包时直接崩溃
- 网络问题可能挂起
- 外部命令可能卡死

**升级后**：
- 日志级别可控
- 缺包时优雅降级
- 网络请求 10s 超时
- 外部命令 30s 超时
- **工具不会崩溃、不会挂起**
