# -*- coding: utf-8 -*-
"""
fixes/system/check_versions.py - Python/Docker/CUDA 版本检测

功能：
1. 检测 Python 版本（≥3.8 才能运行 AI-NAS）
2. 检测 Docker 版本（用于容器化部署）
3. 检测 CUDA 版本（Jetson 设备 GPU 加速）

返回：
- 版本号
- 是否满足最低要求
- 安装建议
"""

import re
import subprocess
from typing import Optional, Tuple, Dict, Any


# ══════════════════════════════════════════════════════════════════
# 版本要求常量
# ══════════════════════════════════════════════════════════════════

PYTHON_MIN_VERSION = (3, 8)  # AI-NAS 最低 Python 版本
PYTHON_REC_VERSION = (3, 11)  # 推荐 Python 版本

DOCKER_MIN_VERSION = (20, 10)  # Docker 最低版本
DOCKER_REC_VERSION = (26, 0)  # 推荐 Docker 版本

CUDA_MIN_VERSION = (11, 4)  # Jetson 最低 CUDA 版本
CUDA_REC_VERSION = (12, 0)  # 推荐 CUDA 版本


# ══════════════════════════════════════════════════════════════════
# 版本解析工具
# ══════════════════════════════════════════════════════════════════


def parse_version(version_str: str) -> Optional[Tuple[int, ...]]:
    """
    从字符串解析版本号。

    Examples:
        "Python 3.11.4" → (3, 11, 4)
        "Docker version 26.1.3" → (26, 1, 3)
        "CUDA 12.2" → (12, 2)
    """
    if not version_str:
        return None

    # 提取数字部分
    match = re.search(r"(\d+(?:\.\d+)*)", version_str)
    if not match:
        return None

    try:
        parts = match.group(1).split(".")
        return tuple(int(p) for p in parts)
    except (ValueError, TypeError):
        return None


def version_compare(v1: Tuple[int, ...], v2: Tuple[int, ...]) -> int:
    """
    比较两个版本号。

    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2
    """
    # 补齐长度
    max_len = max(len(v1), len(v2))
    v1_padded = v1 + (0,) * (max_len - len(v1))
    v2_padded = v2 + (0,) * (max_len - len(v2))

    for a, b in zip(v1_padded, v2_padded):
        if a < b:
            return -1
        if a > b:
            return 1
    return 0


def meets_requirement(current: Optional[Tuple[int, ...]], minimum: Tuple[int, ...]) -> bool:
    """检查当前版本是否满足最低要求"""
    if current is None:
        return False
    return version_compare(current, minimum) >= 0


# ══════════════════════════════════════════════════════════════════
# Python 版本检测
# ══════════════════════════════════════════════════════════════════


def check_python_version() -> Dict[str, Any]:
    """
    检测 Python 版本。

    Returns:
        {
            "installed": True/False,
            "version": "3.11.4",
            "version_tuple": (3, 11, 4),
            "meets_minimum": True/False,
            "meets_recommended": True/False,
            "status": "ok" / "upgrade_needed" / "not_found",
            "message": "Python 3.11.4 ✓",
            "suggestion": "",
        }
    """
    result = {
        "installed": False,
        "version": None,
        "version_tuple": None,
        "meets_minimum": False,
        "meets_recommended": False,
        "status": "not_found",
        "message": "Python 未安装",
        "suggestion": "请安装 Python 3.8 或更高版本",
    }

    # 尝试获取 Python 版本
    try:
        version_info = subprocess.run(
            ["python3", "--version"], capture_output=True, text=True, timeout=5
        )

        if version_info.returncode != 0:
            # 尝试 python
            version_info = subprocess.run(
                ["python", "--version"], capture_output=True, text=True, timeout=5
            )

        if version_info.returncode == 0:
            output = version_info.stdout.strip() or version_info.stderr.strip()
            result["installed"] = True
            result["version"] = output
            result["version_tuple"] = parse_version(output)

            if result["version_tuple"]:
                # 检查是否满足要求
                result["meets_minimum"] = meets_requirement(
                    result["version_tuple"][:2], PYTHON_MIN_VERSION
                )
                result["meets_recommended"] = meets_requirement(
                    result["version_tuple"][:2], PYTHON_REC_VERSION
                )

                if result["meets_recommended"]:
                    result["status"] = "ok"
                    result["message"] = (
                        f"Python {result['version_tuple'][0]}.{result['version_tuple'][1]} ✓"
                    )
                    result["suggestion"] = ""
                elif result["meets_minimum"]:
                    result["status"] = "ok"
                    result["message"] = (
                        f"Python {result['version_tuple'][0]}.{result['version_tuple'][1]} ✓（推荐 3.11+）"
                    )
                    result["suggestion"] = "建议升级到 Python 3.11+ 以获得更好性能"
                else:
                    result["status"] = "upgrade_needed"
                    v = result["version_tuple"]
                    result["message"] = f"Python {v[0]}.{v[1]} ✗（需要 ≥3.8）"
                    result["suggestion"] = "请升级到 Python 3.8 或更高版本"
            else:
                result["message"] = f"Python 已安装，但无法解析版本: {output}"
                result["status"] = "unknown"

    except subprocess.TimeoutExpired:
        result["message"] = "Python 检测超时"
        result["status"] = "timeout"
    except FileNotFoundError:
        result["message"] = "Python 未安装"
        result["status"] = "not_found"
    except Exception as e:
        result["message"] = f"Python 检测出错: {e}"
        result["status"] = "error"

    return result


