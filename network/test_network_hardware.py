#!/usr/bin/env python3
import paramiko
import time

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

def execute_command(client, cmd, description):
    """执行命令并输出结果"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.read().decode('utf-8', errors='ignore').strip()
    error = stderr.read().decode('utf-8', errors='ignore').strip()
    
    if output:
        print(output)
    if error:
        print(f"\n警告: {error}")
    
    return output, error

def main():
    print("="*70)
    print("    昇腾设备网络硬件详细测试")
    print("    Target: 192.168.1.103")
    print("="*70)
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)
        print("\n✓ SSH连接成功")
        
        # 1. 网卡硬件信息
        execute_command(client, "lspci | grep -i net", "1. 网卡硬件信息 (PCI)")
        
        # 2. 网络接口详细信息
        execute_command(client, "ip addr show", "2. 网络接口详细信息")
        
        # 3. 网络接口统计
        execute_command(client, "ip -s link show", "3. 网络接口统计信息")
        
        # 4. 路由表
        execute_command(client, "ip route show", "4. 路由表")
        
        # 5. DNS配置
        execute_command(client, "cat /etc/resolv.conf", "5. DNS配置")
        
        # 6. 网络连接状态
        execute_command(client, "ss -tuln", "6. 网络连接状态")
        
        # 7. 网卡驱动信息
        execute_command(client, "ethtool eth0 2>/dev/null || ethtool eth1 2>/dev/null || echo 'ethtool not available'", "7. 网卡驱动及速率信息")
        
        # 8. ping测试
        print("\n" + "="*60)
        print("  8. 网络连通性测试")
        print("="*60)
        for target in ["192.168.1.1", "8.8.8.8", "baidu.com"]:
            stdin, stdout, stderr = client.exec_command(f"ping -c 3 {target}")
            output = stdout.read().decode('utf-8', errors='ignore')
            print(f"\n--- Ping {target} ---")
            print(output)
        
        # 9. 带宽测试（使用curl）
        print("\n" + "="*60)
        print("  9. 带宽测试")
        print("="*60)
        cmd = "curl -s https://speed.hetzner.de/100MB.bin -o /dev/null -w '下载速度: %{speed_download} bytes/sec\n'"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
        output = stdout.read().decode('utf-8', errors='ignore')
        print(output)
        
        # 10. 网络延迟测试
        print("\n" + "="*60)
        print("  10. 网络延迟测试")
        print("="*60)
        cmd = "for i in 1 2 3; do curl -s -w '延迟: %{time_total}s\n' -o /dev/null http://www.baidu.com; done"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        output = stdout.read().decode('utf-8', errors='ignore')
        print(output)
        
        # 11. ARP缓存
        execute_command(client, "arp -a", "11. ARP缓存表")
        
        # 12. 网络接口队列长度
        execute_command(client, "cat /proc/net/softnet_stat", "12. 网络软中断统计")
        
        # 13. TCP连接统计
        execute_command(client, "cat /proc/net/sockstat", "13. Socket统计")
        
        # 14. 网络命名空间
        execute_command(client, "ip netns list 2>/dev/null || echo '无额外网络命名空间'", "14. 网络命名空间")
        
        # 15. 防火墙状态
        execute_command(client, "ufw status 2>/dev/null || iptables -L 2>/dev/null | head -20 || echo '防火墙状态未知'", "15. 防火墙状态")
        
        print("\n" + "="*70)
        print("    网络硬件测试完成")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
