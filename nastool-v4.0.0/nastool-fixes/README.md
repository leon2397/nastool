# nastool-fixes

修复模块，提供各种系统问题的自动修复功能。

## 功能

- 安全问题修复（禁用root登录、启用fail2ban等）
- 存储问题修复（清理Docker镜像、日志等）
- 网络问题修复（配置DNS等）
- NAS设备修复（配置UPS关机等）
- AI相关修复（安装CUDA等）
- 自动回滚机制

## 目录结构

- `nastool_fixes/`
  - `ai/` - AI相关修复
  - `nas/` - NAS设备修复
  - `network/` - 网络修复
  - `security/` - 安全修复
  - `storage/` - 存储修复
  - `base.py` - 修复基类
  - `fix_engine.py` - 修复引擎
  - `registry.py` - 修复注册表

## 安装

```bash
pip install -e .
```

## 依赖

- `paramiko` - SSH连接（用于远程修复）
- `pyyaml` - 配置文件解析

## 使用示例

### 执行修复

```python
from nastool_fixes.registry import FixRegistry
from nastool_fixes.fix_engine import FixEngine

# 获取修复注册表
registry = FixRegistry()

# 获取可用修复
available_fixes = registry.get_available_fixes()
print("可用修复:")
for fix_id, fix_info in available_fixes.items():
    print(f"- {fix_id}: {fix_info['name']}")

# 创建修复引擎
engine = FixEngine()

# 执行特定修复
try:
    result = engine.apply_fix("disable_root_login")
    print(f"修复结果: {'成功' if result else '失败'}")
except Exception as e:
    print(f"修复失败: {e}")
```

### 批量修复

```python
from nastool_fixes.fix_engine import FixEngine

engine = FixEngine()

# 批量执行修复
fixes_to_apply = [
    "disable_root_login",
    "enable_fail2ban",
    "cleanup_docker_images"
]

results = engine.batch_apply(fixes_to_apply)
for fix_id, success in results.items():
    print(f"{fix_id}: {'成功' if success else '失败'}")
```

### 修复建议

```python
from nastool_fixes.fix_recommendations import generate_fix_recommendations
from nastool_core.checks.base import CheckResult, CheckSeverity

# 模拟检查结果
results = [
    CheckResult(
        check_id="ssh_root",
        category="security",
        severity=CheckSeverity.CRITICAL,
        passed=False,
        title="SSH Root Login",
        current="Enabled",
        expected="Disabled",
        message="SSH root login is enabled"
    ),
    CheckResult(
        check_id="docker_images",
        category="storage",
        severity=CheckSeverity.WARNING,
        passed=False,
        title="Docker Images",
        current="20GB",
        expected="<10GB",
        message="Docker images taking too much space"
    )
]

# 生成修复建议
suggestions = generate_fix_recommendations(results)
print("修复建议:")
for suggestion in suggestions:
    print(f"- {suggestion['fix_id']}: {suggestion['description']} (风险: {suggestion['risk']})")
```

## 修复模块列表

### 安全修复
- `disable_root_login` - 禁用SSH root登录
- `enable_fail2ban` - 启用fail2ban防暴力破解
- `enforce_password_policy` - 强化密码策略
- `renew_ssl_cert` -  renewal SSL证书

### 存储修复
- `cleanup_docker_images` - 清理Docker镜像
- `cleanup_logs` - 清理系统日志
- `cleanup_tmp_space` - 清理临时空间

### 网络修复
- `config_dns` - 配置DNS服务器

### NAS修复
- `config_ups_shutdown` - 配置UPS关机策略

### AI修复
- `install_cuda` - 安装CUDA

## 回滚机制

所有修复都支持自动回滚：

```python
from nastool_fixes.fix_engine import FixEngine

engine = FixEngine()

# 执行修复（失败时自动回滚）
try:
    result = engine.apply_fix("disable_root_login")
    print(f"修复结果: {'成功' if result else '失败'}")
except Exception as e:
    print(f"修复失败，已自动回滚: {e}")

# 手动回滚
rollback_result = engine.rollback_fix("disable_root_login")
print(f"回滚结果: {'成功' if rollback_result else '失败'}")
```

## 修复风险等级

- **low** - 低风险，安全执行
- **medium** - 中等风险，可能影响系统行为
- **high** - 高风险，可能导致系统不稳定

## 扩展修复模块

可以通过继承`Fix`基类创建自定义修复模块：

```python
from nastool_fixes.base import Fix
from nastool_fixes.registry import FixRegistry

class CustomFix(Fix):
    fix_id = "custom_fix"
    name = "自定义修复"
    description = "我的自定义修复"
    risk = "low"
    
    def apply(self):
        # 执行修复逻辑
        # ...
        return True
    
    def rollback(self):
        # 执行回滚逻辑
        # ...
        return True

# 注册修复模块
registry = FixRegistry()
registry.register(CustomFix)
```

## 许可证

MIT