# ══════════════════════════════════════════════════════════════════
# Docker 版本检测
# ══════════════════════════════════════════════════════════════════


def check_docker_version() -> Dict[str, Any]:
    """
    检测 Docker 版本。

    Returns:
        与 check_python_version() 相同格式
    """
    result = {
        "installed": False,
        "version": None,
        "version_tuple": None,
        "meets_minimum": False,
        "meets_recommended": False,
        "status": "not_found",
        "message": "Docker 未安装",
        "suggestion": "请安装 Docker 20.10 或更高版本",
    }

    try:
        version_info = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True, timeout=5
        )

        if version_info.returncode == 0:
            output = version_info.stdout.strip()
            result["installed"] = True
            result["version"] = output
            result["version_tuple"] = parse_version(output)

            if result["version_tuple"]:
                result["meets_minimum"] = meets_requirement(
                    result["version_tuple"][:2], DOCKER_MIN_VERSION
                )
                result["meets_recommended"] = meets_requirement(
                    result["version_tuple"][:2], DOCKER_REC_VERSION
                )

                if result["meets_recommended"]:
                    result["status"] = "ok"
                    v = result["version_tuple"]
                    result["message"] = f"Docker {v[0]}.{v[1]} ✓"
                    result["suggestion"] = ""
                elif result["meets_minimum"]:
                    result["status"] = "ok"
                    v = result["version_tuple"]
                    result["message"] = f"Docker {v[0]}.{v[1]} ✓（推荐 26.0+）"
                    result["suggestion"] = "建议升级到 Docker 26.0+"
                else:
                    result["status"] = "upgrade_needed"
                    v = result["version_tuple"]
                    result["message"] = f"Docker {v[0]}.{v[1]} ✗（需要 ≥20.10）"
                    result["suggestion"] = "请升级 Docker 到 20.10 或更高版本"
            else:
                result["message"] = f"Docker 已安装，但无法解析版本: {output}"
                result["status"] = "unknown"

    except subprocess.TimeoutExpired:
        result["message"] = "Docker 检测超时"
        result["status"] = "timeout"
    except FileNotFoundError:
        result["message"] = "Docker 未安装"
        result["status"] = "not_found"
    except Exception as e:
        result["message"] = f"Docker 检测出错: {e}"
        result["status"] = "error"

    return result


# ══════════════════════════════════════════════════════════════════
# CUDA 版本检测
# ══════════════════════════════════════════════════════════════════


