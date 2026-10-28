#!/usr/bin/env python3
"""
通过 GitHub REST API（git data endpoints）推送本地提交。

**为什么需要它**：某些网络环境下代理只放行 `api.github.com` 而拦 `github.com`，
而 git 的 smart HTTP 协议必须走 `github.com`——此时 `git push` 会持续报
`CONNECT tunnel failed`，完整 `git fetch` 也会因 pack 传输被掐断而失败
（浅克隆 `--depth=1` 反而可能成功，因为它走的是更小的传输）。

**实测结论（2026-10-28）**：本机代理当前对 `github.com` 的**引用查询**与
**浅 fetch / push** 放行，但**完整历史 fetch** 失败（`invalid index-pack
output`）。所以日常推送优先用原生 `git push`（SHA 与本地完全一致，不需对齐）；
本脚本作为**备用通道**保留，用于 git 协议彻底不可用时。

**它保留完整历史**：逐个 commit 重建，不是只推最后一个快照。
每个 commit 的 tree 都由它的父 commit 的 tree 加上该 commit 的差异构成，
所以远端能看到与本地一致的提交序列。

**代价**：远端 commit 的 SHA 与本地不同（GitHub API 重新计算了对象）。
推送完成后用 `git fetch origin && git reset --hard origin/main` 让本地对齐，
或直接 `git reset --soft` 保留本地提交。**不影响内容，只影响 SHA。**

**用法**：
    python tools/push_via_api.py                # 推 master 到 main
    python tools/push_via_api.py --ref master   # 推 master 到 master（危险）
    python tools/push_via_api.py --dry-run      # 只打印计划
    python tools/push_via_api.py --rebuild      # 从根重建（纠正远端错误内容）

**安全**：默认拒绝覆盖有分歧的分支；`master`（前身 V7.x 代码所在）
需要额外输入 yes 确认。
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
REPO = "leon2397/nastool"


def get_token() -> str:
    """从 Git Credential Manager 取已存的凭证。"""
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True, timeout=60,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("错误：未找到 GitHub 凭证。请先配置 credential helper 或推送一次。")


def api(path: str, method: str = "GET", data=None, token: str = "",
        retries: int = 4):
    """
    调用 GitHub API，带指数退避重试。

    **为什么需要重试**：这条通道走的是代理隧道，实测出现过 socket 读超时
    （`TimeoutError: The read operation timed out`）。一次超时不代表请求失败
    ——重试是必要的，否则一个抖动就会打断整条重建链。
    """
    body = json.dumps(data).encode("utf-8") if data is not None else None
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            f"{API}{path}", data=body, method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "User-Agent": "nastool-push",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            # 5xx 是服务端/代理问题，值得重试；4xx 是请求本身的问题，重试无意义
            if e.code >= 500 and attempt < retries:
                last_exc = RuntimeError(f"API 错误 {e.code} {path}")
            else:
                raise SystemExit(f"API 错误 {e.code} {path}: {detail}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # 连接被代理掐断 / 读超时 —— 重试
            if attempt >= retries:
                raise SystemExit(f"API 请求失败（重试 {retries} 次仍未成功） {path}: {e}") from None
            last_exc = e
        time.sleep(min(2 ** attempt, 20))
    raise SystemExit(f"API 请求失败 {path}: {last_exc}")


def git(*args: str, check: bool = True) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=180)
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 失败: {r.stderr.strip()}")
    return r.stdout.strip()


def blob_exists(sha: str, token: str) -> bool:
    try:
        api(f"/repos/{REPO}/git/blobs/{sha}", token=token)
        return True
    except SystemExit:
        return False


def upload_blob(commit_sha: str, path: str, token: str) -> str:
    """
    上传文件为 blob，返回 blob SHA。

    从 **git 对象**读取内容而不是工作区——工作区可能已经没有这个文件了
    （比如它后来被删掉，但删除前的那个 commit 仍需要它）。
    """
    content = subprocess.run(
        ["git", "cat-file", "blob", f"{commit_sha}:{path}"],
        capture_output=True, timeout=120,
    ).stdout
    if not content:
        raise SystemExit(f"读不到 blob 内容: {commit_sha[:8]}:{path}")
    data = base64.b64encode(content).decode()
    res = api(f"/repos/{REPO}/git/blobs", "POST",
              {"content": data, "encoding": "base64"}, token)
    return res["sha"]


def _changed_entries(commit_sha: str, parent: str | None):
    """
    列出该 commit 相对父提交变更的文件：(路径, 模式, blob SHA, 是否删除)

    **必须用 -z（NUL 分隔）**：`git diff-tree` 默认输出时，含中文或特殊字符的
    路径会被 git 加引号并八进制转义（如 "reference/legacy/docs/NASTool\\351\\203\\250..."），
    直接 split 会把转义串当成路径名，在远端造出一堆带引号的假目录。
    实测这个坑造出的假目录会让 Windows 上的 checkout 直接失败。

    根提交没有父，视为「全部文件都是新增」。
    """
    if parent is None:
        args = ["git", "ls-tree", "-r", "-z", commit_sha]
    else:
        args = ["git", "diff-tree", "-r", "-z", "--no-renames",
                "--raw", parent, commit_sha]

    raw = subprocess.run(args, capture_output=True, timeout=180).stdout

    if parent is None:
        for record in raw.split(b"\x00"):
            if not record:
                continue
            meta, _, path_b = record.partition(b"\t")
            mode, typ, sha = meta.decode().split()
            if typ != "blob":
                continue
            yield path_b.decode("utf-8"), mode, sha, False
        return

    # --raw 格式：:<old_mode> <new_mode> <old_sha> <new_sha> <status>\0<path>\0
    #
    # 注意 `-z` 模式下 **metadata 与路径之间是 NUL 而不是 TAB**——
    # 这是 `diff-tree --raw -z` 与 `ls-tree -z` 的关键差别。
    # 所以记录是「meta, path」交替出现的。
    parts = raw.split(b"\x00")
    i = 0
    while i < len(parts) - 1:
        meta = parts[i].decode("utf-8", "replace")
        path = parts[i + 1].decode("utf-8", "replace")
        i += 2
        if not meta or not path:
            continue
        fields = meta.split()
        if len(fields) < 5:
            continue
        old_mode, new_mode, old_sha, new_sha, status = fields[:5]
        if status == "D":
            yield path, new_mode or old_mode, old_sha, True
        elif status == "T":
            # 类型变了（文件 ↔ 符号链接）：按新增处理
            yield path, new_mode, new_sha, False
        else:
            yield path, new_mode, new_sha, False


def build_tree(base_tree: str | None, entries: list, token: str) -> str:
    res = api(f"/repos/{REPO}/git/trees", "POST",
              {"base_tree": base_tree, "tree": entries}, token)
    return res["sha"]


def main() -> int:
    ap = argparse.ArgumentParser(description="通过 GitHub API 推送本地提交")
    ap.add_argument("--ref", default="main", help="目标远端分支（默认 main）")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划")
    ap.add_argument("--rebuild", action="store_true",
                    help="从根重建整个历史（用于纠正远端已有的错误内容）")
    args = ap.parse_args()

    token = get_token()
    local = git("rev-parse", "HEAD")
    print(f"本地 HEAD: {local[:8]}")

    # 目标远端分支现状
    ref_exists = False
    try:
        remote_ref = api(f"/repos/{REPO}/git/ref/heads/{args.ref}", token=token)
        remote_sha = remote_ref["object"]["sha"]
        ref_exists = True
        print(f"远端 {args.ref}: {remote_sha[:8]}")
    except SystemExit:
        remote_sha = None
        print(f"远端 {args.ref}: 不存在（将创建）")

    if remote_sha == local:
        print("✓ 远端与本地一致，无需推送")
        return 0

    # 要推送的 commit 序列（从远端已有的那个之后开始）
    if args.rebuild:
        # 从根重建：远端现有历史可能有错误（路径转义 bug 留下的假目录），
        # 重建能一次性纠正。父链从本地 HEAD 回溯到根。
        commits = git("rev-list", "--reverse", local).splitlines()
        print(f"→ 重建模式：从根重建 {len(commits)} 个提交")
        remote_sha = None
        parent = None
    elif remote_sha:
        ff = True
        try:
            git("merge-base", "--is-ancestor", remote_sha, local)
        except SystemExit:
            ff = False
        if ff:
            commits = git("rev-list", "--reverse", f"{remote_sha}..{local}").splitlines()
            print(f"→ 快进：待推送 {len(commits)} 个提交")
        else:
            behind = git("rev-list", "--count", f"{local}..{remote_sha}")
            print(f"⚠ 分歧：远端有 {behind} 个本地没有的提交，将被丢弃")
            if args.ref == "master":
                print("  ⚠⚠ master 保存着前身 V7.x 代码，覆盖它会丢失那些代码！")
            if not args.dry_run:
                ans = input("  确认覆盖？输入 yes 继续: ").strip()
                if ans.lower() != "yes":
                    print("已取消")
                    return 1
            commits = git("rev-list", "--reverse", f"{local}").splitlines()
    else:
        commits = git("rev-list", "--reverse", local).splitlines()

    if args.dry_run:
        print("\n[dry-run] 将推送这些提交：")
        for c in commits:
            print(f"  {c[:8]} {git('log', '-1', '--format=%s', c)}")
        return 0

    # ── 逐个 commit 重建 ──
    parent = None if args.rebuild else remote_sha
    for idx, commit_sha in enumerate(commits, 1):
        msg = git("log", "-1", "--format=%B", commit_sha).strip()
        author = git("log", "-1", "--format=%an", commit_sha)
        email = git("log", "-1", "--format=%ae", commit_sha)
        when = git("log", "-1", "--format=%cI", commit_sha)

        # 该 commit 相对父提交**变更的**文件
        #
        # 为什么只传差异：GitHub 的建树接口支持 `base_tree`（以父提交的 tree
        # 为基底），只列变更项即可得到与本地完全相同的 tree SHA。
        # 传全量文件的话，15 个提交 × 106 个文件 = 1600 次 blob 探测请求，
        # 在慢代理下要跑十几分钟；只传差异则每个提交通常只有几个文件。
        entries = []
        for path, mode, sha, deleted in _changed_entries(commit_sha, parent):
            if deleted:
                # 删除的文件：用 sha=null 告诉 GitHub 从基底里去掉它
                entries.append({"path": path, "mode": mode, "type": "blob", "sha": None})
                continue
            if not blob_exists(sha, token):
                upload_blob(commit_sha, path, token)
            entries.append({"path": path, "mode": mode, "type": "blob", "sha": sha})

        # base_tree = 父 commit 的 tree
        base_tree = None
        if parent:
            try:
                base_tree = api(f"/repos/{REPO}/git/commits/{parent}",
                                token=token)["tree"]["sha"]
            except SystemExit:
                base_tree = None
        tree_sha = build_tree(base_tree, entries, token)

        new_commit = api(f"/repos/{REPO}/git/commits", "POST", {
            "message": msg,
            "tree": tree_sha,
            "parents": [parent] if parent else [],
            "author": {"name": author, "email": email, "date": when},
            "committer": {"name": author, "email": email, "date": when},
        }, token)
        parent = new_commit["sha"]
        print(f"  [{idx}/{len(commits)}] {commit_sha[:8]} → {parent[:8]}  {msg.splitlines()[0][:50]}")

    # ── 更新 ref ──
    print("\n更新远端分支…")
    # 注意：用 ref_exists（而不是 remote_sha）判断该 PATCH 还是 POST——
    # rebuild 模式会把 remote_sha 清空，但分支本身是存在的。
    if ref_exists:
        api(f"/repos/{REPO}/git/refs/heads/{args.ref}", "PATCH",
            {"sha": parent, "force": True}, token)
    else:
        api(f"/repos/{REPO}/git/refs", "POST",
            {"ref": f"refs/heads/{args.ref}", "sha": parent}, token)

    print(f"\n✓ 推送完成 → https://github.com/{REPO}/tree/{args.ref}")
    print(f"  远端 HEAD: {parent}")
    print(f"  本地 HEAD: {local}")
    print("  注：SHA 不同（API 重建对象）。让本地对齐：")
    print(f"    git fetch origin && git reset --hard origin/{args.ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
