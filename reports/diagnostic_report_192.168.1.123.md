NASTool Diagnostic Report
==================================================
Version: 4.0.0
Time: 2026-04-25 19:37:41

Health Score: 96/100
Total Checks: 90
Passed: 80 | Warnings: 10 | Critical: 0

Detailed Results:
--------------------------------------------------

[PASS] Python Version
  ID: python_version
  Severity: passed
  Message: Python 3.12 meets recommended version

[PASS] Pip Installed
  ID: pip_installed
  Severity: passed
  Message: pip installed: pip 24.3 from /usr/lib/python3.12

[WARN] System Libs
  ID: system_libs
  Severity: warning
  Message: System libraries missing: ffi, zlib

[PASS] Memory Check
  ID: memory_check
  Severity: passed
  Message: Memory: 2.1GB / 32GB used (6.6%), 29.9GB available

[PASS] Cron Jobs
  ID: cron_jobs
  Severity: passed
  Message: Scheduled tasks 8, normal

[PASS] System Logs
  ID: system_logs
  Severity: passed
  Message: Last 200 lines of logs clean, no critical errors

[PASS] Process Count
  ID: process_count
  Severity: passed
  Message: Process count 127, normal

[PASS] Package Updates
  ID: package_updates
  Severity: passed
  Message: System up to date

[PASS] System Disk
  ID: system_disk
  Severity: passed
  Message: System disk: NVMe 500GB, 50% used

[PASS] Docker Info
  ID: docker_info
  Severity: info
  Message: Mock result for docker_info

[PASS] Docker Containers
  ID: docker_containers
  Severity: passed
  Message: Docker: 8/12 containers running

[PASS] Cpu Temperature
  ID: cpu_temperature
  Severity: passed
  Message: CPU temperature: 58C (normal)

[PASS] System Uptime
  ID: system_uptime
  Severity: info
  Message: Mock result for system_uptime

[PASS] Internet Access
  ID: internet_access
  Severity: passed
  Message: Internet connection: connected

[PASS] Dns Cache
  ID: dns_cache
  Severity: passed
  Message: DNS cache service: dnsmasq

[PASS] Dns Resolve
  ID: dns_resolve
  Severity: passed
  Message: DNS resolution working: google.com -> 142.250.x.x

[WARN] Dns Coverage
  ID: dns_coverage
  Severity: warning
  Message: DNS 2/5: google.com and cloudflare DNS failed

[PASS] Mtu Size
  ID: mtu_size
  Severity: passed
  Message: eth0: MTU 1500, eth1: MTU 9000 (Jumbo Frame)

[PASS] Proxy Config
  ID: proxy_config
  Severity: passed
  Message: No proxy configured

[PASS] Wifi Status
  ID: wifi_status
  Severity: info
  Message: WiFi not connected or not available

[PASS] Latency Check
  ID: latency_check
  Severity: info
  Message: Mock result for latency_check

[PASS] Default Route
  ID: default_route
  Severity: passed
  Message: Default route configured via eth0

[PASS] Port Conflict
  ID: port_conflict
  Severity: passed
  Message: 2 available ports in 8000-9000 range

[PASS] Nas Backend
  ID: nas_backend
  Severity: passed
  Message: NAS backend reachable: 120.77.249.3:8000

[PASS] Network Latency
  ID: network_latency
  Severity: passed
  Message: Network latency normal, average 32ms, best AliDNS 28ms

[PASS] Disk Space
  ID: disk_space
  Severity: passed
  Message: Primary volume: 1.2TB / 8TB used (15%), 6.8TB free

[PASS] Inode Usage
  ID: inode_usage
  Severity: passed
  Message: Inode usage normal: /: 12%

[PASS] Io Wait
  ID: io_wait
  Severity: passed
  Message: IO Wait 2.1% normal

[PASS] Path Exists
  ID: path_exists
  Severity: passed
  Message: /data:/backup:/media configured

[PASS] Zfs Pool
  ID: zfs_pool
  Severity: info
  Message: Not using ZFS storage (ext4)

