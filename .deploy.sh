#!/bin/bash
# TNR 生产部署脚本（适配 Docker MariaDB）
set -e

echo "==== [1/7] pip 清华源 ===="
printf '[global]\nindex-url = https://pypi.tuna.tsinghua.edu.cn/simple\n' | sudo tee /etc/pip.conf >/dev/null

echo "==== [2/7] 同步新代码到 /opt/tnr ===="
cd /tmp/tnr
sudo mkdir -p /opt/tnr
# 用 tar 管道同步，排除 venv/db/缓存/git
sudo tar -C /tmp/tnr --exclude='venv' --exclude='db.sqlite3' --exclude='*.pyc' \
  --exclude='__pycache__' --exclude='staticfiles' --exclude='media' --exclude='.git' \
  -cf - . | sudo tar -C /opt/tnr -xf -
echo "代码已同步: $(ls /opt/tnr/manage.py)"

echo "==== [3/7] 重建 venv 并装依赖 ===="
cd /opt/tnr
sudo rm -rf venv
sudo python3 -m venv venv
sudo chown -R ubuntu:ubuntu venv
sudo venv/bin/pip install --upgrade pip -q
sudo venv/bin/pip install -r requirements.txt -q
echo "依赖安装完成"

echo "==== [4/7] 生成 .env ===="
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
sudo tee /opt/tnr/.env >/dev/null <<ENVEOF
DEBUG=False
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=100.99.98.71,124.223.41.44,localhost,127.0.0.1
DB_ENGINE=mysql
DB_NAME=tnr_system
DB_USER=tnr
DB_PASSWORD=ChangeMeInProduction!
DB_HOST=127.0.0.1
DB_PORT=3306
ENVEOF
echo ".env 已生成"

echo "==== [5/7] Django migrate / collectstatic / seed ===="
cd /opt/tnr
set +e
sudo venv/bin/python manage.py migrate --noinput
MIG=$?
sudo venv/bin/python manage.py collectstatic --noinput
sudo venv/bin/python manage.py seed_data
set -e
echo "migrate 退出码=$MIG"

echo "==== [6/7] 创建 admin ===="
sudo venv/bin/python manage.py shell <<'PYEOF'
from accounts.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@tnr.local', 'admin123456', role='gov_city', first_name='市级管理员')
    print('admin created')
else:
    print('admin exists')
PYEOF

echo "==== [7/7] Supervisor + Nginx ===="
sudo mkdir -p /var/log/tnr
sudo cp /tmp/tnr/deploy/supervisor.conf /etc/supervisor/conf.d/tnr.conf
sudo cp /tmp/tnr/deploy/nginx.conf /etc/nginx/sites-available/tnr
sudo ln -sf /etc/nginx/sites-available/tnr /etc/nginx/sites-enabled/tnr
sudo rm -f /etc/nginx/sites-enabled/default
sudo chown -R www-data:www-data /opt/tnr/media 2>/dev/null || true
sudo chown -R www-data:www-data /opt/tnr/staticfiles 2>/dev/null || true
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart tnr-gunicorn tnr-qworker || echo "(supervisor restart 部分完成)"
sudo nginx -t
sudo systemctl reload nginx

echo "==== DEPLOY_DONE ===="