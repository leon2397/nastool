#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查设备上的SSL证书过期日期"""
import sys
import os
import glob
import subprocess
import datetime


def check_openssl():
    """检查openssl命令是否可用"""
    try:
        result = subprocess.run(
            ["openssl", "version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print(f"OpenSSL 版本: {result.stdout.strip()}")
            return True
        else:
            print("错误: OpenSSL 命令执行失败")
            return False
    except FileNotFoundError:
        print("错误: OpenSSL 命令未找到")
        return False
    except Exception as e:
        print(f"检查 OpenSSL 时出错: {e}")
        return False


def get_cert_paths():
    """获取证书路径"""
    cert_paths = [
        "/etc/ssl/certs/*.pem",
        "/etc/letsencrypt/live/*/fullchain.pem",
        "/root/.acme.sh/*/*.cer",
    ]
    
    # 根据设备类型添加其他可能的路径
    if os.path.exists("/proc/device-tree/model"):
        try:
            with open("/proc/device-tree/model", "rb") as f:
                model = f.read().strip().decode('utf-8', errors='replace').lower()
            
            if 'jetson' in model:
                cert_paths.extend([
                    "/etc/nvidia/ssl/*.pem",
                    "/opt/nvidia/ssl/*.pem"
                ])
            elif 'rockchip' in model:
                cert_paths.extend([
                    "/etc/rockchip/ssl/*.pem"
                ])
        except Exception:
            pass
    
    return cert_paths


def check_cert_expiry(cert_file):
    """检查证书过期日期"""
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_file, "-noout", "-enddate"],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode != 0:
            return None, f"OpenSSL 命令执行失败: {result.stderr.strip()}"
        
        raw = result.stdout.strip()
        if "=" not in raw:
            return None, "无效的日期格式"
        
        date_str = raw.split("=", 1)[1].strip()
        
        # 尝试不同的日期格式
        for fmt in ("%b %d %H:%M:%S %Y %Z", "%b %d %H:%M:%S %Y GMT"):
            try:
                exp = datetime.datetime.strptime(date_str, fmt)
                return exp, None
            except ValueError:
                continue
        
        return None, f"无法解析日期: {date_str}"
        
    except Exception as e:
        return None, f"检查证书时出错: {e}"


def main():
    """主函数"""
    print("=== SSL 证书检查 ===")
    
    # 检查 OpenSSL
    if not check_openssl():
        print("无法继续，缺少 OpenSSL 依赖")
        return
    
    # 获取当前时间
    now = datetime.datetime.now()
    print(f"当前时间: {now}")
    
    # 获取证书路径
    cert_paths = get_cert_paths()
    
    # 检查证书
    found_certs = False
    for pattern in cert_paths:
        cert_files = glob.glob(pattern)
        for cert_file in cert_files:
            found_certs = True
            exp_date, error = check_cert_expiry(cert_file)
            
            if error:
                print(f"错误: {cert_file} -> {error}")
                continue
            
            if exp_date:
                days = (exp_date - now).days
                name = cert_file.split("/")[-2] or cert_file
                status = "过期" if days < 0 else "有效"
                print(f"{name}: {days} 天 ({status})")
    
    if not found_certs:
        print("未找到证书文件")
    
    print("\n检查完成")


if __name__ == "__main__":
    main()
