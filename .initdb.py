#!/usr/bin/env python3
"""经代理隧道 SSH，执行多行命令（支持 heredoc，规避 bash 历史展开）。"""
import sys, time, pexpect

HOST = "124.223.41.44"
USER = "ubuntu"
PASS = "PHDbbs123$%^"
PROXY = "127.0.0.1:18080"
CONTAINER = "1Panel-mariadb-LQ69"
DBROOT = "mariadb_XTaMfk"

def main():
    ssh = f"ssh -o StrictHostKeyChecking=no -o ProxyCommand='nc -X connect -x {PROXY} %h %p' {USER}@{HOST}"
    child = pexpect.spawn(ssh, encoding='utf-8', timeout=300)
    child.logfile = sys.stdout
    child.expect("[Pp]assword:")
    child.sendline(PASS)
    child.expect(r"\$")
    # 用 heredoc 写入 SQL 文件（单引号定界符，! 安全）
    sql = f"""sudo tee /tmp/tnr_init.sql >/dev/null <<'SQLEOF'
CREATE DATABASE IF NOT EXISTS tnr_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'tnr'@'%' IDENTIFIED BY 'ChangeMeInProduction!';
GRANT ALL PRIVILEGES ON tnr_system.* TO 'tnr'@'%';
FLUSH PRIVILEGES;
SQLEOF
sudo docker exec -i {CONTAINER} mariadb -uroot -p{DBROOT} < /tmp/tnr_init.sql
echo INIT_SQL_DONE
"""
    child.sendline(sql)
    child.expect("INIT_SQL_DONE")
    child.send("exit\n")
    child.close()

if __name__ == "__main__":
    main()