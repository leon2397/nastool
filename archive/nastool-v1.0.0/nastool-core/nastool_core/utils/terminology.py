# -*- coding: utf-8 -*-
"""
nastool/utils/terminology.py - P2 普通人视角优化

功能：术语翻译层
  将工程师术语翻译为普通人能理解的通俗语言

包含：
  - 类别名称翻译（CheckCategory -> 中文日常用语）
  - 检测项翻译（check_id -> 通俗标题 + 解释）
  - 风险等级翻译（low/medium/high -> 可理解的风险描述）
  - 严重程度翻译（CRITICAL/WARNING/PASSED -> 行动导向）
  - 改进建议生成（每个失败检测 -> 原因+操作+效果）
"""

from typing import Optional
from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory


# ══════════════════════════════════════════════════════════════
# 类别名称翻译
# ══════════════════════════════════════════════════════════════

CATEGORY_NAMES = {
    CheckCategory.STORAGE:  "[D] Data Storage",
    CheckCategory.SYSTEM:    "[S] System",
    CheckCategory.NETWORK:   "[N] Network",
    CheckCategory.AI:        "[A] AI Acceleration",
    CheckCategory.SECURITY:  "[X] Security",
    CheckCategory.NAS:       "[N] NAS System",
    CheckCategory.USB:       "[U] USB",  # v5.0.3
}

# 类别简称（用于紧凑显示）
CATEGORY_SHORT = {
    CheckCategory.STORAGE:  "存储",
    CheckCategory.SYSTEM:    "系统",
    CheckCategory.NETWORK:   "网络",
    CheckCategory.AI:        "AI",
    CheckCategory.SECURITY:  "安全",
    CheckCategory.NAS:       "NAS",
    CheckCategory.USB:       "USB",  # v5.0.3
}


# ══════════════════════════════════════════════════════════════
# 检测项术语翻译
# ══════════════════════════════════════════════════════════════

