# NASTool V7.2 开发者指南

## 1. 开发环境搭建

### 1.1 环境要求

- Python 3.9+
- Git
- 建议使用虚拟环境

### 1.2 克隆仓库

```bash
git clone git@github.com:leon2397/nastool.git
cd nastool
```

### 1.3 创建虚拟环境

```bash
# Linux/Mac
python -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 1.4 安装依赖

```bash
# 安装所有模块（开发模式）
pip install -e ./nastool-common
pip install -e ./nastool-core
pip install -e ./nastool-adapters
pip install -e ./nastool-reporters
pip install -e ./nastool-fixes
pip install -e ./nastool-cli

# 安装测试依赖
pip install pytest pytest-cov
```

---

## 2. 项目结构

```
nastool/
├── docs/                    # 文档
│   ├── ARCHITECTURE.md      # 架构文档
│   ├── API.md               # API 文档
│   └── DEVELOPER_GUIDE.md   # 开发者指南
├── nastool-cli/             # 命令行接口
│   └── nastool_cli/
│       ├── main.py          # 入口文件
│       └── ...
├── nastool-core/            # 核心模块
│   └── nastool_core/
│       ├── checks/          # 检查框架
│       ├── utils/           # 工具函数
│       ├── config/          # 配置管理
│       ├── plugin/          # 插件系统
│       └── ...
├── nastool-adapters/        # 设备适配器
│   └── nastool_adapters/
├── nastool-common/          # 公共模块
│   └── nastool_common/
├── nastool-reporters/       # 报告生成
│   └── nastool_reporters/
├── nastool-fixes/           # 自动修复
│   └── nastool_fixes/
└── tests/                   # 测试用例
```

---

## 3. 开发流程

### 3.1 分支管理

- `main`：主分支，稳定版本
- `develop`：开发分支，日常开发
- `feature/*`：功能分支
- `bugfix/*`：修复分支

### 3.2 开发步骤

1. 从 `develop` 分支创建功能分支
2. 实现功能
3. 编写测试用例
4. 运行测试
5. 提交 PR 到 `develop`

---

## 4. 编写检查插件

### 4.1 创建检查类

创建新的检查类需要继承 `Check` 基类并实现 `run()` 方法。

#### 示例：创建自定义检查

```python
from nastool_core.checks import register_check, Check, CheckResult
from nastool_core.checks.base import CheckCategory, CheckSeverity

@register_check
class CustomSystemCheck(Check):
    """
    自定义系统检查示例
    """
    
    check_id = "custom_system_check"
    category = CheckCategory.SYSTEM
    title = "Custom System Check"
    description = "检查系统自定义指标"
    
    # 可选：配置准确性增强
    enable_data_fusion = True
    enable_consistency_check = True
    
    def run(self) -> CheckResult:
        """
        执行检查逻辑
        
        Returns:
            CheckResult: 检查结果
        """
        # 执行检查逻辑
        try:
            # 获取系统信息
            result = self._run_command("echo 'test'")
            
            if result == "test":
                return CheckResult(
                    check_id=self.check_id,
                    category=self.category,
                    severity=CheckSeverity.PASSED,
                    passed=True,
                    title=self.title,
                    current="OK",
                    expected="OK",
                    message="自定义检查通过"
                )
            else:
                return CheckResult(
                    check_id=self.check_id,
                    category=self.category,
                    severity=CheckSeverity.WARNING,
                    passed=False,
                    title=self.title,
                    current=f"Got: {result}",
                    expected="OK",
                    message="自定义检查警告",
                    fix_available=True,
                    fix_command="echo 'fix command'"
                )
        except Exception as e:
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.CRITICAL,
                passed=False,
                title=self.title,
                current="Error",
                expected="OK",
                message=f"检查失败: {str(e)}"
            )
```

### 4.2 使用多源数据融合

```python
def run(self) -> CheckResult:
    # 创建多数据源
    sources = [
        ("source1", self._read_file, {"path": "/proc/cpuinfo"}),
        ("source2", self._run_command, {"cmd": "cat /proc/cpuinfo"}),
    ]
    
    # 并行采集数据
    results = self._collect_data_parallel(sources)
    
    # 执行数据融合
    fused_value, metadata = self._fuse_multiple_sources(results)
    
    # 验证一致性
    consistency = self._validate_consistency(results)
    
    # 创建结果
    result = CheckResult(
        check_id=self.check_id,
        category=self.category,
        severity=CheckSeverity.PASSED,
        passed=True,
        title=self.title,
        current=str(fused_value),
        expected="OK",
        message="检查通过"
    )
    
    # 增强准确性信息
    return self._enhance_result_with_accuracy(result, results)
```

### 4.3 添加到模块

将检查类放在 `nastool-core/nastool_core/checks/` 下的对应目录：

- 系统检查 → `checks/system/`
- 网络检查 → `checks/network/`
- 存储检查 → `checks/storage/`
- AI 检查 → `checks/ai/`
- 安全检查 → `checks/security/`
- NAS 检查 → `checks/nas/`
- USB 检查 → `checks/usb/`

---

## 5. 编写测试用例

### 5.1 测试文件结构

测试文件应放在各模块的 `tests/` 目录下：

```
nastool-core/
└── tests/
    ├── test_core.py              # 核心测试
    ├── test_checks_detailed.py   # 检查详细测试
    └── test_data_fusion_integration.py  # 数据融合集成测试
```

### 5.2 测试示例

```python
import pytest
from nastool_core.checks import run_check, run_all_checks

class TestCustomCheck:
    """测试自定义检查"""
    
    def test_custom_check_exists(self):
        """测试检查已注册"""
        from nastool_core.checks.registry import get_check
        check_class = get_check("custom_system_check")
        assert check_class is not None
    
    def test_custom_check_run(self):
        """测试检查执行"""
        result = run_check("custom_system_check")
        assert result is not None
        assert result.check_id == "custom_system_check"
    
    def test_custom_check_passed(self):
        """测试检查通过情况"""
        result = run_check("custom_system_check")
        assert result.passed is True
    
    def test_all_checks_run(self):
        """测试所有检查执行"""
        summary = run_all_checks()
        assert summary.total > 0
        assert summary.score >= 0
        assert summary.score <= 100
```

### 5.3 运行测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest nastool-core/tests/

# 运行特定测试文件
pytest nastool-core/tests/test_core.py

# 生成覆盖率报告
pytest --cov=nastool-core
```

---

## 6. 调试技巧

### 6.1 启用调试日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 6.2 使用 pdb 调试

```python
import pdb; pdb.set_trace()
```

### 6.3 运行单个检查调试

```bash
nastool check <check_id> --verbose
```

---

## 7. 代码规范

### 7.1 命名规范

- **模块名**：小写字母，下划线分隔（`my_module.py`）
- **类名**：大驼峰命名（`MyClass`）
- **函数/方法名**：小写字母，下划线分隔（`my_function`）
- **变量名**：小写字母，下划线分隔（`my_variable`）
- **常量名**：全大写，下划线分隔（`MAX_VALUE`）

### 7.2 代码风格

- 使用 4 空格缩进
- 每行不超过 120 字符
- 使用类型提示
- 添加适当的注释

### 7.3 文档规范

每个模块、类、方法都应包含文档字符串：

```python
def my_function(param1: str, param2: int) -> bool:
    """
    函数描述
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
    
    Returns:
        返回值说明
    
    Raises:
        异常类型: 异常说明
    """
    pass
```

---

## 8. 发布流程

### 8.1 更新版本号

在各模块的 `pyproject.toml` 中更新版本号：

```toml
version = "7.2.0"
```

### 8.2 运行测试

```bash
pytest
```

### 8.3 创建标签

```bash
git tag v7.2.0
git push origin v7.2.0
```

### 8.4 CI/CD 自动发布

推送标签后，GitHub Actions 会自动执行：
1. 运行测试
2. 构建包
3. 发布到 PyPI
4. 创建 GitHub Release

---

## 9. 常见问题

### 9.1 检查未注册

**问题**：`run_check("my_check")` 返回 `None`

**原因**：检查类未被导入，导致未注册

**解决**：确保检查类所在模块被导入到 `checks/__init__.py`

### 9.2 依赖冲突

**问题**：安装依赖时出现版本冲突

**解决**：使用虚拟环境，确保 Python 版本符合要求

### 9.3 测试失败

**问题**：测试用例失败

**解决**：
1. 检查测试环境
2. 查看详细错误信息
3. 确保代码逻辑正确

---

## 10. 贡献指南

### 10.1 提交规范

提交信息遵循以下格式：

```
<类型>: <描述>

<详细说明（可选）>
```

**类型**：
- `feat`：新功能
- `fix`：修复 bug
- `docs`：文档更新
- `refactor`：代码重构
- `test`：测试更新
- `chore`：杂项任务

**示例**：
```
feat: add custom system check

- 添加自定义系统检查类
- 添加对应的测试用例
```

### 10.2 PR 流程

1. Fork 仓库
2. 创建功能分支
3. 实现功能
4. 编写测试
5. 提交 PR
6. 等待审核

---

## 附录：常用命令

```bash
# 安装开发环境
pip install -e .

# 运行检查
nastool check <check_id>

# 运行快速诊断
nastool --quick

# 生成报告
nastool --output report.html --format html

# 运行测试
pytest

# 格式化代码
black .

# 检查代码风格
flake8
```