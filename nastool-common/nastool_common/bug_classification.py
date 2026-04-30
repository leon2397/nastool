"""
BUG 分类标准化体系 (T-A/T-B/T-C/T-D)

本模块定义了标准化的 BUG 分类体系，用于统一 BUG 的严重程度和处理优先级。

分类体系：
- T-A: 致命问题 (Critical) - 系统崩溃、数据丢失、安全漏洞
- T-B: 严重问题 (Major)    - 核心功能失效、严重影响用户体验
- T-C: 一般问题 (Minor)    - 次要功能问题、界面瑕疵
- T-D: 轻微问题 (Trivial)  - 改进建议、文档问题、代码优化

使用示例：
    from nastool_common.bug_classification import BugCategory, classify_bug
    
    category = classify_bug(severity="critical", impact="system_crash")
    print(f"BUG 分类: {category.value}")  # T-A
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


class BugCategory(Enum):
    """
    BUG 分类枚举
    
    T-A: 致命问题 - 系统崩溃、数据丢失、安全漏洞
    T-B: 严重问题 - 核心功能失效、严重影响用户体验
    T-C: 一般问题 - 次要功能问题、界面瑕疵
    T-D: 轻微问题 - 改进建议、文档问题、代码优化
    """
    T_A = "T-A"
    T_B = "T-B"
    T_C = "T-C"
    T_D = "T-D"


class ImpactType(Enum):
    """
    影响类型枚举
    """
    SYSTEM_CRASH = "system_crash"           # 系统崩溃
    DATA_LOSS = "data_loss"                 # 数据丢失/损坏
    SECURITY_VULNERABILITY = "security"     # 安全漏洞
    CORE_FUNCTION_FAILURE = "core_failure"  # 核心功能失效
    MAJOR_UX_ISSUE = "major_ux"            # 严重用户体验问题
    MINOR_FUNCTION_ISSUE = "minor_issue"    # 次要功能问题
    UI_GLITCH = "ui_glitch"                 # 界面瑕疵
    DOCUMENTATION_ISSUE = "docs"            # 文档问题
    PERFORMANCE_OPTIMIZATION = "performance"# 性能优化
    CODE_QUALITY = "code_quality"           # 代码质量改进


class SeverityLevel(Enum):
    """
    严重程度枚举
    """
    CRITICAL = "critical"  # 致命
    MAJOR = "major"        # 严重
    MINOR = "minor"        # 一般
    TRIVIAL = "trivial"    # 轻微


@dataclass
class BugClassification:
    """
    BUG 分类结果
    """
    category: BugCategory
    severity: SeverityLevel
    impact: ImpactType
    priority: int  # 优先级 1-5，1 最高
    description: str


def classify_bug(
    severity: Optional[str] = None,
    impact: Optional[str] = None,
    description: Optional[str] = None
) -> BugClassification:
    """
    根据严重程度和影响类型分类 BUG
    
    Args:
        severity: 严重程度 (critical/major/minor/trivial)
        impact: 影响类型
        description: BUG 描述（用于自动分类）
    
    Returns:
        BugClassification: 分类结果
    """
    # 标准化输入
    severity = severity.lower() if severity else "unknown"
    impact = impact.lower() if impact else "unknown"
    
    # 根据严重程度和影响类型进行分类
    if severity == "critical" or impact in ["system_crash", "data_loss", "security"]:
        category = BugCategory.T_A
        severity_level = SeverityLevel.CRITICAL
        priority = 1
        desc = "致命问题：系统崩溃、数据丢失或安全漏洞"
    
    elif severity == "major" or impact in ["core_failure", "major_ux"]:
        category = BugCategory.T_B
        severity_level = SeverityLevel.MAJOR
        priority = 2
        desc = "严重问题：核心功能失效或严重影响用户体验"
    
    elif severity == "minor" or impact in ["minor_issue", "ui_glitch"]:
        category = BugCategory.T_C
        severity_level = SeverityLevel.MINOR
        priority = 3
        desc = "一般问题：次要功能问题或界面瑕疵"
    
    else:  # trivial or docs/performance/code_quality
        category = BugCategory.T_D
        severity_level = SeverityLevel.TRIVIAL
        priority = 4
        desc = "轻微问题：改进建议、文档问题或代码优化"
    
    return BugClassification(
        category=category,
        severity=severity_level,
        impact=ImpactType(impact) if impact in [i.value for i in ImpactType] else None,
        priority=priority,
        description=desc
    )


def get_category_rules() -> Dict[str, Dict[str, Any]]:
    """
    获取分类规则说明
    
    Returns:
        Dict: 分类规则字典
    """
    return {
        "T-A": {
            "name": "致命问题",
            "severity": "Critical",
            "priority": 1,
            "description": "导致系统崩溃、数据丢失或存在安全漏洞的问题",
            "examples": [
                "应用程序启动即崩溃",
                "数据写入失败导致数据丢失",
                "SQL 注入漏洞",
                "认证绕过漏洞",
                "内存泄漏导致系统宕机"
            ],
            "response_time": "立即处理，24小时内修复",
            "impact": "严重影响系统可用性和数据安全"
        },
        "T-B": {
            "name": "严重问题",
            "severity": "Major",
            "priority": 2,
            "description": "核心功能失效或严重影响用户体验的问题",
            "examples": [
                "主要功能按钮点击无响应",
                "报告生成失败",
                "检查结果错误",
                "API 返回错误数据",
                "性能严重下降"
            ],
            "response_time": "48小时内处理",
            "impact": "影响核心功能使用"
        },
        "T-C": {
            "name": "一般问题",
            "severity": "Minor",
            "priority": 3,
            "description": "次要功能问题或界面瑕疵",
            "examples": [
                "界面布局错位",
                "错误提示信息不准确",
                "次要功能偶尔失败",
                "UI 样式不一致"
            ],
            "response_time": "1周内处理",
            "impact": "轻微影响用户体验"
        },
        "T-D": {
            "name": "轻微问题",
            "severity": "Trivial",
            "priority": 4,
            "description": "改进建议、文档问题或代码优化",
            "examples": [
                "文档错别字",
                "代码注释缺失",
                "代码重复",
                "性能优化建议",
                "功能增强请求"
            ],
            "response_time": "按需处理",
            "impact": "无功能性影响"
        }
    }


def format_bug_report(
    bug_id: str,
    title: str,
    description: str,
    category: BugCategory,
    severity: SeverityLevel,
    priority: int,
    assignee: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> str:
    """
    格式化 BUG 报告
    
    Args:
        bug_id: BUG ID
        title: BUG 标题
        description: BUG 描述
        category: 分类
        severity: 严重程度
        priority: 优先级
        assignee: 负责人
        tags: 标签列表
    
    Returns:
        str: 格式化的 BUG 报告
    """
    tags = tags or []
    tag_str = ", ".join(tags)
    
    return f"""
