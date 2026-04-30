#!/usr/bin/env python3
"""
昇腾设备测试环境部署脚本
单目录隔离方案 - 不污染系统
"""
import paramiko
import os

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

def upload_file(sftp, local_path, remote_path):
    """上传文件到远程"""
    sftp.put(local_path, remote_path)
    print(f"✓ 上传: {local_path} -> {remote_path}")

def main():
    print("="*60)
    print("    NASTool 昇腾设备测试部署")
    print("    单目录隔离方案 - 不污染系统")
    print("="*60)
    print(f"\n目标设备: {HOST}")
    print(f"安装目录: /root/tool")
    print()
    
    try:
        # 连接设备
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=HOST, username=USERNAME, password=PASSWORD, timeout=15)
        print("✓ SSH连接成功")
        
        # 创建目录结构
        print("\n创建目录结构...")
        dirs = [
            "/root/tool",
            "/root/tool/test_case",
            "/root/tool/bin",
            "/root/tool/dep",
            "/root/tool/log",
            "/root/tool/temp",
            "/root/tool/doc"
        ]
        for d in dirs:
            client.exec_command(f"mkdir -p {d}")
        print("✓ 目录结构创建完成")
        
        # 创建虚拟环境
        print("\n创建Python虚拟环境...")
        stdin, stdout, stderr = client.exec_command("python3 -m venv /root/tool/dep/venv")
        stdout.read()
        stderr.read()
        print("✓ 虚拟环境创建完成")
        
        # 安装依赖
        print("\n安装Python依赖...")
        cmd = "source /root/tool/dep/venv/bin/activate && pip install paramiko requests psutil"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
        output = stdout.read().decode()
        error = stderr.read().decode()
        if "Successfully installed" in output:
            print("✓ 依赖安装完成")
        else:
            print(f"⚠️ 依赖安装可能有问题: {error[:200]}")
        
        # 上传NASTool模块
        print("\n上传NASTool模块...")
        sftp = client.open_sftp()
        
        # 上传每个模块
        modules = ['nastool-common', 'nastool-core', 'nastool-adapters', 
                   'nastool-cli', 'nastool-reporters', 'nastool-fixes']
        
        for module in modules:
            local_path = os.path.join("D:/project/nastool7", module)
            remote_path = f"/root/tool/bin/{module}"
            client.exec_command(f"mkdir -p {remote_path}")
            
            for root, dirs, files in os.walk(local_path):
                for file in files:
                    if file.endswith('.py'):
                        local_file = os.path.join(root, file)
                        rel_path = os.path.relpath(local_file, local_path)
                        remote_file = os.path.join(remote_path, rel_path)
                        sftp.put(local_file, remote_file)
        
        sftp.close()
        print("✓ NASTool模块上传完成")
        
        # 创建一键启动脚本
        print("\n创建启动脚本...")
        run_sh = """#!/bin/bash
TOOL_DIR="/root/tool"

echo "=================================="
echo "  NASTool 测试工具 v4.1"
echo "  昇腾设备诊断测试"
echo "=================================="

# 激活虚拟环境
source $TOOL_DIR/dep/venv/bin/activate

# 设置PYTHONPATH
export PYTHONPATH="$TOOL_DIR/bin/nastool-cli:$TOOL_DIR/bin/nastool-common:$TOOL_DIR/bin/nastool-core:$TOOL_DIR/bin/nastool-adapters:$TOOL_DIR/bin/nastool-reporters:$TOOL_DIR/bin/nastool-fixes"

# 运行诊断
cd $TOOL_DIR/bin/nastool-cli
python -m nastool_cli.main --full --no-color

# 保存JSON结果
mkdir -p $TOOL_DIR/log
python -m nastool_cli.main --full --json --no-color -o $TOOL_DIR/log/diagnosis_result.json

echo ""
echo "✅ 测试完成！"
echo "结果已保存到: $TOOL_DIR/log/"
"""
        sftp = client.open_sftp()
        with sftp.file('/root/tool/run.sh', 'w') as f:
            f.write(run_sh)
        client.exec_command("chmod +x /root/tool/run.sh")
        print("✓ 启动脚本创建完成")
        
        # 创建一键卸载脚本
        print("\n创建卸载脚本...")
        uninstall_sh = """#!/bin/bash
TOOL_DIR="/root/tool"

echo "=================================="
echo "  测试工具 - 一键卸载"
echo "  所有文件将被彻底删除"
echo "  系统不会留下任何痕迹"
echo "=================================="

read -p "确定卸载？(y/n): " ans
if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    rm -rf $TOOL_DIR
    echo "✅ 卸载完成！系统已恢复初始状态。"
else
    echo "❌ 取消卸载。"
fi
"""
        with sftp.file('/root/tool/uninstall.sh', 'w') as f:
            f.write(uninstall_sh)
        client.exec_command("chmod +x /root/tool/uninstall.sh")
        print("✓ 卸载脚本创建完成")
        
        # 创建BUG记录文件
        print("\n创建BUG记录文件...")
        bug_md = """# NASTool 昇腾设备测试 BUG 记录

## 测试环境
- 设备型号: Ascend 310B1 (davinci-mini)
- 操作系统: Ubuntu 22.04 LTS
- 架构: aarch64
- 测试版本: NASTool v4.1
- 测试日期: 

## BUG列表

| 编号 | 严重等级 | 描述 | 发现时间 | 状态 |
|------|---------|------|---------|------|
| BUG-001 | | | | 待确认 |

## 备注

"""
        with sftp.file('/root/tool/doc/bug_list.md', 'w') as f:
            f.write(bug_md)
        sftp.close()
        print("✓ BUG记录文件创建完成")
        
        client.close()
        
        print("\n" + "="*60)
        print("✅ 部署完成！")
        print("="*60)
        print("\n使用方法:")
        print("  ssh root@192.168.1.103")
        print("  cd /root/tool")
        print("  ./run.sh          # 运行测试")
        print("  ./uninstall.sh    # 一键卸载")
        print("\n测试结果保存在: /root/tool/log/")
        print("BUG记录文件: /root/tool/doc/bug_list.md")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 部署失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
