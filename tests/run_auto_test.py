#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NASTool 自动化真机测试执行脚本 - Round 1
按照 BUG 闭环管理规范执行测试（非交互式版本）
"""

import sys
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

# 设置Windows终端UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 配置
TARGET_DEVICE = "192.168.1.123"
TARGET_PORT = 8000
ROUND = 1
BUGS_FILE = f"bugs_round_{ROUND}.json"
REPORT_FILE = f"test_report_round_{ROUND}.md"

# 使用ASCII字符替代Unicode符号
CHECK_MARK = "[OK]"
CROSS_MARK = "[X]"
ARROW_MARK = "[>]"
WARN_MARK = "[!]"


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step_num, description):
    """打印步骤"""
    print(f"\n[Step {step_num}] {description}")
    print("-" * 40)


def check_environment():
    """Step 1: 环境检查"""
    print_step(1, "环境检查")

    env_info = {
        "test_date": datetime.now().isoformat(),
        "target_device": TARGET_DEVICE,
        "target_port": TARGET_PORT,
        "python_version": sys.version,
        "working_directory": os.getcwd()
    }

    # 检查网络连通性
    print(f"检查目标设备连通性: {TARGET_DEVICE}")
    try:
        result = subprocess.run(
            ["ping", "-n", "2", TARGET_DEVICE],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"  {CHECK_MARK} 设备可连通")
            env_info["ping_status"] = "success"
        else:
            print(f"  {CROSS_MARK} 设备不可连通")
            env_info["ping_status"] = "failed"
    except Exception as e:
        print(f"  {CROSS_MARK} Ping检查失败: {e}")
        env_info["ping_status"] = f"error: {e}"

    # 检查HTTP API
    print(f"\n检查HTTP API: http://{TARGET_DEVICE}:{TARGET_PORT}")
    try:
        import urllib.request
        import socket
        url = f"http://{TARGET_DEVICE}:{TARGET_PORT}"
        req = urllib.request.Request(url, method='HEAD')
        try:
            response = urllib.request.urlopen(req, timeout=5)
            print(f"  {CHECK_MARK} HTTP API可访问 (状态: {response.status})")
            env_info["http_status"] = "success"
        except urllib.error.HTTPError as e:
            print(f"  {WARN_MARK} HTTP返回错误 (状态: {e.code})，但服务正在运行")
            env_info["http_status"] = f"http_error: {e.code}"
        except socket.timeout:
            print(f"  {CROSS_MARK} HTTP API连接超时")
            env_info["http_status"] = "timeout"
        except Exception as e:
            print(f"  {CROSS_MARK} HTTP API检查失败: {e}")
            env_info["http_status"] = f"error: {e}"
    except ImportError:
        print(f"  {WARN_MARK} 无法导入urllib，跳过HTTP检查")
        env_info["http_status"] = "skipped"

    return env_info


def run_tests():
    """Step 2: 执行测试"""
    print_step(2, "执行测试")

    # 运行 test_remote.py
    print("运行远程检测测试...")
    print("-" * 40)

    test_results = {
        "start_time": datetime.now().isoformat(),
        "output": "",
        "errors": "",
        "return_code": None
    }

    try:
        result = subprocess.run(
            [sys.executable, "test_remote.py"],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8',
            errors='replace'
        )
        test_results["output"] = result.stdout
        test_results["errors"] = result.stderr
        test_results["return_code"] = result.returncode
        test_results["end_time"] = datetime.now().isoformat()

        # 打印输出
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)

        if result.returncode == 0:
            print(f"\n{CHECK_MARK} 测试执行完成")
        else:
            print(f"\n{CROSS_MARK} 测试执行失败 (返回码: {result.returncode})")

    except subprocess.TimeoutExpired:
        print(f"\n{CROSS_MARK} 测试执行超时")
        test_results["errors"] = "Timeout"
    except Exception as e:
        print(f"\n{CROSS_MARK} 测试执行异常: {e}")
        test_results["errors"] = str(e)

    return test_results


def init_bugs_file(env_info):
    """初始化BUG记录文件"""
    bugs_data = {
        "round": ROUND,
        "test_date": datetime.now().strftime("%Y-%m-%d"),
        "target_device": TARGET_DEVICE,
        "environment": env_info,
        "bugs": [],
        "summary": {
            "total_bugs": 0,
            "p0": 0,
            "p1": 0,
            "p2": 0,
            "p3": 0
        }
    }

    with open(BUGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(bugs_data, f, indent=2, ensure_ascii=False)

    print(f"\n{CHECK_MARK} BUG记录文件已创建: {BUGS_FILE}")
    return bugs_data


def add_bug(bugs_data, bug_info):
    """添加BUG记录"""
    bug_id = f"BUG-R{ROUND}-{len(bugs_data['bugs']) + 1:03d}"
    bug_record = {
        "bug_id": bug_id,
        "timestamp": datetime.now().isoformat(),
        "status": "open",
        **bug_info
    }

    bugs_data["bugs"].append(bug_record)

    # 更新统计
    severity = bug_info.get("severity", "P3")
    bugs_data["summary"]["total_bugs"] += 1
    if severity.lower() in bugs_data["summary"]:
        bugs_data["summary"][severity.lower()] += 1

    # 保存文件
    with open(BUGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(bugs_data, f, indent=2, ensure_ascii=False)

    print(f"\n{CHECK_MARK} BUG已记录: {bug_id}")
    return bug_id


def generate_report(env_info, test_results, bugs_data):
    """Step 4: 生成测试报告"""
    print_step(4, "生成测试报告")

    report = f"""# NASTool 真机测试报告 - Round {ROUND}