def check_cuda_version() -> Dict[str, Any]:
    """
    检测 CUDA 版本（Jetson 设备）。

    检测方法：
    1. nvcc --version（CUDA 编译器）
    2. nvidia-smi（NVIDIA 驱动）
    3. cat /usr/local/cuda/version.txt

    Returns:
        与 check_python_version() 相同格式
    """
    result = {
        "installed": False,
        "version": None,
        "version_tuple": None,
        "meets_minimum": False,
        "meets_recommended": False,
        "status": "not_found",
        "message": "CUDA 未安装",
        "suggestion": "Jetson 设备建议安装 CUDA 11.4+",
        "gpu_info": None,
    }

    # 方法 1: nvcc --version
    try:
        nvcc_info = subprocess.run(["nvcc", "--version"], capture_output=True, text=True, timeout=5)

        if nvcc_info.returncode == 0:
            output = nvcc_info.stdout.strip()
            # 解析 "release 12.2" 或 "Cuda compilation tools, release 12.2"
            match = re.search(r"release\s+(\d+(?:\.\d+)*)", output)
            if match:
                result["installed"] = True
                result["version"] = f"CUDA {match.group(1)}"
                result["version_tuple"] = parse_version(match.group(1))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    except Exception as e:
        pass  # TODO: 添加日志

    # 方法 2: nvidia-smi（如果 nvcc 没找到）
    if not result["installed"]:
        try:
            smi_info = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)

            if smi_info.returncode == 0:
                output = smi_info.stdout
                # 解析 "CUDA Version: 12.2"
                match = re.search(r"CUDA Version:\s*(\d+(?:\.\d+)*)", output)
                if match:
                    result["installed"] = True
                    result["version"] = f"CUDA {match.group(1)}"
                    result["version_tuple"] = parse_version(match.group(1))

                # 提取 GPU 信息
                gpu_match = re.search(r"GPU\s+\d+:\s*(.+?)\s+\(", output)
                if gpu_match:
                    result["gpu_info"] = gpu_match.group(1).strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        except Exception as e:
            pass  # TODO: 添加日志

    # 方法 3: /usr/local/cuda/version.txt
    if not result["installed"]:
        try:
            with open("/usr/local/cuda/version.txt", "r") as f:
                content = f.read()
                match = re.search(r"CUDA\s+Version\s+(\d+(?:\.\d+)*)", content)
                if match:
                    result["installed"] = True
                    result["version"] = f"CUDA {match.group(1)}"
                    result["version_tuple"] = parse_version(match.group(1))
        except (FileNotFoundError, PermissionError):
            pass
        except Exception as e:
            pass  # TODO: 添加日志

    # 评估版本
    if result["installed"] and result["version_tuple"]:
        result["meets_minimum"] = meets_requirement(result["version_tuple"][:2], CUDA_MIN_VERSION)
        result["meets_recommended"] = meets_requirement(
            result["version_tuple"][:2], CUDA_REC_VERSION
        )

        v = result["version_tuple"]
        if result["meets_recommended"]:
            result["status"] = "ok"
            result["message"] = f"CUDA {v[0]}.{v[1]} ✓"
            result["suggestion"] = ""
        elif result["meets_minimum"]:
            result["status"] = "ok"
            result["message"] = f"CUDA {v[0]}.{v[1]} ✓（推荐 12.0+）"
            result["suggestion"] = "建议升级到 CUDA 12.0+"
        else:
            result["status"] = "upgrade_needed"
            result["message"] = f"CUDA {v[0]}.{v[1]} ✗（需要 ≥11.4）"
            result["suggestion"] = "请升级 CUDA 到 11.4 或更高版本"

    return result


# ══════════════════════════════════════════════════════════════════
# 综合检测入口
# ══════════════════════════════════════════════════════════════════


def check_all_versions() -> Dict[str, Dict[str, Any]]:
    """
    综合检测 Python + Docker + CUDA 版本。

    Returns:
        {
            "python": {...},
            "docker": {...},
            "cuda": {...},
        }
    """
    return {
        "python": check_python_version(),
        "docker": check_docker_version(),
        "cuda": check_cuda_version(),
    }