[PASS] Smart Health
  ID: smart_health
  Severity: passed
  Message: All SMART checks PASSED (8 drives)

[PASS] Hdd Temperature
  ID: hdd_temperature
  Severity: passed
  Message: HDD temperature 38C (normal range)

[PASS] Raid Status
  ID: raid_status
  Severity: passed
  Message: RAID 5 (4x8TB): all drives online, healthy

[WARN] Docker Images
  ID: docker_images
  Severity: warning
  Message: Docker images占用 15.3GB, 建议清理

[PASS] Storage Trend
  ID: storage_trend
  Severity: passed
  Message: Storage growth trend: stable, +0.5GB/week

[PASS] Gpu Detected
  ID: gpu_detected
  Severity: passed
  Message: NVIDIA GPU detected: Orin

[PASS] Nvidia Driver Version
  ID: nvidia_driver_version
  Severity: passed
  Message: NVIDIA driver 535.54.03 installed

[PASS] Cuda Version
  ID: cuda_version
  Severity: passed
  Message: CUDA 12.6 available

[PASS] Tensorrt Version
  ID: tensorrt_version
  Severity: passed
  Message: TensorRT 10.3.0.26 installed

[PASS] Jetpack Version
  ID: jetpack_version
  Severity: passed
  Message: JetPack 6.1 GA installed

[PASS] Rknn Version
  ID: rknn_version
  Severity: passed
  Message: RKNN Toolkit 2.5.0 installed

[PASS] Pytorch Version
  ID: pytorch_version
  Severity: passed
  Message: PyTorch 2.4.0 with CUDA 12.4 support

[PASS] Onnxruntime Version
  ID: onnxruntime_version
  Severity: passed
  Message: ONNXRuntime 1.19.0 available

[PASS] Tensorflow Version
  ID: tensorflow_version
  Severity: passed
  Message: TensorFlow 2.18.0 (GPU: 1 device)

[PASS] Keras Version
  ID: keras_version
  Severity: passed
  Message: Keras 3.8.0 (backend: tensorflow)

[PASS] Cudnn Version
  ID: cudnn_version
  Severity: passed
  Message: cuDNN 9.5.1 (enabled: True)

[PASS] Openvino Version
  ID: openvino_version
  Severity: passed
  Message: OpenVINO 2024.5.0 (devices: CPU, GPU.0)

[WARN] Paddlepaddle Version
  ID: paddlepaddle_version
  Severity: warning
  Message: PaddlePaddle 2.6.1 installed, consider upgrading to 3.0

[PASS] Triton Server
  ID: triton_server
  Severity: passed
  Message: Triton Server running (models: 3)

[PASS] Mlflow
  ID: mlflow
  Severity: passed
  Message: MLflow 2.16.1 running (experiments: 12)

[PASS] Gpu Memory
  ID: gpu_memory
  Severity: passed
  Message: GPU0: 6144MB / 32768MB (18.7%, 26724MB free)

[PASS] Gpu Utilization
  ID: gpu_utilization
  Severity: passed
  Message: GPU0: GPU 35%, Memory 18%

[PASS] Nvidia Container Toolkit
  ID: nvidia_container_toolkit
  Severity: passed
  Message: nvidia-container-toolkit 1.16.2 installed

[PASS] Onnx Model
  ID: onnx_model
  Severity: passed
  Message: Found 8 ONNX models: resnet50-v2.onnx, yolov8n.onnx, ...

[PASS] Onednn Version
  ID: onednn_version
  Severity: passed
  Message: OneDNN (MKL) via PyTorch available

[WARN] Torchserve
  ID: torchserve
  Severity: warning
  Message: TorchServe installed but not running

[PASS] Tensorflow Serving
  ID: tensorflow_serving
  Severity: info
  Message: TensorFlow Serving not installed (optional)

[PASS] Kubeflow
  ID: kubeflow
  Severity: passed
  Message: Kubeflow running (pods: 12/15)

