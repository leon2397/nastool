#!/usr/bin/env python3
import socket
import threading

HOST = "192.168.1.102"
OPEN_PORTS = []

def scan_port(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((HOST, port))
        sock.close()
        if result == 0:
            OPEN_PORTS.append(port)
    except:
        pass

print(f"扫描设备 {HOST} 的端口...")

# 扫描常见端口
common_ports = [21, 22, 23, 80, 443, 139, 445, 8000, 8080, 2222, 3000, 5000, 6000, 6001, 7000, 7001, 8081, 9000, 9001, 27017]

threads = []
for port in common_ports:
    t = threading.Thread(target=scan_port, args=(port,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

if OPEN_PORTS:
    print("\n发现开放的端口:")
    for port in sorted(OPEN_PORTS):
        print(f"  - 端口 {port}")
        
    # 尝试获取服务信息
    for port in OPEN_PORTS:
        try:
            service = socket.getservbyport(port)
            print(f"    服务: {service}")
        except:
            pass
else:
    print("\n没有发现开放的端口")
