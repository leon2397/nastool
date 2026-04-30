#!/usr/bin/env python3
"""
jetson_install.py -- 一键安装 NASArm Toolkit 到 Jetson
用法: python3 jetson_install.py

全程自动：检测路径 -> 补丁 arm_server.py -> 复制 nastool -> 重启服务 -> 诊断报告
"""

import os, sys, subprocess, shutil, time

# ============ 配置 ============
JETSON_HOME = os.path.expanduser("~")  # /home/nvidia
NAS_BASE = os.path.join(JETSON_HOME, "AI-NAS-Media-Manager", "arm", "qizhiainas", "arm")
USB_MOUNTS = ["/media/nvidia", "/media/$USER", "/mnt", "/run/media/nvidia"]
NASTOOL_SRC_ALT = os.path.join(JETSON_HOME, "Desktop")  # U盘可能挂载在这里

# ============ 彩色输出 ============
C = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m", "end": "\033[0m"}


def log(msg, status="ok"):
    icons = {"ok": "[OK]", "info": "ℹ", "warn": "[!]", "fail": "[X]"}
    color = {"ok": "green", "info": "yellow", "warn": "yellow", "fail": "red"}.get(status, "green")
    print(f"{C[color]}{icons[status]}  {msg}{C['end']}")


def run(cmd, check=True, timeout=30):
    """执行 shell 命令，返回 (returncode, stdout, stderr)"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


# ============ 步骤 1：找 nastool 源码 ============
def find_nastool():
    """找 nastool 目录在哪里（U盘 or Desktop or 当前目录）"""
    # 1. 看 arm_server.py 同级有没有 nastool
    arm_dir = NAS_BASE
    local = os.path.join(arm_dir, "nastool")
    if os.path.isdir(local):
        return local, "Jetson 本地"
    # 2. 看 Desktop 上有没有（U盘挂载点）
    for root in [NASTOOL_SRC_ALT, os.getcwd(), "/mnt/usbstorage"]:
        candidate = os.path.join(root, "nastool")
        if os.path.isdir(candidate):
            return candidate, root
    # 3. 找 arm_server.py 的上级目录里有没有 nastool
    possible = [
        os.path.join(arm_dir, "..", "..", "..", "nastool"),
        os.path.join(JETSON_HOME, "nastool"),
    ]
    for p in possible:
        if os.path.isdir(p):
            return p, p
    return None, None


# ============ 步骤 2：补丁 arm_server.py ============
PATCH_CODE = """
# ============ Admin Endpoints (Auto Pull) ============
import tarfile, shutil, subprocess, urllib.request
from fastapi.responses import FileResponse

def _extract_overwrite(tmp_path, nastool_dir):
    with tarfile.open(tmp_path, "r:gz") as tar:
        members = []
        for member in tar.getmembers():
            name = member.name
            if name.startswith("nastool/"):
                member.name = name[8:]
            elif "/" not in name:
                continue
            members.append(member)
        tar.extractall(nastool_dir, members=members)

@app.post("/admin/update")
async def admin_update(file=None, git_url=None, restart: bool = True, token: str = Query(None)):
    expected_token = os.environ.get("NASTOOL_UPDATE_TOKEN", "nastool-update-secret")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    arm_dir = os.path.dirname(os.path.abspath(__file__))
    nastool_dir = os.path.join(arm_dir, "nastool")
    os.makedirs(nastool_dir, exist_ok=True)
    if file:
        content = await file.read()
        tmp_path = "/tmp/admin_update.tar.gz"
        with open(tmp_path, "wb") as f: f.write(content)
        _extract_overwrite(tmp_path, nastool_dir)
        os.remove(tmp_path)
    elif git_url:
        if os.path.isdir(nastool_dir): shutil.rmtree(nastool_dir)
        subprocess.run(["git", "clone", "--depth=1", git_url, nastool_dir],
                       capture_output=True, text=True, timeout=120, check=True)
    else:
        raise HTTPException(status_code=400, detail="请提供 file 或 git_url")
    diag = os.path.join(nastool_dir, "arm_diagnose.py")
    if not os.path.exists(diag):
        raise HTTPException(status_code=500, detail="arm_diagnose.py 不在目录中")
    if restart:
        async def _r():
            await asyncio.sleep(2); os.environ["NASTOOL_RESTART_PENDING"] = "1"; sys.exit(0)
        asyncio.create_task(_r())
        return {"code": 200, "msg": "更新成功，2秒后重启", "data": {"restart_pending": True}}
    return {"code": 200, "msg": "更新成功", "data": {"files": os.listdir(nastool_dir)}}

@app.post("/admin/pull")
async def admin_pull(backend: str = Query(...), token: str = Query(None)):
    expected_token = os.environ.get("NASTOOL_UPDATE_TOKEN", "nastool-update-secret")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    arm_dir = os.path.dirname(os.path.abspath(__file__))
    nastool_dir = os.path.join(arm_dir, "nastool")
    tmp_path = "/tmp/nastool_pull.tar.gz"
    try:
        urllib.request.urlretrieve(backend, tmp_path)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"下载失败: {e}")
    if os.path.isdir(nastool_dir):
        for item in os.listdir(nastool_dir):
            p = os.path.join(nastool_dir, item)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    os.makedirs(nastool_dir, exist_ok=True)
    _extract_overwrite(tmp_path, nastool_dir)
    os.remove(tmp_path)
    diag = os.path.join(nastool_dir, "arm_diagnose.py")
    if not os.path.exists(diag):
        raise HTTPException(status_code=500, detail="arm_diagnose.py 不在目录中")
    async def _r():
        await asyncio.sleep(2); os.environ["NASTOOL_RESTART_PENDING"] = "1"; sys.exit(0)
    asyncio.create_task(_r())
    return {"code": 200, "msg": "拉取成功，2秒后重启"}

