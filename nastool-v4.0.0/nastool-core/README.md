# nastool-core

核心模块，提供健康检查、评分和设备管理功能。

## 功能

- 系统健康检查（CPU、内存、磁盘、网络等）
- 存储健康检查（SMART、RAID、磁盘空间等）
- 网络健康检查（连通性、延迟、带宽等）
- 安全检查（SSH配置、防火墙、SSL证书等）
- NAS设备检查（服务状态、配置等）
- AI能力检查（GPU、CUDA、AI框架等）
- 健康评分系统
- 设备管理

## 目录结构

- `nastool_core/`
  - `checks/` - 各种健康检查模块
    - `system/` - 系统检查
    - `storage/` - 存储检查
    - `network/` - 网络检查
    - `security/` - 安全检查
    - `nas/` - NAS设备检查
    - `ai/` - AI能力检查
    - `usb/` - USB设备检查
  - `utils/` - 工具类
    - `health_scorer.py` - 健康评分器
  - `plugin/` - 插件系统
  - `data/` - 数据管理
  - `schemas/` - 数据模型

## 安装

```bash
pip install -e .
```

## 依赖

- `psutil` - 系统信息采集
- `pyyaml` - 配置文件解析
- `requests` - HTTP请求

## 使用示例

### 执行健康检查

```python
from nastool_core.checks.registry import CheckRegistry
from nastool_core.utils.health_scorer import calculate_health_score

# 获取所有检查项
registry = CheckRegistry()
checks = registry.get_all_checks()

# 执行检查
results = []
for check in checks:
    try:
        result = check.execute()
        results.append(result)
        print(f"{check.check_id}: {'通过' if result.passed else '失败'}")
    except Exception as e:
        print(f"{check.check_id}: 错误 - {e}")

# 计算健康评分
report = calculate_health_score(results, previous_score=85)
print(f"\n综合评分: {report.overall_score}/100")
print(f"等级: {report.level_label}")
print(f"等级说明: {report.level_desc}")

# 查看问题项
print("\n严重问题:")
for item in report.critical_items:
    print(f"- {item.check_id}: {item.message}")

print("\n警告:")
for item in report.warnings_items:
    print(f"- {item.check_id}: {item.message}")
```

### 健康评分报告

```python
from nastool_core.utils.health_scorer import HealthScorer, HealthReport

# 创建评分器
scorer = HealthScorer()

# 添加检查结果
scorer.add_results(results)

# 计算报告
report = scorer.calculate(previous_score=85)

# 报告信息
print(f"综合评分: {report.overall_score}/100")
print(f"检查项数: {report.total_checks}")
print(f"通过: {report.total_passed}")
print(f"警告: {report.total_warnings}")
print(f"严重: {report.total_critical}")

# 分类评分
print("\n分类评分:")
for cat in report.category_scores:
    print(f"{cat.name}: {cat.score}/100")
```

### 快速诊断

```python
from nastool_core.utils.quick_diagnose import quick_diagnose

# 执行快速诊断
diagnosis = quick_diagnose()

print("快速诊断结果:")
print(f"系统状态: {'正常' if diagnosis['system'] else '异常'}")
print(f"存储状态: {'正常' if diagnosis['storage'] else '异常'}")
print(f"网络状态: {'正常' if diagnosis['network'] else '异常'}")
print(f"安全状态: {'正常' if diagnosis['security'] else '异常'}")
```

## 检查项分类

### 系统检查
- CPU温度
- 内存使用
- 磁盘空间
- 系统负载
- 进程数量
- 系统更新
- Python版本

### 存储检查
- 硬盘SMART状态
- RAID阵列状态
- 磁盘空间使用
- 磁盘温度
- 写入速度
- Docker镜像清理

### 网络检查
- 互联网访问
- 网络延迟
- 带宽测试
- DNS解析
- MTU设置
- 端口冲突

### 安全检查
- SSH配置
- 防火墙状态
- 登录失败次数
- SSL证书
- Fail2ban状态

### NAS设备检查
- 服务状态（SMB、NFS、FTP等）
- 备份状态
- 日志磁盘使用
- 用户统计

### AI能力检查
- GPU检测
- CUDA版本
- AI框架检查（TensorFlow、PyTorch等）
- GPU内存使用

## 健康评分规则

- **100-90分**：优秀，系统状态良好
- **89-80分**：良好，存在少量可优化项
- **79-70分**：一般，存在一些警告
- **69-60分**：较差，需要关注
- **59分以下**：严重，需要立即处理

## 性能优化

- **并行执行**：支持批量并行执行检查
- **超时管理**：为检查项设置超时时间
- **内存优化**：减少内存使用
- **缓存机制**：缓存检查结果

## 扩展检查项

可以通过插件系统添加自定义检查项：

```python
from nastool_core.checks.base import CheckBase
from nastool_core.checks.registry import CheckRegistry

class CustomCheck(CheckBase):
    check_id = "custom_check"
    name = "自定义检查"
    description = "我的自定义健康检查"
    category = "system"
    severity = "medium"
    
    def execute(self):
        # 执行检查逻辑
        result = self._run_check()
        return result

# 注册检查项
registry = CheckRegistry()
registry.register(CustomCheck)
```

## 许可证

MIT