TERMINOLOGY = {
    # ── 存储 ──────────────────────────────────────────────
    "smart_health": {
        "title":     "硬盘健康状态",
        "short":     "硬盘SMART",
        "why":       "硬盘是数据仓库，SMART 是硬盘的自我诊断报告。数值异常意味着硬盘可能即将损坏。",
        "risk_low":  "硬盘已运行多年，有轻微老化迹象，建议留意",
        "risk_high": "硬盘有故障前兆，数据随时可能丢失，请立即备份！",
    },
    "hdd_temperature": {
        "title":     "硬盘温度",
        "short":     "硬盘温度",
        "why":       "硬盘工作温度超过 50°C 会加速老化，超过 60°C 有过热风险。",
        "risk_low":  "温度偏高，建议检查机箱风扇",
        "risk_high": "硬盘过热！高温会导致数据损坏或硬盘永久损坏",
    },
    "raid_status": {
        "title":     "RAID 阵列状态",
        "short":     "RAID阵列",
        "why":       "RAID 用来保护数据安全。阵列降级意味着硬盘已损坏，如果再有一块盘故障，所有数据将丢失。",
        "risk_low":  "RAID 正常，数据显示正常保护状态",
        "risk_high": "RAID 降级！请立即备份数据，更换故障硬盘",
    },
    "storage_trend": {
        "title":     "存储空间趋势",
        "short":     "存储趋势",
        "why":       "如果存储空间持续快速增长，可能会在某天突然用满，导致无法写入新数据。",
        "risk_low":  "存储使用趋势正常",
        "risk_high": "存储空间告急！预计在 X 天后存满，请清理或扩容",
    },
    "docker_images": {
        "title":     "Docker 镜像清理",
        "short":     "Docker镜像",
        "why":       "Docker 镜像会占用大量磁盘空间，删除不用的镜像可以释放空间。",
        "risk_low":  "存在可清理的镜像，释放后可恢复磁盘空间",
        "risk_high": "Docker 镜像占用大量空间，影响系统运行",
    },
    "storage_disk": {
        "title":     "磁盘空间",
        "short":     "磁盘空间",
        "why":       "磁盘空间不足会导致程序无法写入数据，服务中断。",
        "risk_low":  "磁盘空间略低，建议清理",
        "risk_high": "磁盘空间严重不足！程序可能无法正常运行",
    },
    "write_speed": {
        "title":     "磁盘写入速度",
        "short":     "写入速度",
        "why":       "写入速度过慢会影响文件传输和备份效率。",
        "risk_low":  "写入速度正常",
        "risk_high": "写入速度异常，可能是硬盘故障或性能下降",
    },
    "path_exists": {
        "title":     "存储路径",
        "short":     "存储路径",
        "why":       "必要的目录不存在会导致程序无法找到数据。",
        "risk_low":  "部分路径缺失，不影响基本运行",
        "risk_high": "关键存储路径缺失，服务无法启动",
    },
    "inode_usage": {
        "title":     "Inode 使用率",
        "short":     "Inode",
        "why":       "Inode 用尽会导致无法创建新文件，即使磁盘空间充足。",
        "risk_low":  "Inode 使用率偏高",
        "risk_high": "Inode 即将用尽，无法创建新文件",
    },
    "io_wait": {
        "title":     "IO 等待时间",
        "short":     "IO等待",
        "why":       "IO 等待时间高说明磁盘读写是性能瓶颈。",
        "risk_low":  "IO 等待偏高",
        "risk_high": "IO 等待过高，磁盘是性能瓶颈",
    },
    "zfs_pool": {
        "title":     "ZFS 存储池",
        "short":     "ZFS",
        "why":       "ZFS 池状态异常会导致数据不可访问。",
        "risk_low":  "ZFS 池状态正常",
        "risk_high": "ZFS 池异常，数据可能丢失",
    },
    "disk_space": {
        "title":     "磁盘空间",
        "short":     "磁盘",
        "why":       "磁盘空间不足会影响系统运行和数据存储。",
        "risk_low":  "磁盘空间略低",
        "risk_high": "磁盘空间严重不足",
    },

    # ── 系统 ──────────────────────────────────────────────
    "cpu_temperature": {
        "title":     "CPU 温度",
        "short":     "CPU温度",
        "why":       "CPU 过热会导致降频运行甚至自动关机保护。",
        "risk_low":  "CPU 温度略高，建议检查散热器",
        "risk_high": "CPU 过热！可能自动降频或关机",
    },
    "uptime": {
        "title":     "系统运行时间",
        "short":     "运行时间",
        "why":       "长时间不重启会导致内存泄漏和系统变慢。超过 90 天建议重启。",
        "risk_low":  "系统已运行较长时间，建议近期重启",
        "risk_high": "系统已运行超过 90 天，建议尽快重启",
    },
    "docker_containers": {
        "title":     "Docker 容器",
        "short":     "Docker容器",
        "why":       "Docker 容器异常或频繁重启意味着应用可能有问题。",
        "risk_low":  "部分容器状态异常，建议检查日志",
        "risk_high": "有容器停止运行或频繁重启，服务可能受影响",
    },
    "memory_check": {
        "title":     "内存使用率",
        "short":     "内存",
        "why":       "内存不足会导致程序变慢或崩溃。",
        "risk_low":  "内存使用率较高，建议关注",
        "risk_high": "内存严重不足，程序可能出现卡顿或崩溃",
    },
    "python_version": {
        "title":     "Python 版本",
        "short":     "Python",
        "why":       "Python 版本过旧会导致新功能无法使用，且存在安全漏洞。",
        "risk_low":  "Python 版本偏低，建议升级",
        "risk_high": "Python 版本过旧，很多功能无法运行",
    },
    "pip_installed": {
        "title":     "pip 包管理器",
        "short":     "pip",
        "why":       "pip 是安装 Python 工具的包管理器，没有它无法安装依赖。",
        "risk_low":  "pip 未安装，部分工具无法使用",
        "risk_high": "pip 未安装，无法安装必要的 Python 包",
    },
    "system_libs": {
        "title":     "系统依赖库",
        "short":     "系统库",
        "why":       "缺少系统库会导致某些功能无法正常工作。",
        "risk_low":  "缺少部分可选库，不影响核心功能",
        "risk_high": "缺少关键系统库，核心功能受限",
    },
    "system_disk": {
        "title":     "系统盘空间",
        "short":     "系统盘",
        "why":       "系统盘满会导致系统无法启动或更新失败。",
        "risk_low":  "系统盘空间偏低",
        "risk_high": "系统盘即将用满，可能导致系统异常",
    },
    "kernel_version": {
        "title":     "内核版本",
        "short":     "内核",
        "why":       "内核版本过旧可能缺少新功能或存在安全漏洞。",
        "risk_low":  "内核版本偏低",
        "risk_high": "内核版本过旧，建议升级",
    },
    "docker_service": {
        "title":     "Docker 服务状态",
        "short":     "Docker服务",
        "why":       "Docker 服务停止会导致所有容器无法运行。",
        "risk_low":  "Docker 服务未运行",
        "risk_high": "Docker 服务异常，容器无法启动",
    },
    "cron_jobs": {
        "title":     "定时任务列表",
        "short":     "定时任务",
        "why":       "定时任务用于自动执行备份、清理等维护操作。",
        "risk_low":  "定时任务较少",
        "risk_high": "定时任务配置异常",
    },
    "package_updates": {
        "title":     "系统更新",
        "short":     "更新",
        "why":       "系统更新包含安全补丁和新功能，建议定期更新。",
        "risk_low":  "有少量待更新软件包",
        "risk_high": "有大量待更新软件包，存在安全风险",
    },
    "process_count": {
        "title":     "进程数量",
        "short":     "进程",
        "why":       "进程数量过多可能导致系统资源紧张。",
        "risk_low":  "进程数量偏多",
        "risk_high": "进程数量过多，系统资源紧张",
    },
    "system_logs": {
        "title":     "系统日志",
        "short":     "日志",
        "why":       "系统日志可以帮助排查问题，但占用磁盘空间。",
        "risk_low":  "日志文件较多",
        "risk_high": "日志文件过大，占用磁盘空间",
    },
    "system_uptime": {
        "title":     "系统运行时间",
        "short":     "运行时间",
        "why":       "长时间不重启可能导致内存泄漏和系统变慢。",
        "risk_low":  "系统运行时间较长，建议定期重启",
        "risk_high": "系统运行时间过长，建议重启",
    },

    # ── 网络 ──────────────────────────────────────────────
    "internet_access": {
        "title":     "互联网连接",
        "short":     "网络连接",
        "why":       "无法连接外网会导致无法下载更新和同步数据。",
        "risk_low":  "网络连接不稳定",
        "risk_high": "无法连接互联网！无法下载更新",
    },
    "dns_resolve": {
        "title":     "DNS 解析",
        "short":     "DNS解析",
        "why":       "DNS 负责把网址翻译成 IP，无法解析意味着无法访问大多数网站。",
        "risk_low":  "DNS 解析不稳定，部分网站可能无法访问",
        "risk_high": "DNS 解析失败！无法访问任何网站",
    },
    "dns_coverage": {
        "title":     "DNS 配置",
        "short":     "DNS配置",
        "why":       "只配一个 DNS 的话，如果它挂了所有网站都访问不了。",
        "risk_low":  "DNS 配置偏少，建议增加备用 DNS",
        "risk_high": "DNS 配置严重不足，访问可靠性差",
    },
    "nic_speed": {
        "title":     "网卡速率",
        "short":     "网卡速率",
        "why":       "网卡速率过低会导致文件传输非常慢。",
        "risk_low":  "网卡速率偏低，可能是网线或交换机限制",
        "risk_high": "网卡速率异常，可能影响数据传输",
    },
    "nas_backend": {
        "title":     "NAS 后端连接",
        "short":     "NAS连接",
        "why":       "无法连接 NAS 后端意味着无法管理存储和文件。",
        "risk_low":  "NAS 连接延迟偏高",
        "risk_high": "无法连接 NAS 后端！无法访问数据",
    },
    "port_conflict": {
        "title":     "端口冲突",
        "short":     "端口冲突",
        "why":       "两个程序用了同一个端口，后启动的会启动失败。",
        "risk_low":  "存在端口冲突，可能导致部分服务无法启动",
        "risk_high": "关键端口被占用，多个服务无法启动",
    },
    "network_latency": {
        "title":     "网络延迟",
        "short":     "延迟",
        "why":       "网络延迟高会导致远程访问卡顿，文件传输慢。",
        "risk_low":  "网络延迟偏高",
        "risk_high": "网络延迟过高，远程访问体验差",
    },
    "bandwidth": {
        "title":     "网络带宽",
        "short":     "带宽",
        "why":       "带宽不足会影响大文件传输和多人同时访问。",
        "risk_low":  "带宽偏低，高峰期可能拥堵",
        "risk_high": "带宽严重不足，文件传输很慢",
    },
    "mtu_size": {
        "title":     "MTU 数据包大小",
        "short":     "MTU",
        "why":       "MTU 设置不当会导致大文件传输失败或网络不稳定。",
        "risk_low":  "MTU 设置非标准值",
        "risk_high": "MTU 设置错误，可能导致传输失败",
    },
    "proxy_config": {
        "title":     "代理配置",
        "short":     "代理",
        "why":       "代理配置错误会导致部分网络请求失败。",
        "risk_low":  "代理配置存在但未启用",
        "risk_high": "代理配置错误，网络请求可能失败",
    },
    "default_route": {
        "title":     "默认路由",
        "short":     "路由",
        "why":       "没有默认路由的话设备无法访问外网。",
        "risk_low":  "默认路由配置异常",
        "risk_high": "无默认路由，无法访问外网",
    },
    "dns_cache": {
        "title":     "DNS 缓存",
        "short":     "DNS缓存",
        "why":       "DNS 缓存可以加速域名解析，但缓存过期会导致访问异常。",
        "risk_low":  "DNS 缓存未启用",
        "risk_high": "DNS 缓存异常，可能导致域名解析失败",
    },
    "wifi_status": {
        "title":     "WiFi 连接状态",
        "short":     "WiFi",
        "why":       "WiFi 信号弱或不稳定会影响网络质量。",
        "risk_low":  "WiFi 信号一般",
        "risk_high": "WiFi 信号弱或不稳定，建议使用有线连接",
    },

    # ── 安全 ──────────────────────────────────────────────
    "login_failures": {
        "title":     "登录失败检测",
        "short":     "暴力破解",
        "why":       "大量登录失败说明有人在尝试暴力破解密码，非常危险。",
        "risk_low":  "有少量登录失败，可能是用户输错密码",
        "risk_high": "检测到大量登录失败！可能正在遭受黑客攻击",
    },
    "ssl_cert": {
        "title":     "SSL 证书",
        "short":     "SSL证书",
        "why":       "SSL 证书过期后浏览器会显示「不安全」，用户无法正常访问。",
        "risk_low":  "证书将在 30 天内过期，请及时续期",
        "risk_high": "SSL 证书已过期！浏览器会拦截访问",
    },
    "firewall": {
        "title":     "防火墙状态",
        "short":     "防火墙",
        "why":       "防火墙是系统的第一道防线，关掉后任何人都可以直接访问你的设备。",
        "risk_low":  "防火墙部分规则关闭",
        "risk_high": "防火墙已关闭！设备完全暴露在互联网上",
    },
    "selinux": {
        "title":     "SELinux 状态",
        "short":     "SELinux",
        "why":       "SELinux 是 Linux 的额外安全层，关闭后安全性降低。",
        "risk_low":  "SELinux 处于宽松模式",
        "risk_high": "SELinux 已关闭，系统安全性降低",
    },
    "ssh_root": {
        "title":     "SSH Root 登录",
        "short":     "Root登录",
        "why":       "允许 root 直接 SSH 登录是严重安全隐患，黑客可以直接控制你的设备。",
        "risk_low":  "允许 root SSH 登录存在安全隐患",
        "risk_high": "允许 root SSH 登录！请立即禁用，改用普通用户+sudo",
    },
    "ssh_config": {
        "title":     "SSH 配置安全",
        "short":     "SSH配置",
        "why":       "SSH 配置不当会导致安全漏洞，如弱加密算法、端口暴露等。",
        "risk_low":  "SSH 配置存在可优化项",
        "risk_high": "SSH 配置存在安全隐患，建议加固",
    },
    "ssl_cert_days": {
        "title":     "SSL 证书有效期",
        "short":     "证书有效期",
        "why":       "证书即将过期需要提前续期，避免服务中断。",
        "risk_low":  "SSL 证书即将过期，请提前续期",
        "risk_high": "SSL 证书即将过期！请立即续期",
    },
    "openssl_version": {
        "title":     "OpenSSL 版本",
        "short":     "OpenSSL",
        "why":       "OpenSSL 版本过旧可能存在安全漏洞。",
        "risk_low":  "OpenSSL 版本偏低，建议升级",
        "risk_high": "OpenSSL 版本过旧，存在已知安全漏洞",
    },
    "fail2ban": {
        "title":     "Fail2ban 入侵防护",
        "short":     "Fail2ban",
        "why":       "Fail2ban 自动封禁暴力破解 IP，是防黑客的重要工具。",
        "risk_low":  "Fail2ban 未启用",
        "risk_high": "Fail2ban 未运行，设备容易被暴力破解",
    },
    "clamav": {
        "title":     "ClamAV 病毒扫描",
        "short":     "ClamAV",
        "why":       "ClamAV 是开源杀毒软件，适合检测上传文件中的恶意软件。",
        "risk_low":  "ClamAV 未安装",
        "risk_high": "ClamAV 服务异常，病毒扫描不可用",
    },
    "suspicious_ports": {
        "title":     "异常端口检测",
        "short":     "异常端口",
        "why":       "检测监听中的异常端口，可能是后门或恶意软件。",
        "risk_low":  "检测到非标准端口",
        "risk_high": "检测到可疑端口，可能存在安全风险",
    },

    # ── AI ─────────────────────────────────────────────────
    "gpu_detected": {
        "title":     "AI 加速芯片",
        "short":     "AI芯片",
        "why":       "没有 AI 加速芯片，所有图像处理都靠 CPU，速度会非常慢。",
        "risk_low":  "未检测到 AI 加速芯片，部分功能速度较慢",
        "risk_high": "AI 加速不可用！所有 AI 功能将无法使用",
    },
    "version_checker": {
        "title":     "版本兼容性",
        "short":     "版本",
        "why":       "版本不兼容会导致功能异常或崩溃。",
        "risk_low":  "部分版本偏低，建议升级",
        "risk_high": "版本严重不兼容，很多功能无法正常工作",
    },

    # ── AI 框架扩展（v5.0.2）────────────────────────────────
    "tensorflow_version": {
        "title":     "TensorFlow 版本",
        "short":     "TensorFlow",
        "why":       "TensorFlow 是最流行的深度学习框架，版本过旧可能存在兼容性问题或安全漏洞。",
        "risk_low":  "TensorFlow 版本偏低，建议升级到最新稳定版",
        "risk_high": "TensorFlow 版本过旧，部分模型无法加载或运行异常",
    },
    "keras_version": {
        "title":     "Keras 版本",
        "short":     "Keras",
        "why":       "Keras 是高级神经网络 API，常与 TensorFlow 配合使用。",
        "risk_low":  "Keras 版本偏低，建议升级",
        "risk_high": "Keras 版本不兼容，模型加载可能失败",
    },
    "cudnn_version": {
        "title":     "cuDNN 版本",
        "short":     "cuDNN",
        "why":       "cuDNN 是 NVIDIA 的深度学习加速库，版本必须与 CUDA 匹配。",
        "risk_low":  "cuDNN 版本偏低，GPU 加速效率不高",
        "risk_high": "cuDNN 版本不匹配，GPU 加速可能无法使用",
    },
    "openvino_version": {
        "title":     "OpenVINO 版本",
        "short":     "OpenVINO",
        "why":       "OpenVINO 是 Intel 的 AI 推理优化工具，适合 CPU 推理加速。",
        "risk_low":  "OpenVINO 版本偏低",
        "risk_high": "OpenVINO 版本过旧，部分模型无法优化",
    },
    "paddlepaddle_version": {
        "title":     "PaddlePaddle 版本",
        "short":     "PaddlePaddle",
        "why":       "PaddlePaddle 是百度开源的深度学习框架，在国内使用广泛。",
        "risk_low":  "PaddlePaddle 版本偏低",
        "risk_high": "PaddlePaddle 版本过旧，模型兼容性差",
    },
    "onednn_version": {
        "title":     "OneDNN 版本",
        "short":     "OneDNN",
        "why":       "OneDNN 是 Intel 的深度神经网络库，可加速 CPU 推理。",
        "risk_low":  "OneDNN 版本偏低",
        "risk_high": "OneDNN 版本过旧，CPU 推理速度慢",
    },
    "gpu_memory": {
        "title":     "GPU 显存使用率",
        "short":     "GPU显存",
        "why":       "GPU 显存不足会导致模型加载失败或推理中断。",
        "risk_low":  "GPU 显存占用较高，建议检查是否有僵尸进程",
        "risk_high": "GPU 显存即将耗尽！模型可能无法运行",
    },
    "gpu_utilization": {
        "title":     "GPU 计算利用率",
        "short":     "GPU利用率",
        "why":       "GPU 利用率低意味着硬件未被充分利用，可能是模型太小或批次太小。",
        "risk_low":  "GPU 利用率偏低，可考虑增加批次大小",
        "risk_high": "GPU 利用率异常低，可能存在性能瓶颈",
    },
    "nvidia_driver_version": {
        "title":     "NVIDIA 驱动版本",
        "short":     "NVIDIA驱动",
        "why":       "NVIDIA 驱动版本决定 GPU 能否正常工作，版本过低会导致 CUDA 不可用。",
        "risk_low":  "NVIDIA 驱动版本偏低",
        "risk_high": "NVIDIA 驱动版本过旧，CUDA/GPU 无法使用",
    },
    "nvidia_container_toolkit": {
        "title":     "NVIDIA Container Toolkit",
        "short":     "Docker GPU",
        "why":       "NVIDIA Container Toolkit 让 Docker 容器能使用 GPU，是容器化 AI 的必需品。",
        "risk_low":  "未安装 NVIDIA Container Toolkit，Docker 容器无法使用 GPU",
        "risk_high": "Docker GPU 支持不可用，容器化 AI 功能受限",
    },
    "triton_server": {
        "title":     "Triton 推理服务器",
        "short":     "Triton",
        "why":       "Triton 是 NVIDIA 的高性能推理服务器，支持多框架模型部署。",
        "risk_low":  "Triton 未运行，推理服务不可用",
        "risk_high": "Triton 服务异常，模型推理中断",
    },
    "torchserve": {
        "title":     "TorchServe 推理服务",
        "short":     "TorchServe",
        "why":       "TorchServe 是 PyTorch 官方的模型服务化工具。",
        "risk_low":  "TorchServe 未运行",
        "risk_high": "TorchServe 服务异常",
    },
    "tensorflow_serving": {
        "title":     "TensorFlow Serving",
        "short":     "TF Serving",
        "why":       "TensorFlow Serving 是 TensorFlow 模型的生产级部署方案。",
        "risk_low":  "TensorFlow Serving 未运行",
        "risk_high": "TF Serving 服务异常，模型推理失败",
    },
    "mlflow": {
        "title":     "MLflow 实验追踪",
        "short":     "MLflow",
        "why":       "MLflow 用于追踪机器学习实验和管理模型版本。",
        "risk_low":  "MLflow 未安装，实验追踪不可用",
        "risk_high": "MLflow 服务异常",
    },
    "kubeflow": {
        "title":     "Kubeflow 平台",
        "short":     "Kubeflow",
        "why":       "Kubeflow 是 Kubernetes 上的机器学习工具包，用于大规模训练和部署。",
        "risk_low":  "Kubeflow 未安装",
        "risk_high": "Kubeflow 服务异常",
    },
    "onnx_model": {
        "title":     "ONNX 模型检测",
        "short":     "ONNX模型",
        "why":       "ONNX 是跨框架模型格式，支持 PyTorch/TensorFlow 等模型互转。",
        "risk_low":  "未检测到 ONNX 模型文件",
        "risk_high": "ONNX 模型文件损坏或格式错误",
    },
    "model_format": {
        "title":     "模型格式检测",
        "short":     "模型格式",
        "why":       "检测常见模型格式（.onnx/.pt/.h5/.pb 等）的存在和完整性。",
        "risk_low":  "模型文件较少或格式单一",
        "risk_high": "模型文件缺失或损坏，推理可能失败",
    },

    # ── NAS ───────────────────────────────────────────────
    "dsm_version": {
        "title":     "NAS 系统版本",
        "short":     "NAS版本",
        "why":       "NAS 系统版本过旧可能存在安全漏洞，且无法使用新功能。",
        "risk_low":  "NAS 系统版本偏低，建议升级",
        "risk_high": "NAS 系统版本过旧，存在已知安全漏洞",
    },
    "user_stats": {
        "title":     "用户账号安全",
        "short":     "用户账号",
        "why":       "弱密码账号是入侵的主要入口，必须强制修改。",
        "risk_low":  "存在使用默认密码的账号",
        "risk_high": "存在弱密码账号！极易被黑客入侵",
    },
    "shared_perms": {
        "title":     "共享权限设置",
        "short":     "共享权限",
        "why":       "权限设置过大可能导致数据泄露给不应该看到的人。",
        "risk_low":  "部分共享权限偏大",
        "risk_high": "存在权限过大的共享目录，数据可能泄露",
    },
    "ups_status": {
        "title":     "UPS 不间断电源",
        "short":     "UPS电源",
        "why":       "UPS 可以在停电时保护设备突然断电造成数据丢失。",
        "risk_low":  "UPS 未连接或状态异常",
        "risk_high": "UPS 未连接！停电时设备会突然断电，可能损坏数据",
    },
    "log_disk": {
        "title":     "日志存储空间",
        "short":     "日志空间",
        "why":       "日志目录占用太大会导致磁盘空间不足。",
        "risk_low":  "日志目录占用较高，建议定期清理",
        "risk_high": "日志目录占用过大，影响磁盘空间",
    },
    "cron_conflicts": {
        "title":     "定时任务冲突",
        "short":     "定时任务",
        "why":       "多个定时任务同时运行会占用大量资源或导致数据冲突。",
        "risk_low":  "存在可能的定时任务冲突",
        "risk_high": "存在定时任务冲突，可能导致服务异常",
    },
    "nas_version": {
        "title":     "NAS 系统版本",
        "short":     "NAS版本",
        "why":       "NAS 系统版本过旧可能存在安全漏洞，且无法使用新功能。",
        "risk_low":  "NAS 系统版本偏低，建议升级",
        "risk_high": "NAS 系统版本过旧，存在已知安全漏洞",
    },
    "nas_users": {
        "title":     "NAS 用户账号",
        "short":     "NAS用户",
        "why":       "用户账号过多或存在弱密码会增加安全风险。",
        "risk_low":  "用户账号较多，建议定期审计",
        "risk_high": "存在弱密码账号，极易被入侵",
    },
    "nas_temperature": {
        "title":     "NAS 设备温度",
        "short":     "NAS温度",
        "why":       "NAS 设备温度过高会影响稳定性和硬盘寿命。",
        "risk_low":  "NAS 温度偏高，建议检查散热",
        "risk_high": "NAS 温度过高！可能影响硬盘寿命",
    },
    "media_indexer": {
        "title":     "媒体索引服务",
        "short":     "媒体索引",
        "why":       "媒体索引服务负责建立照片和视频的缩略图和搜索索引。",
        "risk_low":  "媒体索引服务未运行",
        "risk_high": "媒体索引服务异常，照片搜索和缩略图不可用",
    },
    "backup_status": {
        "title":     "备份状态",
        "short":     "备份",
        "why":       "定期备份是数据安全的最后一道防线。",
        "risk_low":  "备份任务较久未执行",
        "risk_high": "备份任务失败或长期未执行，数据有丢失风险",
    },
    "smb_service": {
        "title":     "SMB 文件共享",
        "short":     "SMB",
        "why":       "SMB 是 Windows 网络共享协议，NAS 的核心服务之一。",
        "risk_low":  "SMB 服务未运行",
        "risk_high": "SMB 服务异常，Windows 无法访问共享文件夹",
    },
    "nfs_service": {
        "title":     "NFS 文件共享",
        "short":     "NFS",
        "why":       "NFS 是 Linux/Unix 网络共享协议，常用于虚拟机和容器存储。",
        "risk_low":  "NFS 服务未运行",
        "risk_high": "NFS 服务异常，Linux 客户端无法挂载共享",
    },
    "afp_service": {
        "title":     "AFP 文件共享",
        "short":     "AFP",
        "why":       "AFP 是 Apple 文件协议，用于 Mac 电脑访问 NAS。",
        "risk_low":  "AFP 服务未运行",
        "risk_high": "AFP 服务异常，Mac 无法访问 Time Machine 备份",
    },
    "ftp_service": {
        "title":     "FTP 文件传输",
        "short":     "FTP",
        "why":       "FTP 是传统文件传输协议，用于远程文件上传下载。",
        "risk_low":  "FTP 服务未运行",
        "risk_high": "FTP 服务异常，无法进行文件传输",
    },
    "sftp_service": {
        "title":     "SFTP 安全传输",
        "short":     "SFTP",
        "why":       "SFTP 是基于 SSH 的安全文件传输协议。",
        "risk_low":  "SFTP 服务未运行",
        "risk_high": "SFTP 服务异常，安全文件传输不可用",
    },
    "webdav_service": {
        "title":     "WebDAV 服务",
        "short":     "WebDAV",
        "why":       "WebDAV 支持 HTTP 方式访问文件，适合远程访问和移动端同步。",
        "risk_low":  "WebDAV 服务未运行",
        "risk_high": "WebDAV 服务异常，远程文件访问受限",
    },
    "snmp_service": {
        "title":     "SNMP 监控服务",
        "short":     "SNMP",
        "why":       "SNMP 用于远程监控设备状态，常与监控系统集成。",
        "risk_low":  "SNMP 服务未运行",
        "risk_high": "SNMP 服务异常，监控数据无法采集",
    },

    # ─── USB checks (v5.0.3) ───────────────────────────────────────
    "usb_devices": {
        "title":     "USB 设备检测",
        "short":     "USB设备",
        "why":       "USB 口常接外置存储、UPS、摄像头等设备，需确认已识别。",
        "risk_low":  "未检测到 USB 设备",
        "risk_high": "USB 设备未被识别，可能松动或驱动缺失",
    },
    "usb_storage_mount": {
        "title":     "USB 存储挂载",
        "short":     "USB存储",
        "why":       "USB 外置硬盘若未挂载则无法访问数据。",
        "risk_low":  "未挂载 USB 存储",
        "risk_high": "USB 存储挂载失败",
    },
    "usb_permissions": {
        "title":     "USB 设备权限",
        "short":     "USB权限",
        "why":       "用户若无 plugdev 组权限，无法正常访问 USB 设备。",
        "risk_low":  "用户不在 plugdev 组",
        "risk_high": "USB 设备权限不足，应用程序无法访问",
    },
    "usb_power": {
        "title":     "USB 端口供电",
        "short":     "USB供电",
        "why":       "过流可能损坏设备或数据，供电不足则设备无法正常工作。",
        "risk_low":  "USB 电源数据不可用",
        "risk_high": "USB 过流保护触发！可能损坏设备",
    },
}


