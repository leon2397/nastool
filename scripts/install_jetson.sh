#!/bin/bash

# Jetson nastool 安装脚本
echo "================================================"
echo "Jetson nastool v4.0.0 安装脚本"
echo "================================================"
echo

echo "1. 清理pip缓存..."
pip3 cache purge

echo "\n2. 升级pip..."
pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "\n3. 安装构建依赖..."
pip3 install --user build wheel setuptools -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "\n4. 安装核心依赖..."
pip3 install --user pydantic requests paramiko -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "\n5. 安装nastool-common..."
cd ~/nastool-v4.0.0/nastool-common && pip3 install --user --no-build-isolation . -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "\n6. 安装nastool-core..."
cd ~/nastool-v4.0.0/nastool-core && pip3 install --user --no-build-isolation . -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "\n7. 安装nastool-adapters..."
cd ~/nastool-v4.0.0/nastool-adapters && pip3 install --user --no-build-isolation . -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "\n8. 安装nastool-reporters..."
cd ~/nastool-v4.0.0/nastool-reporters && pip3 install --user --no-build-isolation . -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "\n9. 安装nastool-fixes..."
cd ~/nastool-v4.0.0/nastool-fixes && pip3 install --user --no-build-isolation . -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "\n10. 安装nastool-cli..."
cd ~/nastool-v4.0.0/nastool-cli && pip3 install --user --no-build-isolation . -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "\n11. 配置环境变量..."
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc

echo "\n12. 验证安装..."
source ~/.bashrc
echo "\nnastool_core 版本:"
python3 -c "import nastool_core; print(nastool_core.__version__)" 2>&1
echo "\nnastool_cli 版本:"
python3 -c "import nastool_cli; print(nastool_cli.__version__)" 2>&1
echo "\nnastool 命令:"
which nastool || echo "需要重新登录 shell"

echo "\n================================================"
echo "安装完成！"
echo "================================================"
echo "请重新登录或运行: source ~/.bashrc"
echo "然后测试: nastool --version"