╔══════════════════════════════════════════════════════════════════╗
║ BUG 报告                                                         ║
╠══════════════════════════════════════════════════════════════════╣
║ ID:         {bug_id}                                            ║
║ 分类:       {category.value} ({get_category_rules()[category.value]['name']}) ║
║ 严重程度:   {severity.value}                                     ║
║ 优先级:     P{priority}                                         ║
║ 负责人:     {assignee or '未分配'}                              ║
║ 标签:       {tag_str or '无'}                                   ║
╠══════════════════════════════════════════════════════════════════╣
║ 标题: {title}                                                    ║
╠══════════════════════════════════════════════════════════════════╣
║ 描述:                                                            ║
║ {description}                                                    ║
╚══════════════════════════════════════════════════════════════════╝
"""


def validate_bug_report(data: Dict[str, Any]) -> Dict[str, str]:
    """
    验证 BUG 报告数据
    
    Args:
        data: BUG 报告数据
    
    Returns:
        Dict: 错误信息字典（如果验证通过返回空字典）
    """
    errors = {}
    
    required_fields = ["title", "description", "severity"]
    for field in required_fields:
        if field not in data or not data[field]:
            errors[field] = f"缺少必填字段: {field}"
    
    if "severity" in data and data["severity"] not in [s.value for s in SeverityLevel]:
        errors["severity"] = f"无效的严重程度值: {data['severity']}"
    
    if "impact" in data and data["impact"] not in [i.value for i in ImpactType]:
        errors["impact"] = f"无效的影响类型值: {data['impact']}"
    
    return errors


# 示例用法
if __name__ == "__main__":
    # 示例 1: 分类致命问题
    bug1 = classify_bug(severity="critical", impact="system_crash")
    print(f"分类结果: {bug1.category.value}")
    print(f"优先级: P{bug1.priority}")
    print(f"描述: {bug1.description}")
    
    # 示例 2: 分类一般问题
    bug2 = classify_bug(severity="minor", impact="ui_glitch")
    print(f"\n分类结果: {bug2.category.value}")
    print(f"优先级: P{bug2.priority}")
    
    # 示例 3: 生成格式化报告
    report = format_bug_report(
        bug_id="BUG-001",
        title="应用启动崩溃",
        description="用户报告应用程序启动时立即崩溃，无法使用",
        category=BugCategory.T_A,
        severity=SeverityLevel.CRITICAL,
        priority=1,
        assignee="张三",
        tags=["崩溃", "紧急"]
    )
    print("\n格式化报告:")
    print(report)