@app.get("/admin/status")
async def admin_status(token: str = Query(None)):
    expected_token = os.environ.get("NASTOOL_UPDATE_TOKEN", "nastool-update-secret")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    arm_dir = os.path.dirname(os.path.abspath(__file__))
    nastool_dir = os.path.join(arm_dir, "nastool")
    diag = os.path.join(nastool_dir, "arm_diagnose.py")
    return {"code": 200, "msg": "ok", "data": {
        "nastool_installed": os.path.isdir(nastool_dir),
        "arm_diagnose_exists": os.path.exists(diag),
        "nastool_dir": nastool_dir,
    }}
# ============ End Admin Endpoints ============
"""


def patch_arm_server():
    arm_server = os.path.join(NAS_BASE, "arm_server.py")
    if not os.path.exists(arm_server):
        log(f"未找到 arm_server.py: {arm_server}", "fail")
        return False
    with open(arm_server, "r", encoding="utf-8") as f:
        content = f.read()
    marker = "# ============ Admin Endpoints (Auto Pull) ============"
    if marker in content:
        log("arm_server.py 已包含 Admin 接口，跳过", "info")
        return True
    with open(arm_server, "a", encoding="utf-8") as f:
        f.write(PATCH_CODE)
    log(f"已追加 Admin 接口到 arm_server.py", "ok")
    return True


# ============ 步骤 3：复制 nastool ============
def install_nastool(src):
    dst = os.path.join(NAS_BASE, "nastool")
    try:
        if os.path.exists(dst) and os.path.samefile(src, dst):
            log("nastool 已在正确位置，跳过复制", "info")
            return True
    except FileNotFoundError:
        pass
    if os.path.isdir(dst):
        log(f"清理旧 nastool: {dst}", "info")
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    log(f"nastool 已安装到: {dst}", "ok")
    return True


# ============ 步骤 4：重启服务 ============
def restart_service():
    log("重启 arm_server.py 服务...", "info")
    run("pkill -f 'arm_server.py' || true", check=False)
    time.sleep(2)
    rc, out, err = run(
        f"cd {NAS_BASE} && nohup python3 arm_server.py > arm_server.log 2>&1 & echo $!", check=False
    )
    time.sleep(4)
    # 验证服务启动
    rc, out, err = run(f"curl -s http://localhost:9999/admin/status", check=False, timeout=10)
    if rc == 0 and '"code":200' in out:
        log(f"服务启动成功: {out[:80]}", "ok")
        return True
    else:
        log(f"服务启动异常: {err or out}", "warn")
        return True  # 不阻断，继续


# ============ 步骤 5：运行诊断 ============
def run_diagnose():
    diag = os.path.join(NAS_BASE, "nastool", "arm_diagnose.py")
    if not os.path.exists(diag):
        log("未找到 arm_diagnose.py，跳过诊断", "warn")
        return
    log("运行 NASArm Toolkit 诊断...", "info")
    run(f"cd {NAS_BASE}/nastool && python3 arm_diagnose.py", timeout=60)


# ============ 主流程 ============
def main():
    print(f"\n{'=' * 50}")
    print("  NASArm Toolkit 一键安装")
    print(f"{'=' * 50}\n")

    # Step 1: 找 nastool
    log("Step 1/5: 定位 nastool 源码...", "info")
    nastool_src, location = find_nastool()
    if not nastool_src:
        log("未找到 nastool 目录！请将 nastool 文件夹放到 Desktop 或与本脚本同级目录", "fail")
        sys.exit(1)
    log(f"找到 nastool: {nastool_src}（来源: {location}）", "ok")

    # Step 2: 补丁 arm_server.py
    log("Step 2/5: 补丁 arm_server.py（添加 Admin 接口）...", "info")
    if not patch_arm_server():
        sys.exit(1)

    # Step 3: 复制 nastool
    log("Step 3/5: 安装 nastool 到 arm_server 同级目录...", "info")
    install_nastool(nastool_src)

    # Step 4: 重启服务
    log("Step 4/5: 重启 arm_server.py 服务...", "info")
    restart_service()

    # Step 5: 诊断
    log("Step 5/5: 运行诊断工具...", "info")
    run_diagnose()

    print(f"\n{'=' * 50}")
    log("安装完成！", "ok")
    print(f"{'=' * 50}")
    print(f"\n后续命令:")
    print(f"  重新诊断:  cd {NAS_BASE}/nastool && python3 arm_diagnose.py")
    print(f"  查看日志:  tail -f {NAS_BASE}/arm_server.log")


if __name__ == "__main__":
    main()