# ══════════════════════════════════════════════════════════════
# 风险等级翻译
# ══════════════════════════════════════════════════════════════

RISK_LABELS = {
    "low":    ("⚪ 低风险",    "安全，可放心操作"),
    "medium": ("[!] 中风险",    "有风险，请仔细阅读说明"),
    "high":   ("🔴 高风险",    "危险，可能影响数据，请谨慎操作"),
}


# ══════════════════════════════════════════════════════════════
# 严重程度翻译
# ══════════════════════════════════════════════════════════════

SEVERITY_LABELS = {
    CheckSeverity.PASSED:  ("[OK] 正常",      "此项没有问题"),
    CheckSeverity.INFO:    ("ℹ 提示",      "供参考的信息"),
    CheckSeverity.WARNING: ("[!] 警告",      "需要关注，建议处理"),
    CheckSeverity.CRITICAL:("🔴 严重",      "必须立即处理，否则有风险"),
}


# ══════════════════════════════════════════════════════════════
# 核心翻译函数
# ══════════════════════════════════════════════════════════════

def translate_result(result: CheckResult) -> dict:
    """
    将 CheckResult 翻译为普通人能理解的信息。

    Returns:
        dict with keys:
          - friendly_title: 通俗标题
          - friendly_message: 通俗描述（当前状态）
          - friendly_reason: 为什么这很重要
          - friendly_action: 应该怎么做
          - friendly_severity: 行动导向的严重程度
          - friendly_fix: 修复建议（如果有）
    """
    t = TERMINOLOGY.get(result.check_id, {})
    sev_label, sev_desc = SEVERITY_LABELS.get(result.severity, ("❓ 未知", ""))

    # 生成通俗消息
    if result.passed:
        msg = f"{result.current}，一切正常"
    elif result.severity == CheckSeverity.CRITICAL:
        t_reason = t.get("risk_high", "此项存在严重问题")
        msg = f"{result.current}。{t_reason}"
    elif result.severity == CheckSeverity.WARNING:
        t_reason = t.get("risk_low", "此项需要关注")
        msg = f"{result.current}。{t_reason}"
    else:
        msg = result.message

    # 修复建议
    fix_hint = ""
    if result.fix_available and result.fix_description:
        fix_hint = f"[!] 修复建议：{result.fix_description}"

    return {
        "friendly_title":    t.get("title", result.title),
        "friendly_short":   t.get("short", result.title),
        "friendly_message":  msg,
        "friendly_reason":  t.get("why", ""),
        "friendly_severity": sev_label,
        "friendly_severity_desc": sev_desc,
        "friendly_fix":     fix_hint,
        "current":          result.current,
        "expected":         result.expected,
    }


