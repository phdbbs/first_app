#!/usr/bin/env python3
"""交互式 SSH 执行指定命令序列。用法: python3 .sshx.py '命令1; 命令2; ...'"""
import sys, pexpect

HOST = "124.223.41.44"
USER = "ubuntu"
PASS = "PHDbbs123$%^"
PROXY = "127.0.0.1:18080"

def main(cmd):
    ssh = f"ssh -o StrictHostKeyChecking=no -o ProxyCommand='nc -X connect -x {PROXY} %h %p' {USER}@{HOST}"
    child = pexpect.spawn(ssh, encoding='utf-8', timeout=300)
    child.logfile = sys.stdout
    child.expect("[Pp]assword:")
    child.sendline(PASS)
    child.expect(r"\$")
    child.sendline(cmd)
    child.expect(r"\$")
    child.send("exit\n")
    child.close()

if __name__ == "__main__":
    main(sys.argv[1])