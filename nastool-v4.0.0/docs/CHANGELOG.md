# CHANGELOG

## v4.0.0 (2026-04-22)

### 性能优化 (Phase A)

- **A-1 检测并行化**: AsyncCheckExecutor，4.2x 提升 (43s→10s)
- **A-2 批量并行**: BatchParallelExecutor，2.1x 提升 (3.7s→1.8s)
- **A-3 内存优化**: StreamingResultProcessor，-50% 内存

### 代码重构 (Phase B)

- **B-1 main.py 拆分**: 4330行→77行，commands/ 模块化架构
- 新增：Command基类、CommandRegistry、装饰器注册

### 用户体验 (Phase C)

- **C-1 Rich输出**: 表格、进度条、面板、彩色消息
- 新增：rich_reporter.py，美化的诊断输出

### 质量提升 (Phase D)

- **D-1 测试覆盖**: 新增12测试（test_v4_features.py + test_stability.py）
- **D-2 文档统一**: docs/README.md 统一入口
- **D-3 稳定性**: 超时配置、资源管理、线程安全测试

### BUG 修复

| BUG | 级别 | 描述 |
|-----|------|------|
| BUG-001 | P1 | AdapterReport → AdapterResult |
| BUG-002 | P1 | BaseAdapter 抽象方法无默认实现 |
| BUG-003/006 | P1 | chip_type 与 device_type 不一致 |
| BUG-004 | P2 | specific_checks/ok 幽灵属性 |
| BUG-005 | P4 | --full 模式静默降级 mock |
| BUG-007 | P1 | NASBackend 系列类缺失 |
| BUG-009 | P3 | 双重 @classmethod |
| BUG-010 | P4 | TYPE_CHECKING 导入幽灵类 |
| BUG-012 | P0 | 裸 except 语句 |
| BUG-013 | P3 | 版本号不一致 |
| BUG-016 | P5 | pydantic 依赖缺失 |
| BUG-017 | P7 | 硬编码密钥和 IP |
| BUG-018 | P0 | GBK 编码问题 |
| BUG-019 | P0 | main.py 入口点缩进错误 |
| BUG-020 | P1 | messages 模块错误导入 |

### 交付物

- Windows 可执行文件 (40.6 MB)
- 完整源码备份
- PyInstaller 构建脚本

---

## v3.0.0 (2026-04-20)

### 新功能

- **多设备管理**: device registry, batch diagnosis, comparison
- **实时监测**: WebSocket client for live status
- **插件系统**: extend checks and adapters via plugins
- **Python SDK**: NASToolAPIClient for Relay Server API
- **OpenAPI spec**: openapi.json for API documentation

### CLI 新命令

```bash
nastool device list                    # 列出所有设备
nastool device add <host> --group prod # 添加设备到分组
nastool device tag <id> --tag rk3588   # 打标签
nastool --batch @devices.txt           # 批量检测
nastool --batch @prod --parallel 4     # 按分组批量检测
nastool compare <id1> <id2>            # 两设备对比
nastool compare <id> --history 7d      # 历史对比
nastool baseline <id>                  # vs 理想基线
nastool monitor <id1> <id2>            # 监控指定设备
nastool monitor --all                  # 监控所有设备
```

---

## v2.0.0 (2026-04-19)

### 新功能

- **RK3588/RK3568 专项支持**: NPU/DDR/thermal/benchmark/driver_ver
- **远程检测**: HTTP + Relay 两种模式
- **调优建议**: 7维分析，3档配置
- **RK专用报告**: 加权评分 + 趋势分析

---

## v1.0.0 (2026-04-18)

### 初始版本

- 93项检测，6大分类
- 本地检测基础功能
- 终端/HTML/JSON 报告
- 自动修复脚本