[PASS] Model Format
  ID: model_format
  Severity: passed
  Message: PyTorch (.pt): 8; ONNX (.onnx): 8; Keras (.h5): 2

[PASS] Openssl Version
  ID: openssl_version
  Severity: passed
  Message: OpenSSL 3.0.15

[PASS] Firewall
  ID: firewall
  Severity: passed
  Message: Firewall enabled (iptables, 12 rules active)

[PASS] Ssh Root
  ID: ssh_root
  Severity: passed
  Message: SSH root login disabled

[PASS] Ssh Config
  ID: ssh_config
  Severity: passed
  Message: SSH configuration secure

[PASS] Fail2Ban
  ID: fail2ban
  Severity: passed
  Message: Fail2ban running

[PASS] Clamav
  ID: clamav
  Severity: passed
  Message: ClamAV: ClamAV 1.4.0/24872

[PASS] Suspicious Ports
  ID: suspicious_ports
  Severity: passed
  Message: No suspicious listening ports detected

[PASS] Selinux
  ID: selinux
  Severity: info
  Message: SELinux not installed (not applicable)

[WARN] Ssl Cert
  ID: ssl_cert
  Severity: warning
  Message: SSL certificate expires in 18 days (critical!)

[WARN] Ssl Cert Days
  ID: ssl_cert_days
  Severity: warning
  Message: Primary SSL cert expires in 18 days

[WARN] Login Failures
  ID: login_failures
  Severity: warning
  Message: 3 failed login attempts in last hour (root from 192.168.1.50)

[PASS] Afp Service
  ID: afp_service
  Severity: info
  Message: AFP service not running (Mac users can use SMB/SFTP)

[PASS] Backup Status
  ID: backup_status
  Severity: passed
  Message: /backup: 245 files; 3 backup tasks configured

[PASS] Cron Conflicts
  ID: cron_conflicts
  Severity: passed
  Message: No scheduled task conflicts detected

[PASS] Nas Version
  ID: nas_version
  Severity: passed
  Message: Synology DSM 7.2.2-72806 Update 2

[WARN] Ftp Service
  ID: ftp_service
  Severity: warning
  Message: FTP service not running

[PASS] Log Disk
  ID: log_disk
  Severity: passed
  Message: Log disk: 2.1GB / 10GB (21%)

[PASS] Media Indexer
  ID: media_indexer
  Severity: passed
  Message: Media indexer service: jellyfin, sonarr, radarr

[PASS] Nfs Service
  ID: nfs_service
  Severity: passed
  Message: NFS service running (8 nfsd processes)

[PASS] Nas Temperature
  ID: nas_temperature
  Severity: passed
  Message: Temperature normal: sda=38C, hdd=41C

[PASS] Sftp Service
  ID: sftp_service
  Severity: passed
  Message: SSH/SFTP service running (3 sshd processes)

[PASS] Shared Perms
  ID: shared_perms
  Severity: passed
  Message: 6 shared folders with proper permissions

[PASS] Smb Service
  ID: smb_service
  Severity: passed
  Message: SMB service running (12 smbd processes)

[PASS] Snmp Service
  ID: snmp_service
  Severity: passed
  Message: SNMP service running

[PASS] Ups Status
  ID: ups_status
  Severity: passed
  Message: UPS connected: APC BR1500G, 85% battery, 45min runtime

[PASS] Nas Users
  ID: nas_users
  Severity: passed
  Message: 5 user accounts (admin, backup, media, guest, worker)

[WARN] Webdav Service
  ID: webdav_service
  Severity: warning
  Message: WebDAV service not configured

[PASS] Usb Devices
  ID: usb_devices
  Severity: info
  Message: Mock result for usb_devices

[PASS] Usb Permissions
  ID: usb_permissions
  Severity: info
  Message: Mock result for usb_permissions

[PASS] Usb Power
  ID: usb_power
  Severity: info
  Message: Mock result for usb_power

[PASS] Usb Storage Mount
  ID: usb_storage_mount
  Severity: info
  Message: Mock result for usb_storage_mount
