#!/usr/bin/env python3
"""上传 .deploy.sh（base64）到服务器并执行，实时回显输出。"""
import sys, base64, pexpect

HOST = "124.223.41.44"
USER = "ubuntu"
PASS = "PHDbbs123$%^"
PROXY = "127.0.0.1:18080"

def main():
    with open("/workspace/.deploy.sh", "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ssh = f"ssh -o StrictHostKeyChecking=no -o ProxyCommand='nc -X connect -x {PROXY} %h %p' {USER}@{HOST}"
    child = pexpect.spawn(ssh, encoding='utf-8', timeout=600)
    child.logfile = sys.stdout
    child.expect("[Pp]assword:")
    child.sendline(PASS)
    child.expect(r"\$")
    # 写部署脚本并执行 —— 单行命令，base64 无特殊字符
    cmd = f"echo {b64} | base64 -d > /tmp/tnr_deploy.sh && sudo bash /tmp/tnr_deploy.sh"
    child.sendline(cmd)
    child.expect("DEPLOY_DONE")
    child.send("exit\n")
    child.close()
    print("\n[DEPLOY_FINISHED]")

if __name__ == "__main__":
    main()