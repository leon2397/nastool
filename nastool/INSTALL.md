# nastool v3.0.7 安装指南

## 快速安装

### Linux / 群晖 / 威联通 / Jetson

```bash
# 1. 解压
unzip nastool-v3.0.7.zip

# 2. 进入目录
cd nastool-v3.0.7

# 3. 安装依赖（可选，部分功能需要）
pip3 install pyyaml psutil

# 4. 运行
python3 arm_diagnose.py
```

### Windows

```cmd
# 1. 解压
# 右键 → 解压到当前文件夹

# 2. 双击运行
start.bat
```

---

## 依赖要求

- **Python**: 3.8 或更高版本
- **可选依赖**:
  - `pyyaml` - 配置文件解析
  - `psutil` - 系统监控
  - `reportlab` - PDF 报告生成

安装依赖：
```bash
pip3 install pyyaml psutil reportlab
```

---

## 快速开始

```bash
# 快速诊断（30秒）
python3 arm_diagnose.py

# 完整诊断（5分钟）
python3 arm_diagnose.py --full

# 指定 NAS 类型
python3 arm_diagnose.py --nas synology  # 群晖
python3 arm_diagnose.py --nas qnap      # 威联通
python3 arm_diagnose.py --nas ai_nas    # AI-NAS

# 预设场景
python3 arm_diagnose.py --scene quick   # 快速
python3 arm_diagnose.py --scene daily   # 日常
python3 arm_diagnose.py --scene full    # 完整
python3 arm_diagnose.py --scene ai      # AI专项
python3 arm_diagnose.py --scene storage # 存储专项
```

---

## 支持的 NAS 设备

| NAS 类型 | ARM 机型 | 芯片 |
|----------|----------|------|
| 群晖 Synology | DS223j, DS223, DS120j | RTD1619B, Armada |
| 威联通 QNAP | TS-231P3, TS-431KX | AL-314, AL-514 |
| AI-NAS | 所有 ARM 设备 | 所有 ARM 芯片 |

---

## 常见问题

### Q: 提示 Python 未找到？
A: 请先安装 Python 3.8+
- 群晖: 套件中心搜索 Python
- 威联通: App Center 搜索 Python

### Q: 提示权限不足？
A: 使用管理员权限运行
```bash
sudo python3 arm_diagnose.py
```

### Q: 如何注册到 AI-NAS 后端？
A: 运行以下命令
```bash
python3 arm_diagnose.py --register --backend https://your-nas-server.com
```

---

## 技术支持

- 文档: https://docs.ai-nas.com/nastool
- 问题反馈: https://github.com/your-repo/nastool/issues
