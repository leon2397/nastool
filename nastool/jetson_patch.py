#!/usr/bin/env python3
"""
jetson_patch.py - 追加 Admin 接口到 arm_server.py
用法: python3 jetson_patch.py

运行后在 Jetson 上执行:
  pkill -f "arm_server.py" || true
  sleep 1
  nohup python3 arm_server.py > arm_server.log 2>&1 &
  sleep 3
  curl -s http://localhost:9999/admin/status
"""

import os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARM_SERVER = os.path.join(
    os.path.dirname(SCRIPT_DIR),  # nastool 的父目录 = arm/qizhiainas/arm/
    "arm_server.py",
)

PATCH = '''
# ============ Admin Endpoints (Auto Pull) ============

import tarfile, shutil, subprocess, tempfile, urllib.request
from fastapi.responses import FileResponse

@app.post("/admin/update")
async def admin_update(
    file=None,
    git_url=None,
    restart: bool = True,
    token: str = Query(None)
):
    expected_token = os.environ.get("NASTOOL_UPDATE_TOKEN", "nastool-update-secret")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    arm_dir = os.path.dirname(os.path.abspath(__file__))
    nastool_dir = os.path.join(arm_dir, "nastool")
    os.makedirs(nastool_dir, exist_ok=True)

    if file:
        logger.info(f"收到上传: {file.filename}")
        content = await file.read()
        tmp_path = "/tmp/admin_update.tar.gz"
        with open(tmp_path, "wb") as f:
            f.write(content)
        _extract_overwrite(tmp_path, nastool_dir)
        os.remove(tmp_path)
        logger.info(f"nastool 更新成功: {nastool_dir}")

    elif git_url:
        logger.info(f"从 GitHub 拉取: {git_url}")
        if os.path.isdir(nastool_dir):
            shutil.rmtree(nastool_dir)
        subprocess.run(
            ["git", "clone", "--depth=1", git_url, nastool_dir],
            capture_output=True, text=True, timeout=120, check=True
        )
    else:
        raise HTTPException(status_code=400, detail="请提供 file 或 git_url")

    diag = os.path.join(nastool_dir, "arm_diagnose.py")
    if not os.path.exists(diag):
        raise HTTPException(status_code=500, detail="arm_diagnose.py 不在目录中")

    if restart:
        async def _r():
            await asyncio.sleep(2)
            os.environ["NASTOOL_RESTART_PENDING"] = "1"
            sys.exit(0)
        asyncio.create_task(_r())
        return {"code": 200, "msg": "更新成功，2秒后重启", "data": {"restart_pending": True}}
    return {"code": 200, "msg": "更新成功", "data": {"files": os.listdir(nastool_dir)}}


@app.post("/admin/pull")
async def admin_pull(
    backend: str = Query(...),
    token: str = Query(None)
):
    expected_token = os.environ.get("NASTOOL_UPDATE_TOKEN", "nastool-update-secret")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    arm_dir = os.path.dirname(os.path.abspath(__file__))
    nastool_dir = os.path.join(arm_dir, "nastool")
    tmp_path = "/tmp/nastool_pull.tar.gz"
    logger.info(f"从 {backend} 拉取 nastool...")
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

    logger.info(f"nastool 拉取成功: {nastool_dir}")

    async def _r():
        await asyncio.sleep(2)
        os.environ["NASTOOL_RESTART_PENDING"] = "1"
        sys.exit(0)
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
    return {
        "code": 200, "msg": "ok", "data": {
            "nastool_installed": os.path.isdir(nastool_dir),
            "arm_diagnose_exists": os.path.exists(diag),
            "nastool_dir": nastool_dir,
        }
    }


def _extract_overwrite(tmp_path, nastool_dir):
    """解压 tar.gz，跳过顶层目录名，直接覆盖 nastool_dir"""
    with tarfile.open(tmp_path, "r:gz") as tar:
        members = []
        for member in tar.getmembers():
            name = member.name
            if name.startswith("nastool/"):
                member.name = name[8:]  # 去掉 "nastool/" 前缀
            elif "/" not in name:
                continue  # 跳过顶层无关文件
            members.append(member)
        tar.extractall(nastool_dir, members=members)

# ============ End Admin Endpoints ============
'''


def main():
    if not os.path.exists(ARM_SERVER):
        print(f"错误: 找不到 arm_server.py: {ARM_SERVER}")
        sys.exit(1)

    with open(ARM_SERVER, "r", encoding="utf-8") as f:
        content = f.read()

    marker = "# ============ Admin Endpoints (Auto Pull) ============"
    if marker in content:
        print("Admin 接口已存在，跳过")
        return

    with open(ARM_SERVER, "a", encoding="utf-8") as f:
        f.write(PATCH)

    print(f"✅ 已追加 Admin 接口到:")
    print(f"   {ARM_SERVER}")
    print()
    print("下一步，在 Jetson 上执行:")
    print("  pkill -f 'arm_server.py' || true")
    print("  sleep 1")
    print("  nohup python3 arm_server.py > arm_server.log 2>&1 &")
    print("  sleep 3")
    print("  curl -s http://localhost:9999/admin/status")


if __name__ == "__main__":
    main()