def get_deployment_readiness() -> Dict[str, Any]:
    """
    检查部署就绪状态。

    Returns:
        {
            "ready": True/False,
            "python_ok": True/False,
            "docker_ok": True/False,
            "cuda_ok": True/False,  # CUDA 可选
            "issues": ["Python 版本过低", ...],
            "suggestions": ["请升级 Python", ...],
        }
    """
    versions = check_all_versions()

    issues = []
    suggestions = []

    python_ok = versions["python"]["meets_minimum"]
    docker_ok = versions["docker"]["meets_minimum"]
    cuda_ok = versions["cuda"]["meets_minimum"] or not versions["cuda"]["installed"]  # CUDA 可选

    if not python_ok:
        issues.append(f"Python: {versions['python']['message']}")
        suggestions.append(versions["python"]["suggestion"])

    if not docker_ok:
        issues.append(f"Docker: {versions['docker']['message']}")
        suggestions.append(versions["docker"]["suggestion"])

    # CUDA 是可选的，但如果有安装但不满足要求，给出警告
    if versions["cuda"]["installed"] and not versions["cuda"]["meets_minimum"]:
        issues.append(f"CUDA: {versions['cuda']['message']}（可选）")
        suggestions.append(versions["cuda"]["suggestion"])

    return {
        "ready": python_ok and docker_ok,
        "python_ok": python_ok,
        "docker_ok": docker_ok,
        "cuda_ok": cuda_ok,
        "issues": issues,
        "suggestions": suggestions,
        "versions": versions,
    }


# ══════════════════════════════════════════════════════════════════
# SSH 远程检测（用于 nastools GUI）
# ══════════════════════════════════════════════════════════════════


