# -*- coding: utf-8 -*-
"""
nastools 发布打包脚本 v2.0

功能:
  - 自动从 CHANGELOG.md 提取版本号
  - 生成文件清单 (MANIFEST.txt)
  - 计算所有文件 SHA256
  - 支持增量更新 (只打包变更文件)
  - 生成发布说明摘要

用法:
  python build_release.py              # 自动检测版本
  python build_release.py 4.0.0        # 指定版本
  python build_release.py --dry-run    # 预览模式
"""
import os
import sys
import re
import shutil
import zipfile
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

ROOT = Path(__file__).parent.resolve()
DIST_DIR = ROOT / "dist"

# 排除模式
EXCLUDE = {
    "__pycache__", ".git", ".gitignore", "*.pyc", "*.pyo",
    "*.bak", "*.tmp", ".DS_Store", "Thumbs.db",
    "node_modules", ".venv", "venv", "env",
    "*.egg-info", ".pytest_cache", ".mypy_cache",
    ".idea", ".vscode", "*.sublime-*",
    "dist", "nastools-v*", "*.log", "*.db",
}

# 要包含的目录和文件
INCLUDE_DIRS = ["nastool", "nastools_pkg", "relay_server", "docs"]
INCLUDE_FILES = [
    "README.md", "CHANGELOG.md", "MEMO.md",
    "启动 nastools.bat", "nastools_README.md", "nastools_ROADMAP.md",
]


def should_include(path: Path) -> bool:
    """检查是否应该包含此文件"""
    name = path.name
    for pattern in EXCLUDE:
        if pattern.startswith("*"):
            if name.endswith(pattern[1:]):
                return False
        elif name == pattern:
            return False
    # 额外检查路径中的排除项
    for part in path.parts:
        if part in EXCLUDE:
            return False
    return True


def get_version_from_changelog() -> str:
    """从 CHANGELOG.md 提取最新版本号"""
    changelog = ROOT / "CHANGELOG.md"
    if not changelog.exists():
        return "4.0.0"
    
    content = changelog.read_text(encoding="utf-8")
    match = re.search(r"## v(\d+\.\d+\.\d+)", content)
    if match:
        return match.group(1)
    return "4.0.0"


def get_file_hash(path: Path) -> str:
    """计算文件 SHA256"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_tree(src: Path, dst: Path, manifest: dict):
    """复制目录树，记录清单"""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if not should_include(item):
            continue
        if item.is_dir():
            copy_tree(item, dst / item.name, manifest)
        else:
            rel_path = item.relative_to(ROOT)
            file_hash = get_file_hash(item)
            manifest[str(rel_path)] = {
                "hash": file_hash,
                "size": item.stat().st_size,
            }
            shutil.copy2(item, dst / item.name)


def get_release_notes(version: str) -> str:
    """从 CHANGELOG.md 提取当前版本的发布说明"""
    changelog = ROOT / "CHANGELOG.md"
    if not changelog.exists():
        return ""
    
    content = changelog.read_text(encoding="utf-8")
    # 提取当前版本的说明（到下一个版本标题之前）
    pattern = rf"## v{re.escape(version)}.*?(?=## v|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(0).strip()
    return ""


def build_package(version: str, dry_run: bool = False) -> Optional[Path]:
    """构建发布包"""
    pkg_name = f"nastools-v{version}"
    build_dir = DIST_DIR / pkg_name
    
    # 统计
    file_count = 0
    total_size = 0
    manifest = {}

    if dry_run:
        print(f"[DRY-RUN] Would build {pkg_name}")
        print("\n包含目录:")
        for d in INCLUDE_DIRS:
            src = ROOT / d
            if src.exists():
                count = sum(1 for f in src.rglob("*") if f.is_file() and should_include(f))
                print(f"  {d}/ ({count} files)")
        print("\n包含文件:")
        for f in INCLUDE_FILES:
            if (ROOT / f).exists():
                print(f"  {f}")
        return None

    # 清理
    if build_dir.exists():
        shutil.rmtree(build_dir)
    DIST_DIR.mkdir(exist_ok=True)

    print(f"[INFO] Building nastools v{version}...")
    print(f"[INFO] Build time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 复制目录
    for d in INCLUDE_DIRS:
        src = ROOT / d
        if src.exists():
            copy_tree(src, build_dir / d, manifest)
            count = sum(1 for f in (build_dir / d).rglob("*") if f.is_file())
            print(f"  [DIR]  {d}/ ({count} files)")
            file_count += count

    # 复制文件
    for f in INCLUDE_FILES:
        src = ROOT / f
        if src.exists():
            rel_path = f
            file_hash = get_file_hash(src)
            manifest[f] = {"hash": file_hash, "size": src.stat().st_size}
            shutil.copy2(src, build_dir / f)
            total_size += src.stat().st_size
            print(f"  [FILE] {f}")
            file_count += 1

    # 生成 VERSION.txt
    version_content = f"""nastools v{version}
Build: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Python: >= 3.8
Files: {file_count}
"""
    (build_dir / "VERSION.txt").write_text(version_content, encoding="utf-8")
    manifest["VERSION.txt"] = {
        "hash": get_file_hash(build_dir / "VERSION.txt"),
        "size": len(version_content.encode("utf-8")),
    }

    # 生成 MANIFEST.json
    manifest_data = {
        "version": version,
        "build_date": datetime.now().isoformat(),
        "files": manifest,
        "total_files": file_count,
    }
    (build_dir / "MANIFEST.json").write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    # 创建 zip
    zip_path = DIST_DIR / f"{pkg_name}.zip"
    print(f"\n[INFO] Creating archive...")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in build_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(DIST_DIR)
                zf.write(file, arcname)

    # 计算压缩包哈希
    zip_hash = get_file_hash(zip_path)
    zip_size = zip_path.stat().st_size

    # 写入 SHA256 文件
    sha_path = DIST_DIR / f"{pkg_name}.sha256"
    sha_path.write_text(f"{zip_hash}  {zip_path.name}\n", encoding="utf-8")

    # 写入发布说明
    release_notes = get_release_notes(version)
    if release_notes:
        notes_path = DIST_DIR / f"{pkg_name}-RELEASE_NOTES.md"
        notes_path.write_text(release_notes, encoding="utf-8")

    # 清理 build 目录
    shutil.rmtree(build_dir)

    # 输出统计
    print(f"\n{'='*50}")
    print(f"[OK] Package built successfully!")
    print(f"{'='*50}")
    print(f"  Version:    v{version}")
    print(f"  Archive:    {zip_path.name}")
    print(f"  Size:       {zip_size / 1024 / 1024:.2f} MB")
    print(f"  Files:      {file_count}")
    print(f"  SHA256:     {zip_hash}")
    print(f"{'='*50}")

    return zip_path


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args or "-n" in args
    
    # 解析版本号
    version = None
    for arg in args:
        if re.match(r"\d+\.\d+\.\d+", arg):
            version = arg
            break
    
    if not version:
        version = get_version_from_changelog()
    
    build_package(version, dry_run)


if __name__ == "__main__":
    main()
