# nastool-reporters

报告生成模块，提供各种格式的诊断报告输出。

## 功能

- 终端报告（彩色输出）
- JSON报告
- HTML报告
- 友好报告（易于阅读的HTML格式）
- PDF报告（专业格式，支持Logo）
- 健康仪表盘
- RK报告

## 目录结构

- `nastool_reporters/`
  - `pdf_reporter.py` - PDF报告生成器
  - `html_reporter.py` - HTML报告生成器
  - `json_reporter.py` - JSON报告生成器
  - `terminal.py` - 终端报告生成器
  - `friendly_reporter.py` - 友好报告生成器
  - `health_dashboard.py` - 健康仪表盘
  - `rk_reporter.py` - RK报告生成器
  - `file_reporter.py` - 文件报告生成器

## 安装

```bash
pip install -e .

# PDF报告需要额外安装
pip install reportlab
```

## 依赖

- `reportlab` - PDF报告生成（可选）
- `pyyaml` - 配置文件解析

## 使用示例

### PDF报告

```python
from nastool_reporters.pdf_reporter import PDFReporter, generate_pdf_report
from nastool_core.utils.health_scorer import calculate_health_score
from nastool_core.checks.registry import CheckRegistry

# 执行检查
registry = CheckRegistry()
checks = registry.get_all_checks()
results = [check.execute() for check in checks]

# 计算健康评分
report = calculate_health_score(results)

# 生成PDF报告
reporter = PDFReporter(
    logo_path="path/to/logo.png",  # 可选
    title="系统健康诊断报告",
    author="NASTool"
)

# 生成PDF
success = reporter.generate(report, "health_report.pdf")
print(f"PDF生成: {'成功' if success else '失败'}")

# 或者使用便捷函数
success = generate_pdf_report(report, "health_report.pdf")
```

### HTML报告

```python
from nastool_reporters.html_reporter import HTMLReporter

reporter = HTMLReporter()
html = reporter.build(report)

# 保存到文件
with open("report.html", "w", encoding="utf-8") as f:
    f.write(html)

print("HTML报告已生成")
```

### JSON报告

```python
from nastool_reporters.json_reporter import JSONReporter

reporter = JSONReporter()
data = reporter.build(report)

# 保存到文件
reporter.dump("report.json")

print("JSON报告已生成")
```

### 终端报告

```python
from nastool_reporters.terminal import TerminalReporter

reporter = TerminalReporter()
reporter.print_report(results)
```

### 友好报告

```python
from nastool_reporters.friendly_reporter import FriendlyReporter

reporter = FriendlyReporter()
html = reporter.build_html(results)

with open("friendly_report.html", "w", encoding="utf-8") as f:
    f.write(html)

print("友好报告已生成")
```

### 健康仪表盘

```python
from nastool_reporters.health_dashboard import HealthDashboard

reporter = HealthDashboard()
dashboard = reporter.build(report)

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(dashboard)

print("健康仪表盘已生成")
```

## PDF报告特性

- **专业格式**：包含封面、综合评分、分类详情、问题列表和建议
- **支持Logo**：可以添加自定义Logo
- **中文支持**：支持中文显示
- **美观布局**：专业的排版和样式
- **详细信息**：包含完整的健康评分信息

## 报告格式对比

| 格式 | 优点 | 适用场景 |
|------|------|----------|
| PDF | 专业、可打印 | 正式报告、存档 |
| HTML | 交互性好、美观 | 在线查看、分享 |
| JSON | 机器可读、结构化 | 数据交换、自动化处理 |
| 终端 | 实时、简洁 | 命令行操作、快速查看 |
| 友好报告 | 易于阅读、直观 | 非技术人员查看 |

## 自定义报告

### 自定义PDF报告

```python
from nastool_reporters.pdf_reporter import PDFReporter

class CustomPDFReporter(PDFReporter):
    def _add_custom_section(self, story, report):
        """添加自定义章节"""
        from reportlab.platypus import Paragraph
        
        story.append(Paragraph("自定义章节", self._styles['PDFHeading']))
        story.append(Paragraph("这是自定义内容", self._styles['PDFBody']))
    
    def generate(self, report, output_path):
        """重写生成方法，添加自定义章节"""
        # 调用父类方法
        super().generate(report, output_path)
        
        # 添加自定义内容
        # ...

# 使用
reporter = CustomPDFReporter()
reporter.generate(report, "custom_report.pdf")
```

## 性能优化

- **延迟加载**：PDF报告依赖在需要时才加载
- **内存优化**：生成过程中合理管理内存
- **并行处理**：支持批量生成报告

## 注意事项

- PDF报告需要安装 `reportlab` 库
- 生成大型报告时可能需要较多内存
- Logo图片应使用合适的尺寸和格式

## 许可证

MIT