def check_remote_versions(ssh_client) -> Dict[str, Dict[str, Any]]:
    """
    通过 SSH 检测远程设备的版本。

    Args:
        ssh_client: SSH 连接对象（需有 exec 方法）

    Returns:
        与 check_all_versions() 相同格式
    """
    result = {
        "python": {
            "installed": False,
            "version": None,
            "version_tuple": None,
            "meets_minimum": False,
            "meets_recommended": False,
            "status": "not_found",
            "message": "Python 未安装",
            "suggestion": "请安装 Python 3.8 或更高版本",
        },
        "docker": {
            "installed": False,
            "version": None,
            "version_tuple": None,
            "meets_minimum": False,
            "meets_recommended": False,
            "status": "not_found",
            "message": "Docker 未安装",
            "suggestion": "请安装 Docker 20.10 或更高版本",
        },
        "cuda": {
            "installed": False,
            "version": None,
            "version_tuple": None,
            "meets_minimum": False,
            "meets_recommended": False,
            "status": "not_found",
            "message": "CUDA 未安装",
            "suggestion": "Jetson 设备建议安装 CUDA 11.4+",
            "gpu_info": None,
        },
    }

    if not ssh_client:
        return result

    # Python 检测
    try:
        ec, out, _ = ssh_client.exec("python3 --version 2>&1 || python --version 2>&1", timeout=5)
        if ec == 0 and out.strip():
            result["python"]["installed"] = True
            result["python"]["version"] = out.strip()
            result["python"]["version_tuple"] = parse_version(out)

            if result["python"]["version_tuple"]:
                result["python"]["meets_minimum"] = meets_requirement(
                    result["python"]["version_tuple"][:2], PYTHON_MIN_VERSION
                )
                result["python"]["meets_recommended"] = meets_requirement(
                    result["python"]["version_tuple"][:2], PYTHON_REC_VERSION
                )

                v = result["python"]["version_tuple"]
                if result["python"]["meets_minimum"]:
                    result["python"]["status"] = "ok"
                    result["python"]["message"] = f"Python {v[0]}.{v[1]} ✓"
                    result["python"]["suggestion"] = ""
                else:
                    result["python"]["status"] = "upgrade_needed"
                    result["python"]["message"] = f"Python {v[0]}.{v[1]} ✗（需要 ≥3.8）"
                    result["python"]["suggestion"] = "请升级到 Python 3.8+"
    except Exception as e:
        pass  # TODO: 添加日志

    # Docker 检测
    try:
        ec, out, _ = ssh_client.exec("docker --version 2>&1", timeout=5)
        if ec == 0 and out.strip():
            result["docker"]["installed"] = True
            result["docker"]["version"] = out.strip()
            result["docker"]["version_tuple"] = parse_version(out)

            if result["docker"]["version_tuple"]:
                result["docker"]["meets_minimum"] = meets_requirement(
                    result["docker"]["version_tuple"][:2], DOCKER_MIN_VERSION
                )
                result["docker"]["meets_recommended"] = meets_requirement(
                    result["docker"]["version_tuple"][:2], DOCKER_REC_VERSION
                )

                v = result["docker"]["version_tuple"]
                if result["docker"]["meets_minimum"]:
                    result["docker"]["status"] = "ok"
                    result["docker"]["message"] = f"Docker {v[0]}.{v[1]} ✓"
                    result["docker"]["suggestion"] = ""
                else:
                    result["docker"]["status"] = "upgrade_needed"
                    result["docker"]["message"] = f"Docker {v[0]}.{v[1]} ✗（需要 ≥20.10）"
                    result["docker"]["suggestion"] = "请升级到 Docker 20.10+"
    except Exception as e:
        pass  # TODO: 添加日志

    # CUDA 检测
    try:
        ec, out, _ = ssh_client.exec("nvcc --version 2>&1 | grep release", timeout=5)
        if ec == 0 and out.strip():
            match = re.search(r"release\s+(\d+(?:\.\d+)*)", out)
            if match:
                result["cuda"]["installed"] = True
                result["cuda"]["version"] = f"CUDA {match.group(1)}"
                result["cuda"]["version_tuple"] = parse_version(match.group(1))

        # 如果 nvcc 没找到，尝试 nvidia-smi
        if not result["cuda"]["installed"]:
            ec, out, _ = ssh_client.exec("nvidia-smi 2>&1 | grep 'CUDA Version'", timeout=5)
            if ec == 0 and out.strip():
                match = re.search(r"CUDA Version:\s*(\d+(?:\.\d+)*)", out)
                if match:
                    result["cuda"]["installed"] = True
                    result["cuda"]["version"] = f"CUDA {match.group(1)}"
                    result["cuda"]["version_tuple"] = parse_version(match.group(1))

        # 评估 CUDA 版本
        if result["cuda"]["installed"] and result["cuda"]["version_tuple"]:
            result["cuda"]["meets_minimum"] = meets_requirement(
                result["cuda"]["version_tuple"][:2], CUDA_MIN_VERSION
            )
            result["cuda"]["meets_recommended"] = meets_requirement(
                result["cuda"]["version_tuple"][:2], CUDA_REC_VERSION
            )

            v = result["cuda"]["version_tuple"]
            if result["cuda"]["meets_minimum"]:
                result["cuda"]["status"] = "ok"
                result["cuda"]["message"] = f"CUDA {v[0]}.{v[1]} ✓"
                result["cuda"]["suggestion"] = ""
            else:
                result["cuda"]["status"] = "upgrade_needed"
                result["cuda"]["message"] = f"CUDA {v[0]}.{v[1]} ✗（需要 ≥11.4）"
                result["cuda"]["suggestion"] = "请升级到 CUDA 11.4+"
    except Exception as e:
        pass  # TODO: 添加日志

    return result


def get_remote_deployment_readiness(ssh_client) -> Dict[str, Any]:
    """
    通过 SSH 检查远程设备的部署就绪状态。

    Returns:
        与 get_deployment_readiness() 相同格式
    """
    versions = check_remote_versions(ssh_client)

    issues = []
    suggestions = []

    python_ok = versions["python"]["meets_minimum"]
    docker_ok = versions["docker"]["meets_minimum"]
    cuda_ok = versions["cuda"]["meets_minimum"] or not versions["cuda"]["installed"]

    if not python_ok:
        issues.append(f"Python: {versions['python']['message']}")
        suggestions.append(versions["python"]["suggestion"])

    if not docker_ok:
        issues.append(f"Docker: {versions['docker']['message']}")
        suggestions.append(versions["docker"]["suggestion"])

    if versions["cuda"]["installed"] and not versions["cuda"]["meets_minimum"]:
        issues.append(f"CUDA: {versions['cuda']['message']}（可选）")
        suggestions.append(versions["cuda"]["suggestion"])

    return {
        "ready": python_ok and docker_ok,
        "python_ok": python_ok,
        "docker_ok": docker_ok,
        "cuda_ok": cuda_ok,
        "issues": issues,
        "suggestions": suggestions,
        "versions": versions,
    }
