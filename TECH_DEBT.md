# nastools 技术债务清单

> 版本：V4.0.1
> 更新时间：2026-04-14

---

## 一、日志记录点待补充（71 处）

**状态**：🟡 已知债务，不影响功能
**优先级**：P2（建议 V5.0 处理）
**工时**：约 4 小时

### 问题描述

V4.0 日志系统已统一（`logger.py` + `get_logger`），但部分 `except` 块捕获异常后未记录日志，仅标记 `# TODO: 添加日志`。

### 影响范围

| 文件 | 数量 | 说明 |
|------|------|------|
| `core/network_health.py` | 10 | 网络检测异常处理 |
| `core/security_health.py` | 6 | 安全检测异常处理 |
| `core/ai_accel.py` | 5 | AI 加速器检测异常处理 |
| `core/device.py` | 5 | 设备信息获取异常处理 |
| `core/nas_health.py` | 5 | NAS 健康检测异常处理 |
| `core/system_health.py` | 5 | 系统检测异常处理 |
| `core/storage.py` | 4 | 存储检测异常处理 |
| `core/storage_health.py` | 3 | 存储健康检测异常处理 |
| `fixes/system/check_versions.py` | 6 | 版本检测异常处理 |
| `profiles/loader.py` | 6 | 配置加载异常处理 |
| `checks/ai/*.py` | 3 | AI 检查异常处理 |
| `checks/network/dns_resolve.py` | 1 | DNS 解析异常处理 |
| `adapters/*.py` | 5 | 适配器异常处理 |
| `core/network.py` | 1 | 网络工具异常处理 |
| `core/upnp_scanner.py` | 1 | UPnP 扫描异常处理 |
| `core/version_check.py` | 1 | 版本检查异常处理 |

### 修复建议

```python
# 当前代码
except Exception as e:
    pass  # TODO: 添加日志

# 建议修改为
except Exception as e:
    logger.warning(f"操作失败: {e}")
```

### 不修复理由

1. 功能正常：异常被正确捕获，不影响程序运行
2. 风险低：仅影响调试时的日志可见性
3. 工时较高：需要逐文件检查上下文，约 4 小时

---

## 二、硬编码 IP/路径（5 处）

**状态**：🟡 部分完成（创建配置模板）
**优先级**：P2（V4.0.1 不强制）

| 文件 | 位置 | 内容 |
|------|------|------|
| `core/network.py` | 多处 | 192.168.x.x 示例 IP |
| `core/security_health.py` | 多处 | 网络地址范围 |
| `scripts/setup_usb_gadget.py` | 配置 | USB 网络地址 |
| `tests/test_network.py` | 测试用例 | 测试用 IP |
| `tests/test_exceptions.py` | 测试用例 | 测试用 IP |

### 修复结果（V4.0.1）

- [x] 创建 `nastool/network_config.yaml`（配置模板）
- [x] 检查核心代码硬编码：全部在注释中（非运行时值）
  - `network.py:79` - 示例输出格式
  - `security_health.py:160,182` - 日志示例

### 结论

✅ **无需修改**：所有硬编码 IP 都在注释中作为示例，非实际运行值。

**文件中的运行值**：
- `jetson_install.py` - localhost/1/tmp/1 是命令行默认值，可覆盖
- `jetson_patch.py` - 同上

V4.1 如需配置化，可基于 `network_config.yaml` 扩展。

---

## 三、核心模块 docstring 补充（V4.0.1）

**状态**：✅ 已完成

| 模块 | 函数数 | 已补充 docstring |
|------|--------|-----------------|
| `core/safety.py` | 13 | 8 (BackupManager 类 4 个，装饰器 4 个) |
| `core/network.py` | 8 | 6 (接口/连通性测试) |
| `adapters/adb_adapter.py` | 25 | 27 (已超过，可能有嵌套) |
| `scripts/setup_usb_gadget.py` | 28 | 20 |

**无 docstring 函数**（不影响功能，仅代码可读性）：
- safety.py: safe_subprocess, get_hostname, load_config, 装饰器内部函数
- network.py: _run, _is_ipv4, _cidr_to_netmask, check_network

**结论**：V4.0.1 核心模块 docstring 已满足最低要求。

---

## 四、测试覆盖不足

**状态**：🟡 已知债务
**优先级**：P2（建议 V5.0 处理）

- 单元测试覆盖率：< 10%
- 集成测试：缺失
- GUI 测试：缺失

---

## 五、Relay Server 路径验证缺失（2026-04-14）

**状态**：🟡 已修复，但需要长期改进
**优先级**：P1（建议 V4.1.0 处理）
**问题**：数据库/配置文件路径不正确时不报错，创建空文件覆盖已有数据

### 问题描述

`relay_server/src/db.js` 中使用相对路径 `../data` 计算数据库路径，但未验证路径是否正确：
- 当路径计算错误时（如 `../../data` → `/data`），服务器会创建新的空数据库
- 覆盖已有数据，且不输出任何警告

### 事件时间线

1. 20:25 - ARM Agent 连接失败，"Invalid agent_key"
2. 20:33 - 发现根因：`__dirname` 解析错误导致数据库路径错误
3. 20:35 - 修复：`../../data` → `../data`
4. 20:36 - Agent 连接成功

### 修复建议

```javascript
// 启动时验证
if (!existsSync(DB_PATH)) {
  console.error(`[DB] ERROR: Database not found at ${DB_PATH}`);
  process.exit(1);
}
```

### 待办清单

- [ ] 添加启动时路径存在性检查
- [ ] 添加配置验证脚本 `scripts/verify-paths.js`
- [ ] 统一日志格式，便于自动化监控

---

## 六、文档待补充

**状态**：🟡 已知债务

- API 文档：缺失
- 架构文档：缺失
- 开发指南：缺失

---

**总结**：V4.0.1 保留现有功能，不增加新功能。以上技术债务记录在案，供后续版本参考。
