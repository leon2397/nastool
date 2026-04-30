# NASTool RK Diagnostic Report

**Chip:** RK3588  
**Time:** 2026-04-25 19:37:41  
**RK Score:** 0/100 (Grade F: Critical)  

## Category Scores (RK-weighted)

| Category | Score | Bar |
|----------|-------|-----|
| CheckCategory.SYSTEM | 87 | `#################---` |
| CheckCategory.NETWORK | 87 | `#################---` |
| CheckCategory.STORAGE | 85 | `#################---` |
| CheckCategory.AI | 82 | `################----` |
| CheckCategory.SECURITY | 58 | `###########---------` |
| CheckCategory.NAS | 78 | `###############-----` |
| CheckCategory.USB | 100 | `####################` |

## Thermal Status

**Rating:** Good (max: 58.0C)

| Sensor | Temperature |
|--------|-------------|
| cpu_temperature | 58.0C |
| hdd_temperature | 38.0C |

## Issues

- [!] **System Libs**: System libraries missing: ffi, zlib
- [!] **Dns Coverage**: DNS 2/5: google.com and cloudflare DNS failed
- [!] **Docker Images**: Docker images占用 15.3GB, 建议清理
- [!] **Paddlepaddle Version**: PaddlePaddle 2.6.1 installed, consider upgrading to 3.0
- [!] **Torchserve**: TorchServe installed but not running
- [!] **Ssl Cert**: SSL certificate expires in 18 days (critical!)
- [!] **Ssl Cert Days**: Primary SSL cert expires in 18 days
- [!] **Login Failures**: 3 failed login attempts in last hour (root from 192.168.1.50)
- [!] **Ftp Service**: FTP service not running
- [!] **Webdav Service**: WebDAV service not configured

## All Checks

| Check | Severity | Passed | Value |
|-------|----------|--------|-------|
| Python Version | passed | Y | 3.12 |
| Pip Installed | passed | Y | installed |
| System Libs | warning | N | Missing: ffi, zlib |
| Memory Check | passed | Y | 2.1GB / 32GB (6.6%) |
| Cron Jobs | passed | Y | 8 jobs |
| System Logs | passed | Y | clean |
| Process Count | passed | Y | 127 processes |
| Package Updates | passed | Y | up to date |
| System Disk | passed | Y | NVMe 500GB (250GB used, 50%) |
| Docker Info | info | Y | mock |
| Docker Containers | passed | Y | 12 containers (8 running, 4 stopped) |
| Cpu Temperature | passed | Y | 58C |
| System Uptime | info | Y | mock |
| Internet Access | passed | Y | connected |
| Dns Cache | passed | Y | running |
| Dns Resolve | passed | Y | working |
| Dns Coverage | warning | N | 2 of 5 passed |
| Mtu Size | passed | Y | eth0: 1500 |
| Proxy Config | passed | Y | none |
| Wifi Status | info | Y | not connected |
| Latency Check | info | Y | mock |
| Default Route | passed | Y | configured |
| Port Conflict | passed | Y | 2 available |
| Nas Backend | passed | Y | 120.77.249.3:8000 |
| Network Latency | passed | Y | 32ms |
| Disk Space | passed | Y | 1.2TB / 8TB (15%) |
| Inode Usage | passed | Y | /: 12% inode |
| Io Wait | passed | Y | 2.1% |
| Path Exists | passed | Y | /data:/backup:/media configured |
| Zfs Pool | info | Y | not ZFS |
| Smart Health | passed | Y | PASSED |
| Hdd Temperature | passed | Y | 38C |
| Raid Status | passed | Y | healthy |
| Docker Images | warning | N | 15.3GB |
| Storage Trend | passed | Y | stable |
| Gpu Detected | passed | Y | 1 GPU (NVIDIA) |
| Nvidia Driver Version | passed | Y | 535.54.03 |
| Cuda Version | passed | Y | 12.6 |
| Tensorrt Version | passed | Y | 10.3.0.26 |
| Jetpack Version | passed | Y | 6.1 |
| Rknn Version | passed | Y | 2.5.0 |
| Pytorch Version | passed | Y | 2.4.0+cu124 |
| Onnxruntime Version | passed | Y | 1.19.0 |
| Tensorflow Version | passed | Y | 2.18.0 |
| Keras Version | passed | Y | 3.8.0 |
| Cudnn Version | passed | Y | 9.5.1 |
| Openvino Version | passed | Y | 2024.5.0 |
| Paddlepaddle Version | warning | N | 2.6.1 |
| Triton Server | passed | Y | running |
| Mlflow | passed | Y | v2.16.1 |
| Gpu Memory | passed | Y | 6144MB / 32768MB (18.7%, 26724MB free) |
| Gpu Utilization | passed | Y | GPU0: GPU 35%, Memory 18% |
| Nvidia Container Toolkit | passed | Y | v1.16.2 |
| Onnx Model | passed | Y | 8 models |
| Onednn Version | passed | Y | available via PyTorch |
| Torchserve | warning | N | installed |
| Tensorflow Serving | info | Y | not installed |
| Kubeflow | passed | Y | 12/15 pods running |
| Model Format | passed | Y | 15 models |
| Openssl Version | passed | Y | 3.0.15 |
| Firewall | passed | Y | enabled (iptables) |
| Ssh Root | passed | Y | disabled |
| Ssh Config | passed | Y | secure |
| Fail2Ban | passed | Y | running |
| Clamav | passed | Y | installed |
| Suspicious Ports | passed | Y | clean |
| Selinux | info | Y | Not installed |
| Ssl Cert | warning | N | 18 days |
| Ssl Cert Days | warning | N | 18 days |
| Login Failures | warning | N | 3 failed logins (root, 192.168.1.50) |
| Afp Service | info | Y | not running |
| Backup Status | passed | Y | 3 backup tasks |
| Cron Conflicts | passed | Y | no conflicts |
| Nas Version | passed | Y | DSM 7.2.2-72806 |
| Ftp Service | warning | N | not running |
| Log Disk | passed | Y | 2.1GB used (21%) |
| Media Indexer | passed | Y | running |
| Nfs Service | passed | Y | running |
| Nas Temperature | passed | Y | sda: 38C, hdd: 41C |
| Sftp Service | passed | Y | running |
| Shared Perms | passed | Y | 6 shared folders |
| Smb Service | passed | Y | running |
| Snmp Service | passed | Y | running |
| Ups Status | passed | Y | connected, 85% battery |
| Nas Users | passed | Y | 5 users |
| Webdav Service | warning | N | not configured |
| Usb Devices | info | Y | mock |
| Usb Permissions | info | Y | mock |
| Usb Power | info | Y | mock |
| Usb Storage Mount | info | Y | mock |
