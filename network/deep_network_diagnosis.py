#!/usr/bin/env python3
import paramiko
import time

HOST = "192.168.1.103"
USERNAME = "root"
PASSWORD = "linaro123"

def execute_command(client, cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

def main():
    print("="*70)
    print("    昇腾设备网络断网问题深度诊断")
    print("    Target: 192.168.1.103")
    print("="*70)
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(hostname=HOST, username=USERNAME, password=PASSWORD)
        print("\n✓ SSH连接成功")
        
        # ============ 1. 网络接口详细状态 ============
        print("\n" + "="*60)
        print("  1. 网络接口详细状态")
        print("="*60)
        output, _ = execute_command(client, "ip -d link show")
        print(output)
        
        # ============ 2. 网络接口错误统计 ============
        print("\n" + "="*60)
        print("  2. 网络接口错误统计")
        print("="*60)
        output, _ = execute_command(client, "cat /proc/net/dev")
        print(output)
        
        # ============ 3. 网络中断日志 ============
        print("\n" + "="*60)
        print("  3. 网络相关系统日志")
        print("="*60)
        output, _ = execute_command(client, "dmesg | grep -i -E 'eth|net|link|dhcp|network' | tail -30")
        print(output)
        
        # ============ 4. 最近网络事件 ============
        print("\n" + "="*60)
        print("  4. 最近网络事件 (journalctl)")
        print("="*60)
        output, _ = execute_command(client, "journalctl -u NetworkManager 2>/dev/null | tail -20 || journalctl | grep -i 'network\\|eth\\|dhcp' | tail -20")
        print(output)
        
        # ============ 5. TCP连接状态详细 ============
        print("\n" + "="*60)
        print("  5. TCP连接状态")
        print("="*60)
        output, _ = execute_command(client, "ss -tnp state established")
        print(output)
        
        # ============ 6. 网络软中断和队列 ============
        print("\n" + "="*60)
        print("  6. 网络软中断统计")
        print("="*60)
        output, _ = execute_command(client, "cat /proc/net/softnet_stat")
        print("软中断统计:", output)
        
        output, _ = execute_command(client, "cat /proc/sys/net/core/netdev_max_backlog")
        print("\n网络设备最大队列长度:", output)
        
        output, _ = execute_command(client, "cat /proc/sys/net/ipv4/tcp_max_syn_backlog")
        print("TCP SYN队列长度:", output)
        
        # ============ 7. DHCP状态 ============
        print("\n" + "="*60)
        print("  7. DHCP客户端状态")
        print("="*60)
        output, _ = execute_command(client, "dhclient -v 2>&1 | tail -10 || echo 'dhclient not available'")
        print(output)
        
        # ============ 8. 网络连接稳定性测试 ============
        print("\n" + "="*60)
        print("  8. 网络连接稳定性测试 (10次ping)")
        print("="*60)
        output, _ = execute_command(client, "ping -c 10 192.168.1.1")
        print(output)
        
        # ============ 9. DNS解析测试 ============
        print("\n" + "="*60)
        print("  9. DNS解析测试")
        print("="*60)
        output, _ = execute_command(client, "dig @127.0.0.53 www.baidu.com +short 2>/dev/null || nslookup www.baidu.com 2>/dev/null || host www.baidu.com 2>/dev/null || echo 'DNS工具不可用'")
        print(output)
        
        # ============ 10. 网卡驱动信息 ============
        print("\n" + "="*60)
        print("  10. 网卡驱动信息")
        print("="*60)
        output, _ = execute_command(client, "lspci -vv | grep -A 10 -i 'Ethernet controller'")
        print(output)
        
        # ============ 11. 网络配置文件检查 ============
        print("\n" + "="*60)
        print("  11. 网络配置文件检查")
        print("="*60)
        output, _ = execute_command(client, "cat /etc/network/interfaces 2>/dev/null || ls -la /etc/network/")
        print(output)
        
        # ============ 12. 网络服务状态 ============
        print("\n" + "="*60)
        print("  12. 网络服务状态")
        print("="*60)
        output, _ = execute_command(client, "systemctl status network-manager 2>/dev/null || systemctl status networking 2>/dev/null")
        print(output)
        
        # ============ 13. 网络丢包测试 ============
        print("\n" + "="*60)
        print("  13. 网络丢包测试 (外网)")
        print("="*60)
        output, _ = execute_command(client, "ping -c 10 8.8.8.8")
        print(output)
        
        # ============ 14. 网络超时测试 ============
        print("\n" + "="*60)
        print("  14. TCP连接超时测试")
        print("="*60)
        output, _ = execute_command(client, "timeout 5 nc -zv www.baidu.com 80 2>&1 || echo '连接超时或失败'")
        print(output)
        
        # ============ 15. 网络带宽实时测试 ============
        print("\n" + "="*60)
        print("  15. 网络带宽测试")
        print("="*60)
        output, _ = execute_command(client, "curl -s https://www.baidu.com > /dev/null -w '连接时间: %{time_connect}s\\n传输时间: %{time_starttransfer}s\\n总时间: %{time_total}s\\n下载速度: %{speed_download} bytes/sec\\n'")
        print(output)
        
        print("\n" + "="*70)
        print("    网络深度诊断完成")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
