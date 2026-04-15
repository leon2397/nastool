@echo off
chcp 65001 >nul
:: setup_usb_gadget_pc.bat — PC 端 USB Gadget 网络配置
:: V3.0-beta
:: 
:: 在 Windows PC 上自动配置 USB RNDIS 虚拟网卡 IP，
:: 使 PC 能通过 USB 线直接访问 ARM 设备的 USB Gadget IP。
::
:: 用法: setup_usb_gadget_pc.bat
:: 需要管理员权限（右击 -> 以管理员身份运行）
::
setlocal EnableDelayedExpansion

set "DEVICE_IP=192.168.58.2"
set "PC_IP=192.168.58.1"
set "NETMASK=255.255.255.0"

echo ==========================================
echo   USB Gadget PC 端配置向导
echo   目标设备 IP: %DEVICE_IP%
echo ==========================================
echo.

:: ── 检查管理员权限 ──────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 需要管理员权限！
    echo 请右击本文件，选择「以管理员身份运行」
    pause
    exit /b 1
)

:: ── 步骤 1：找到 USB RNDIS 适配器 ───────────────────────
echo [步骤1] 查找 USB RNDIS 网络适配器...
echo.

:: 列出所有网络适配器，找 RNDIS 相关
powershell -Command "Get-NetAdapter | Where-Object {$_.InterfaceDescription -match 'RNDIS|USB Ethernet|Linux-USB|gadget'} | Select-Object Name, InterfaceDescription, Status, MacAddress | Format-Table -AutoSize"

if %errorlevel% neq 0 (
    powershell -Command "Get-NetAdapter | Format-Table -AutoSize"
    echo.
    echo [提示] 未找到 USB RNDIS 适配器？
    echo   - 请确保设备端 USB Gadget 已启用（运行 setup_usb_gadget.py）
    echo   - 请确保 USB 线已连接设备
    echo   - 等待 Windows 安装驱动（可能需要几分钟）
    echo   - 或者手动在设备管理器中查找「USB RNDIS」适配器
    echo.
    set /p user_iface=请输入适配器名称（直接回车退出）: 
    if "!user_iface!"=="" exit /b 0
    set "ADAPTER=!user_iface!"
) else (
    :: 获取第一个 RNDIS 适配器名称
    for /f "delims=" %%i in ('powershell -Command "$a = Get-NetAdapter^| Where-Object {$_.InterfaceDescription -match 'RNDIS|USB Ethernet|Linux-USB|gadget'}^| Select-Object -First 1 -ExpandProperty Name; if ($a) { Write-Output $a }"') do set "ADAPTER=%%i"
)

if not defined ADAPTER (
    echo [错误] 未能找到 USB RNDIS 适配器
    echo.
    echo 请尝试以下步骤：
    echo   1. 确认设备端已运行 setup_usb_gadget.py
    echo   2. 重新插拔 USB 线
    echo   3. 在设备管理器中查找"USB RNDIS"或"USB Ethernet"
    echo   4. 手动运行: setup_usb_gadget_pc.bat
    pause
    exit /b 1
)

echo [找到] 适配器: %ADAPTER%
echo.

:: ── 步骤 2：配置 IP 地址 ───────────────────────────────
echo [步骤2] 配置 IP 地址...
echo   PC IP:   %PC_IP%
echo   子网掩码: %NETMASK%
echo.

:: 检查是否已有 IP
powershell -Command "Get-NetIPAddress -InterfaceAlias '%ADAPTER%' -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty IPAddress" > temp_ip.txt
set /p CURRENT_IP=<temp_ip.txt
del temp_ip.txt >nul 2>&1

if defined CURRENT_IP (
    echo [已有] 当前 IP: %CURRENT_IP%
    if "!CURRENT_IP!"=="%PC_IP%" (
        echo [OK] IP 已正确，无需修改
    ) else (
        echo [修改] 更新为 %PC_IP%...
        netsh interface ip set address name="%ADAPTER%" static %PC_IP% %NETMASK% >nul 2>&1
        if %errorlevel% equ 0 (
            echo [OK] IP 已更新
        ) else (
            echo [错误] IP 配置失败，请手动设置
            echo   在「网络连接」中右键适配器 -> 属性 -> IPv4 -> 使用下面 IP:
            echo   IP: %PC_IP%
            echo   子网掩码: %NETMASK%
        )
    )
) else (
    echo [设置] 分配静态 IP...
    netsh interface ip set address name="%ADAPTER%" static %PC_IP% %NETMASK% >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] IP 已设置为 %PC_IP%
    ) else (
        echo [错误] IP 配置失败（需要管理员权限）
        echo   请手动设置:
        echo   IP: %PC_IP%
        echo   子网掩码: %NETMASK%
    )
)

echo.

:: ── 步骤 3：测试连接 ─────────────────────────────────
echo [步骤3] 测试连接...
echo   ping -n 3 -w 1000 %DEVICE_IP%
echo.

ping -n 3 -w 1000 %DEVICE_IP% > temp_ping.txt 2>&1
findstr /i "TTL" temp_ping.txt >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo   [成功] USB Gadget 连接正常！
    echo ==========================================
    echo.
    echo   PC IP:  %PC_IP%
    echo   设备 IP: %DEVICE_IP%
    echo.
    echo   下一步：在 PC 上运行以下命令访问设备：
    echo  .
    echo   ssh root@%DEVICE_IP%
    echo   scp file.txt root@%DEVICE_IP%:/tmp/
    echo.
    del temp_ping.txt >nul 2>&1
) else (
    echo.
    echo ==========================================
    echo   [失败] 无法 ping 通 %DEVICE_IP%
    echo ==========================================
    echo.
    echo   请检查：
    echo   1. [设备端] 是否运行了 setup_usb_gadget.py --enable
    echo   2. [USB 线] 是否插好（建议用数据线，非充电线）
    echo   3. [设备端] USB Gadget 是否绑定到正确的控制器
    echo   4. [Windows] USB RNDIS 驱动是否安装成功
    echo.
    echo   设备端诊断: 
    echo   dmesg ^| grep gadget
    echo   ls /sys/kernel/config/usb_gadget/
    echo   ip addr show usb0
    echo.
    type temp_ping.txt
    del temp_ping.txt >nul 2>&1
)

pause
