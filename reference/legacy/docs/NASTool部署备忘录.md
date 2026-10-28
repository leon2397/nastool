# NASTool 子目录部署操作记录

## 操作时间
2026年4月27日

## 操作目标
将 NASTool 从主目录移动到子目录 `~/nastool`，解决文件混乱问题。

## 操作步骤

### 1. 创建子目录
```bash
ssh nvidia@192.168.1.123 'mkdir -p ~/nastool'
```

### 2. 移动核心目录
```bash
ssh nvidia@192.168.1.123 'mv ~/nastool ~/nastool-core && mv ~/nastool-agent ~/nastool/ && mv ~/adapters ~/nastool/ && mv ~/core ~/nastool/ && mv ~/fixes ~/nastool/ && mv ~/reporters ~/nastool/ && mv ~/utils ~/nastool/ && mv ~/config ~/nastool/ && mv ~/scripts ~/nastool/ && mv ~/test ~/nastool/ && mv ~/tests ~/nastool/'
```

### 3. 移动脚本文件
```bash
ssh nvidia@192.168.1.123 'mv ~/check.sh ~/nastool/ && mv ~/fix.sh ~/nastool/ && mv ~/start.sh ~/nastool/ && mv ~/monitor.sh ~/nastool/ && mv ~/report.sh ~/nastool/ && mv ~/install.sh ~/nastool/'
```

### 4. 移动配置文件
```bash
ssh nvidia@192.168.1.123 'mv ~/config.py ~/nastool/ && mv ~/constants.py ~/nastool/ && mv ~/logger.py ~/nastool/ && mv ~/messages.py ~/nastool/ && mv ~/exceptions.py ~/nastool/ && mv ~/config.yaml.example ~/nastool/ && mv ~/network_config.yaml ~/nastool/'
```

### 5. 复制完整版本
```bash
ssh nvidia@192.168.1.123 'cp -r ~/nastool-v4.0.0/* ~/nastool/'
```

### 6. 创建启动脚本
```bash
ssh nvidia@192.168.1.123 'cat > ~/nastool/run.sh << "EOF"
#!/bin/bash
# NASTool 启动脚本
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
PYTHONPATH="$SCRIPT_DIR/nastool-cli:$SCRIPT_DIR/nastool-common:$SCRIPT_DIR/nastool-core:$SCRIPT_DIR/nastool-reporters:$SCRIPT_DIR/nastool-fixes:$SCRIPT_DIR/nastool-adapters" python3 -m nastool_cli.main "$@"
EOF
chmod +x ~/nastool/run.sh'
```

## 目录结构
```
~/nastool/
├── nastool-cli/         # 核心命令行工具
├── nastool-core/        # 核心功能模块
├── nastool-common/      # 公共库
├── nastool-reporters/   # 报告生成器
├── nastool-fixes/       # 修复模块
├── nastool-adapters/    # 适配器模块
├── run.sh               # 启动脚本
└── 其他相关文件
```

## 使用方法

### 运行版本信息
```bash
~/nastool/run.sh --version
```

### 运行快速诊断
```bash
~/nastool/run.sh --mock healthy
```

### 运行交互式菜单
```bash
~/nastool/run.sh ui
```

## 优势
1. **目录整洁**：主目录不再混乱
2. **易于维护**：所有组件集中管理
3. **避免冲突**：减少与其他应用的文件冲突
4. **便于备份**：可以直接备份整个目录
5. **版本管理**：不同版本可以部署在不同子目录

## 注意事项
- 确保启动脚本有执行权限
- 首次运行可能需要安装依赖
- 定期备份 `~/nastool` 目录