> 测试日期: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 目标设备: {TARGET_DEVICE}:{TARGET_PORT}
> 测试状态: {'已完成' if test_results.get('return_code') == 0 else '执行异常'}

---

## 一、环境信息

| 项目 | 值 |
|------|-----|
| 目标设备 | {TARGET_DEVICE} |
| 目标端口 | {TARGET_PORT} |
| Python版本 | {env_info.get('python_version', 'N/A').split()[0] if env_info.get('python_version') else 'N/A'} |
| 工作目录 | {env_info.get('working_directory', 'N/A')} |
| Ping状态 | {env_info.get('ping_status', 'N/A')} |
| HTTP状态 | {env_info.get('http_status', 'N/A')} |

---

## 二、测试执行结果

| 项目 | 值 |
|------|-----|
| 开始时间 | {test_results.get('start_time', 'N/A')} |
| 结束时间 | {test_results.get('end_time', 'N/A')} |
| 返回码 | {test_results.get('return_code', 'N/A')} |
| 执行状态 | {'成功' if test_results.get('return_code') == 0 else '失败'} |

### 测试输出

```
{test_results.get('output', '无输出')[:2000]}
```

### 错误输出

```
{test_results.get('errors', '无错误')[:1000]}
```

---

## 三、BUG汇总

| 严重等级 | 数量 |
|----------|------|
| P0 - 阻断性 | {bugs_data['summary']['p0']} |
| P1 - 关键 | {bugs_data['summary']['p1']} |
| P2 - 次要 | {bugs_data['summary']['p2']} |
| P3 - 改进 | {bugs_data['summary']['p3']} |
| **总计** | **{bugs_data['summary']['total_bugs']}** |

### BUG清单

"""

    if bugs_data["bugs"]:
        for bug in bugs_data["bugs"]:
            report += f"""#### {bug['bug_id']} [{bug['severity']}] {bug['title']}

- **模块**: {bug['module']}
- **严重等级**: {bug['severity']}
- **状态**: {bug['status']}
- **记录时间**: {bug['timestamp']}
- **描述**: {bug['description']}

"""
            if bug.get('reproduce_steps'):
                report += f"- **复现步骤**: {', '.join(bug['reproduce_steps'])}\n"
            if bug.get('expected_result'):
                report += f"- **预期结果**: {bug['expected_result']}\n"
            if bug.get('actual_result'):
                report += f"- **实际结果**: {bug['actual_result']}\n"
            report += "\n"
    else:
        report += "本轮测试未发现BUG。\n"

    report += f"""