def translate_category(category: CheckCategory) -> str:
    """将 CheckCategory 翻译为普通人能理解的名称"""
    return CATEGORY_NAMES.get(category, str(category.value))


def translate_risk(risk: str) -> tuple:
    """将 risk 翻译为 (label, description)"""
    return RISK_LABELS.get(risk, ("⚫ 未知风险", "风险未知"))


def score_urgency(result: CheckResult) -> str:
    """
    根据检查结果判断紧急程度（用于建议排序）
    Returns: "now" / "soon" / "later"
    """
    if result.severity == CheckSeverity.CRITICAL:
        return "now"
    elif result.severity == CheckSeverity.WARNING:
        return "soon"
    return "later"


def generate_suggestions(results: list) -> list:
    """
    为一组 CheckResult 生成普通人能理解的改进建议列表。

    Returns:
        list of dict {
            "urgency": "now" / "soon" / "later",
            "title": str,           # 通俗标题
            "problem": str,          # 问题是什么
            "why_matters": str,     # 为什么重要
            "action": str,          # 具体操作步骤
            "risk": str,            # 操作风险
            "benefit": str,         # 预期效果
            "check_id": str,        # 对应检测ID
            "fix_available": bool,
        }
    """
    suggestions = []

    for r in results:
        if r.passed and r.severity != CheckSeverity.INFO:
            continue  # 跳过正常的检测

        t = TERMINOLOGY.get(r.check_id, {})
        urgency = score_urgency(r)

        # 确定问题描述
        if r.severity == CheckSeverity.CRITICAL:
            problem = t.get("risk_high", r.message)
        elif r.severity == CheckSeverity.WARNING:
            problem = t.get("risk_low", r.message)
        else:
            problem = r.message

        # 生成操作步骤
        action = _build_action(r)
        risk_label, risk_desc = translate_risk(r.fix_risk if r.fix_risk else "medium")

        # 预期效果
        benefit = _build_benefit(r)

        suggestions.append({
            "urgency":       urgency,
            "title":         t.get("title", r.title),
            "problem":       problem,
            "why_matters":   t.get("why", ""),
            "action":        action,
            "risk":          risk_label,
            "risk_desc":     risk_desc,
            "benefit":       benefit,
            "check_id":      r.check_id,
            "fix_available": r.fix_available,
            "fix_description": r.fix_description or "",
        })

    # 按紧急程度排序
    order = {"now": 0, "soon": 1, "later": 2}
    suggestions.sort(key=lambda s: order.get(s["urgency"], 2))
    return suggestions


