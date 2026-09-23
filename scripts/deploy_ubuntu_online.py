#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
熵舟 · Ubuntu 在线一键部署驱动（从本机 Windows 通过 SSH/SFTP 编排）
用法：
    python scripts/deploy_ubuntu_online.py            # 上传 + 部署
    python scripts/deploy_ubuntu_online.py --upload-only
    python scripts/deploy_ubuntu_online.py --run-only
"""
import os
import sys
import posixpath
import paramiko

# ------------------------------ 连接参数 -------------------------------------
HOST = os.environ.get("SZ_HOST", "172.28.186.196")
USER = os.environ.get("SZ_USER", "yuty")
PWD  = os.environ.get("SZ_PASS", "0000")
APP_DIR = os.environ.get("SZ_APP_DIR", "/home/yuty/shangzhou")
REMOTE_SCRIPT = posixpath.join(APP_DIR, "deploy-ubuntu-online.sh")

LOCAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 上传映射：(本地相对路径, 远端相对路径, 排除正则片段)
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", "venv_libs", "logs", "node_modules", ".git"}
EXCLUDE_SUFFIX = (".pyc", ".pyo")
# 需要保留的 backend 目录级缓存：排除运行时 cache/ 与 data/（可重建/本地态）
BACKEND_EXCLUDE_TOP = {"cache"}

UPLOADS = [
    ("backend", "backend"),
    (os.path.join("front", "dist"), "front/dist"),
    ("scripts/deploy-ubuntu-online.sh", "deploy-ubuntu-online.sh"),
]


def connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PWD, timeout=30,
              banner_timeout=30, auth_timeout=30)
    return c


def _sftp_makedirs(sftp, remote_dir):
    parts = remote_dir.strip("/").split("/")
    cur = ""
    for p in parts:
        cur = cur + "/" + p
        try:
            sftp.stat(cur)
        except IOError:
            sftp.mkdir(cur)


def should_skip(rel_path):
    segs = rel_path.replace("\\", "/").split("/")
    for s in segs:
        if s in EXCLUDE_DIRS:
            return True
    if rel_path.endswith(EXCLUDE_SUFFIX):
        return True
    return False


def upload(c):
    sftp = c.open_sftp()
    # 准备 APP_DIR 并交给当前用户上传（避免 root 属主）
    run(c, f"echo {PWD} | sudo -S -p '' mkdir -p {APP_DIR}", quiet=True)
    run(c, f"echo {PWD} | sudo -S -p '' chown -R {USER}:{USER} {APP_DIR}", quiet=True)
    total = 0
    for local_rel, remote_rel in UPLOADS:
        lp = os.path.join(LOCAL_ROOT, local_rel.replace("/", os.sep))
        rp = posixpath.join(APP_DIR, remote_rel)
        if os.path.isfile(lp):
            _sftp_makedirs(sftp, posixpath.dirname(rp))
            sftp.put(lp, rp)
            total += 1
            print(f"  file -> {rp}")
            continue
        # 目录递归
        for root, dirs, files in os.walk(lp):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                if f.endswith(EXCLUDE_SUFFIX):
                    continue
                absf = os.path.join(root, f)
                rel = os.path.relpath(absf, lp).replace("\\", "/")
                if local_rel == "backend" and rel.split("/")[0] in BACKEND_EXCLUDE_TOP:
                    continue  # 跳过 backend/cache 运行时缓存
                target = posixpath.join(rp, rel)
                _sftp_makedirs(sftp, posixpath.dirname(target))
                sftp.put(absf, target)
                total += 1
        print(f"  dir  -> {rp}  ({local_rel})")
    sftp.close()
    print(f"[upload] 完成，共 {total} 个文件")


def run(c, cmd, quiet=False, stream=False):
    _, o, e = c.exec_command(cmd, timeout=1800, get_pty=stream)
    if stream:
        # 读取原始字节再增量解码，避免 readline 在多字节 UTF-8 边界截断
        chan = o.channel
        pending = b""
        while True:
            data = chan.recv(4096)
            if not data:
                break
            buf = pending + data
            try:
                text = buf.decode("utf-8")
                pending = b""
            except UnicodeDecodeError:
                # 保留末尾可能的半个多字节序列，等待下一块
                keep = 0
                for k in (1, 2, 3, 4):
                    try:
                        text = buf[:-k].decode("utf-8")
                        pending = buf[-k:]
                        keep = 1
                        break
                    except UnicodeDecodeError:
                        continue
                if not keep:
                    text = buf.decode("utf-8", "replace")
                    pending = b""
            if text:
                sys.stdout.write(text)
                sys.stdout.flush()
        if pending:
            sys.stdout.write(pending.decode("utf-8", "replace"))
            sys.stdout.flush()
        rc = o.channel.recv_exit_status()
        return rc
    out = o.read().decode("utf-8", "replace")
    err = e.read().decode("utf-8", "replace")
    rc = o.channel.recv_exit_status()
    if not quiet:
        print(out)
        if err.strip():
            print("STDERR:", err)
    return rc


def deploy(c):
    # 清理旧位置 /opt/shangzhou（历史遗留，现已迁至 /home/yuty）
    run(c, "echo %s | sudo -S -p '' rm -rf /opt/shangzhou" % PWD, quiet=True)
    # 去掉可能的 CRLF，确保可执行
    run(c, f"sed -i 's/\\r$//' {REMOTE_SCRIPT}")
    run(c, f"chmod +x {REMOTE_SCRIPT}")
    print(f"[deploy] 运行一键部署脚本：{REMOTE_SCRIPT}")
    rc = run(c, f"echo {PWD} | sudo -S -p '' bash {REMOTE_SCRIPT}", stream=True)
    print(f"[deploy] 脚本退出码 = {rc}")
    return rc


def main():
    args = sys.argv[1:]
    upload_only = "--upload-only" in args
    run_only = "--run-only" in args
    c = connect()
    print(f"[ssh] 已连接 {USER}@{HOST}")
    try:
        if not run_only:
            upload(c)
        if not upload_only:
            rc = deploy(c)
            if rc != 0:
                sys.exit(rc)
    finally:
        c.close()


if __name__ == "__main__":
    main()