---

## 四、下一轮测试建议

"""

    if bugs_data['summary']['p0'] > 0:
        report += "- **优先级**: 高 - 存在P0级阻断性BUG，建议修复后立即进行回归测试\n"
    elif bugs_data['summary']['p1'] > 0:
        report += "- **优先级**: 中 - 存在P1级关键BUG，建议修复后进行回归测试\n"
    elif bugs_data['summary']['total_bugs'] > 0:
        report += "- **优先级**: 低 - 存在P2/P3级BUG，可安排后续迭代修复\n"
    else:
        report += "- **优先级**: 常规 - 本轮测试未发现BUG，可按计划进行下一轮功能测试\n"

    report += f"""
---

## 五、附件

- BUG记录文件: `{BUGS_FILE}`
- 详细日志: 请查看控制台输出

---

*报告生成时间: {datetime.now().isoformat()}*
"""

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"{CHECK_MARK} 测试报告已生成: {REPORT_FILE}")
    return report


def main():
    """主函数"""
    print_header(f"NASTool 真机测试 - Round {ROUND}")
    print(f"目标设备: {TARGET_DEVICE}:{TARGET_PORT}")
    print(f"BUG记录文件: {BUGS_FILE}")
    print(f"测试报告文件: {REPORT_FILE}")
    print("\n按照 BUG 闭环管理规范执行测试")
    print("测试期间发现BUG请记录，不要中断测试去修复！")

    # Step 1: 环境检查
    env_info = check_environment()

    # 初始化BUG记录文件
    bugs_data = init_bugs_file(env_info)

    # Step 2: 执行测试
    print("\n" + "=" * 60)
    print("开始执行测试...")
    test_results = run_tests()

    # Step 3: 自动分析测试结果中的潜在BUG
    print_step(3, "分析测试结果")
    
    # 从测试输出中分析潜在问题
    output = test_results.get('output', '')
    errors = test_results.get('errors', '')
    
    potential_issues = []
    
    # 检查常见的错误模式
    if 'Error' in output or 'Exception' in output:
        potential_issues.append({
            "type": "exception",
            "description": "测试输出中包含异常信息"
        })
    
    if '无法连接' in output or 'connection' in output.lower():
        potential_issues.append({
            "type": "connection",
            "description": "检测到连接问题"
        })
    
    if '超时' in output or 'timeout' in output.lower():
        potential_issues.append({
            "type": "timeout",
            "description": "检测到超时问题"
        })
    
    if test_results.get('return_code') != 0:
        potential_issues.append({
            "type": "execution_failed",
            "description": f"测试脚本返回非零状态码: {test_results.get('return_code')}"
        })
    
    if potential_issues:
        print(f"{WARN_MARK} 发现 {len(potential_issues)} 个潜在问题:")
        for issue in potential_issues:
            print(f"  - [{issue['type']}] {issue['description']}")
        print(f"\n请检查测试输出，如有BUG请手动记录到 {BUGS_FILE}")
    else:
        print(f"{CHECK_MARK} 测试执行正常，未发现明显问题")

    # Step 4: 生成报告
    report = generate_report(env_info, test_results, bugs_data)

    # 完成
    print_header("测试完成")
    print(f"{CHECK_MARK} BUG记录: {BUGS_FILE}")
    print(f"{CHECK_MARK} 测试报告: {REPORT_FILE}")
    print(f"{CHECK_MARK} BUG总数: {bugs_data['summary']['total_bugs']}")
    
    if potential_issues:
        print(f"\n{WARN_MARK} 注意: 测试过程中发现潜在问题，请检查报告和日志")
    
    print("\n请按照闭环管理规范:")
    print("1. 检查测试输出，如有BUG请手动添加到bugs_round_1.json")
    print("2. 修复所有记录的BUG")
    print("3. 安排下一轮测试")


if __name__ == "__main__":
    main()