def _build_action(result: CheckResult) -> str:
    """为检测结果生成具体的操作步骤"""
    fix_id = result.fix_id or ""

    actions = {
        # DNS 相关
        "dns_resolve":       "运行 python arm_diagnose.py --fix，然后选择 DNS 修复",
        "dns_coverage":      "编辑 /etc/resolv.conf，手动追加 nameserver 8.8.8.8 和 223.5.5.5",
        # 网络相关
        "internet_access":   "检查路由器网络连接，联系网络运营商",
        "nic_speed":        "检查网线和交换机，尝试更换网线或端口",
        "port_conflict":    "查找占用端口的进程：lsof -i:端口号，然后停止对应服务",
        # 安全相关
        "login_failures":   "启用 fail2ban 自动封禁攻击者 IP，或更换 SSH 端口",
        "ssl_cert":         "登录 NAS 管理界面，找到证书管理，手动续期",
        "firewall":         "运行 ufw enable 开启防火墙，或在 NAS 管理界面开启",
        "ssh_root":         "编辑 /etc/ssh/sshd_config，设 PermitRootLogin no，然后重启 sshd",
        # 存储相关
        "smart_health":     "立即备份重要数据！然后用 smartctl -t 进行全面自检，考虑更换硬盘",
        "hdd_temperature":  "清理机箱灰尘，检查风扇运转，添加机箱风扇",
        "raid_status":      "立即备份数据！更换故障硬盘，等待 RAID 重建完成",
        "storage_trend":    "清理不需要的大文件，或添加新硬盘扩容",
        "log_disk":         "运行 find /var/log -name '*.gz' -mtime +30 -delete 清理旧日志",
        # 系统相关
        "cpu_temperature":  "清理散热器灰尘，重新涂抹硅脂，检查风扇转速",
        "uptime":           "在 NAS 管理界面执行重启，或运行 sudo reboot",
        "docker_containers":"运行 docker ps -a 查看停止的容器，根据需要重启或修复",
        # NAS 相关
        "dsm_version":      "在 NAS 管理界面检查更新，下载并安装最新版 DSM",
        "user_stats":       "登录 NAS 管理界面，找到用户管理，强制修改弱密码",
        "shared_perms":     "登录 NAS 管理界面，找到共享文件夹权限设置，收紧权限",
        "ups_status":       "检查 UPS 连接线和 USB 线，确保 NUT 服务正在运行",
    }

    if fix_id in actions:
        return actions[fix_id]

    # 通用建议
    if result.fix_available and result.fix_description:
        return f"运行 python arm_diagnose.py --fix 选择对应修复项：{result.fix_description}"
    return f"请检查「{result.title}」：{result.message}"


def _build_benefit(result: CheckResult) -> str:
    """生成预期效果描述"""
    benefits = {
        "dns_resolve":       "可以正常访问互联网",
        "internet_access":   "可以下载更新和同步数据",
        "login_failures":   "防止黑客入侵和数据泄露",
        "ssl_cert":         "浏览器不再显示安全警告，用户正常访问",
        "firewall":         "防止未经授权的访问",
        "ssh_root":         "防止黑客通过 root 账号控制设备",
        "smart_health":     "提前发现硬盘故障，避免数据丢失",
        "raid_status":      "数据得到 RAID 保护，避免同时损坏多块硬盘",
        "cpu_temperature":  "CPU 性能恢复正常，不再降频",
        "uptime":           "系统性能恢复，减少内存泄漏问题",
    }
    return benefits.get(result.fix_id or result.check_id, "提升系统整体健康度和安全性")
