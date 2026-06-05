# Log Analyzer 系统服务打包与部署方案

> 版本: v1.0
> 更新日期: 2026-06-05
> 项目路径: `/Users/a666/Documents/trae_projects/log/log_analyzer`

---

## 目录

1. [文档概述](#1-文档概述)
2. [系统打包规范](#2-系统打包规范)
3. [测试环境部署流程](#3-测试环境部署流程)
4. [生产环境部署流程](#4-生产环境部署流程)
5. [部署自动化配置](#5-部署自动化配置)
6. [监控与日志配置](#6-监控与日志配置)
7. [配置管理策略](#7-配置管理策略)
8. [附录](#8-附录)

---

## 1. 文档概述

### 1.1 目的

本文档旨在为 Log Analyzer 系统提供一套完整的打包与部署方案，涵盖测试环境和生产环境的部署流程、自动化配置、监控策略以及配置管理规范。

### 1.2 适用范围

- **测试环境**：开发测试、功能验证、性能测试
- **生产环境**：正式上线运行、业务服务支撑

### 1.3 参考文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 项目概述 | `docs/PROJECT_OVERVIEW.md` | 项目功能说明 |
| API文档 | `docs/API.md` | 接口规范 |
| 开发者指南 | `docs/DEVELOPER_GUIDE.md` | 开发规范 |

---

## 2. 系统打包规范

### 2.1 依赖管理

#### 2.1.1 Python版本要求

```bash
Python >= 3.10.0
```

#### 2.1.2 核心依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| httpx | >=0.25.0 | HTTP客户端 |
| aiofiles | >=23.0.0 | 异步文件操作 |
| fastapi | >=0.109.0 | Web框架 |
| uvicorn | >=0.27.0 | ASGI服务器 |
| python-multipart | >=0.0.6 | 文件上传处理 |
| reportlab | >=4.0.0 | PDF生成 |
| python-docx | >=1.1.0 | Word生成 |
| markdown | >=3.4.0 | Markdown处理 |
| weasyprint | >=69.0 | HTML转PDF |

#### 2.1.3 依赖安装命令

```bash
# 安装核心依赖
pip install -r requirements.txt

# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 安装性能测试依赖
pip install locust
```

### 2.2 构建流程

#### 2.2.1 打包前检查

```bash
# 1. 检查Python版本
python --version

# 2. 检查依赖完整性
pip check

# 3. 运行单元测试
pytest tests/ -v

# 4. 运行并发性能测试
python tests/concurrency_test.py
```

#### 2.2.2 打包命令

```bash
# 使用pip打包（推荐）
pip install wheel
python setup.py sdist bdist_wheel

# 或使用 poetry（备选）
poetry build
```

#### 2.2.3 Docker打包

```bash
# 构建Docker镜像
docker build -t log-analyzer:v2.5.1 .

# 保存镜像到文件
docker save -o log-analyzer-v2.5.1.tar log-analyzer:v2.5.1
```

### 2.3 产物结构

#### 2.3.1 源码包结构

```
log_analyzer/
├── web/                    # Web服务模块
│   ├── app.py             # FastAPI应用入口
│   ├── auth.py            # 认证模块
│   ├── action_logger.py   # 操作日志
│   ├── storage.py         # 存储管理
│   └── static/            # 静态资源
├── report/                # 报告生成模块
│   ├── generator.py       # 报告生成器
│   └── rule_based_analyzer.py  # 规则分析器
├── processor/             # 日志处理模块
│   └── chunk_processor.py # 分块处理器
├── llm/                   # LLM客户端
│   └── client.py          # LLM调用封装
├── config/                # 配置文件
│   └── config.json        # 主配置文件
├── data/                  # 数据目录（运行时创建）
│   ├── uploads/           # 上传文件
│   ├── reports/           # 生成报告
│   ├── tasks/             # 任务信息
│   └── action_logs/       # 操作日志
├── logs/                  # 系统日志
├── tests/                 # 测试用例
├── docs/                  # 文档
├── requirements.txt       # 依赖清单
└── README.md              # 项目说明
```

#### 2.3.2 部署包结构

```
deploy_package/
├── log_analyzer/          # 应用代码
├── requirements.txt       # 依赖清单
├── config/                # 配置文件目录
│   ├── config.json        # 应用配置
│   └── .env               # 环境变量
├── scripts/               # 部署脚本
│   ├── start.sh           # 启动脚本
│   ├── stop.sh            # 停止脚本
│   └── health_check.sh    # 健康检查脚本
└── VERSION                # 版本号文件
```

---

## 3. 测试环境部署流程

### 3.1 环境准备

#### 3.1.1 操作系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Ubuntu 22.04 LTS / CentOS 8+ / macOS 12+ |
| CPU | 至少2核 |
| 内存 | 至少4GB |
| 磁盘 | 至少20GB可用空间 |
| 网络 | 能访问外部网络（LLM API调用） |

#### 3.1.2 依赖安装

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip
sudo apt install -y tshark  # PCAP分析依赖
sudo apt install -y libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0  # WeasyPrint依赖

# CentOS/RHEL
sudo yum install -y python3.10 python3.10-devel
sudo yum install -y wireshark-cli
sudo yum install -y pango harfbuzz

# macOS
brew install python@3.10
brew install tshark
```

### 3.2 部署步骤

#### 3.2.1 克隆代码

```bash
cd /opt
git clone https://github.com/your-repo/log_analyzer.git
cd log_analyzer
git checkout v2.5.1
```

#### 3.2.2 创建虚拟环境

```bash
python3.10 -m venv venv
source venv/bin/activate
```

#### 3.2.3 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3.2.4 配置环境

```bash
# 创建数据目录
mkdir -p data/uploads data/reports data/tasks data/action_logs logs

# 复制配置文件
cp config/config.json config/config.json.bak

# 修改测试环境配置
cat > config/config.json << EOF
{
  "llm": {
    "api_url": "https://api.modelarts-maas.com/openai/v1",
    "model_name": "qwen3-235b-a22b",
    "api_key": "your-test-api-key",
    "backup_model": "deepseek-v3.2"
  },
  "processing": {
    "chunk_size": 1000000,
    "max_retries": 3,
    "retry_delay": 1.0,
    "batch_size": 100,
    "checkpoint_interval": 1000,
    "enable_checkpoint": true,
    "max_workers": 2,
    "merge_threshold": 0.8
  },
  "paths": {
    "error_log_dir": "/opt/log_analyzer/data/uploads",
    "output_dir": "/opt/log_analyzer/data/reports",
    "checkpoint_dir": "/opt/log_analyzer/checkpoint",
    "user_data_dir": "/opt/log_analyzer/data"
  },
  "logging": {
    "log_level": "DEBUG",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "enable_file_logging": true
  },
  "app": {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": true,
    "api_prefix": "/api"
  },
  "security": {
    "allowed_users": ["admin001", "test_user", "hanmeimei"],
    "max_file_size_mb": 100,
    "max_files_per_request": 5
  },
  "server_path": {
    "allowed_directories": ["/tmp", "/opt/test-logs"],
    "max_paths": 3
  }
}
EOF
```

#### 3.2.5 启动服务

```bash
# 方式1：直接启动（开发模式）
cd web
./start.sh

# 方式2：后台启动
nohup uvicorn web.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --reload \
    > logs/web.log 2>&1 &

# 方式3：使用systemd（推荐）
cat > /etc/systemd/system/log-analyzer-test.service << EOF
[Unit]
Description=Log Analyzer Test Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/log_analyzer
Environment="PATH=/opt/log_analyzer/venv/bin"
ExecStart=/opt/log_analyzer/venv/bin/uvicorn web.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --reload
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start log-analyzer-test
systemctl enable log-analyzer-test
```

### 3.3 验证方法

#### 3.3.1 健康检查

```bash
# 检查服务是否启动
curl -s http://localhost:8000/api/health

# 预期响应
{"code":0,"message":"ok","data":{"status":"healthy","timestamp":"2026-06-05T10:00:00"}}
```

#### 3.3.2 API功能测试

```bash
# 测试文件上传接口
curl -X POST http://localhost:8000/api/upload \
    -F "file=@/path/to/test.log" \
    -H "X-User-Id: test_user"

# 测试任务处理接口
curl -X POST http://localhost:8000/api/process \
    -H "Content-Type: application/json" \
    -H "X-User-Id: test_user" \
    -d '{"file_path": "/path/to/test.log", "use_llm": false}'
```

#### 3.3.3 前端页面验证

```bash
# 检查前端页面是否可访问
curl -s http://localhost:8000/ | head -5

# 预期包含
# <!DOCTYPE html>
# <html lang="zh-CN">
```

#### 3.3.4 性能测试

```bash
# 运行并发性能测试
python tests/concurrency_test.py

# 运行端到端测试
python tests/test_complete_e2e.py
```

---

## 4. 生产环境部署流程

### 4.1 环境要求

#### 4.1.1 硬件要求

| 项目 | 推荐配置 | 最低配置 |
|------|---------|---------|
| CPU | 8核及以上 | 4核 |
| 内存 | 16GB及以上 | 8GB |
| 磁盘 | 100GB SSD | 50GB |
| 网络 | 100Mbps带宽 | 50Mbps |

#### 4.1.2 软件要求

| 项目 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 运行时环境 |
| Nginx | 1.20+ | 反向代理 |
| Certbot | 1.20+ | SSL证书 |
| tshark | 4.0+ | PCAP分析 |

### 4.2 部署策略

#### 4.2.1 蓝绿部署模式

```
┌─────────────────────────────────────────────────────────────┐
│                    生产环境架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [Nginx Load Balancer]                                     │
│           │                                                 │
│     ┌─────┴─────┐                                           │
│     ▼           ▼                                           │
│  [Blue]      [Green]                                        │
│  v2.5.0     v2.5.1                                         │
│                                                             │
│  1. 部署新版本到Green环境                                    │
│  2. 验证Green环境                                           │
│  3. 切换流量到Green                                          │
│  4. 监控运行状态                                            │
│  5. 如失败则切回Blue                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 4.2.2 滚动更新模式（单节点）

```bash
# 1. 停止旧版本
systemctl stop log-analyzer

# 2. 备份数据
tar -czf /backup/log_analyzer_$(date +%Y%m%d).tar.gz /opt/log_analyzer/data

# 3. 更新代码
git pull origin main
git checkout v2.5.1

# 4. 更新依赖
pip install -r requirements.txt --upgrade

# 5. 启动新版本
systemctl start log-analyzer

# 6. 验证
curl -s http://localhost:8000/api/health
```

### 4.3 详细部署步骤

#### 4.3.1 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装依赖
sudo apt install -y python3.10 python3.10-venv python3-pip
sudo apt install -y nginx certbot python3-certbot-nginx
sudo apt install -y tshark libpango-1.0-0 libharfbuzz0b

# 创建用户
sudo useradd -m -d /opt/log_analyzer -s /bin/bash loganalyzer
```

#### 4.3.2 代码部署

```bash
# 切换到专用用户
su - loganalyzer

# 克隆代码
git clone https://github.com/your-repo/log_analyzer.git /opt/log_analyzer
cd /opt/log_analyzer
git checkout v2.5.1

# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 创建数据目录
mkdir -p data/uploads data/reports data/tasks data/action_logs logs
```

#### 4.3.3 生产环境配置

```bash
# 创建生产配置文件
cat > config/config.json << EOF
{
  "llm": {
    "api_url": "https://api.modelarts-maas.com/openai/v1",
    "model_name": "qwen3-235b-a22b",
    "api_key": "your-production-api-key",
    "backup_model": "deepseek-v3.2"
  },
  "processing": {
    "chunk_size": 1000000,
    "max_retries": 3,
    "retry_delay": 1.0,
    "batch_size": 100,
    "checkpoint_interval": 1000,
    "enable_checkpoint": true,
    "max_workers": 4,
    "merge_threshold": 0.8
  },
  "paths": {
    "error_log_dir": "/opt/log_analyzer/data/uploads",
    "output_dir": "/opt/log_analyzer/data/reports",
    "checkpoint_dir": "/opt/log_analyzer/checkpoint",
    "user_data_dir": "/opt/log_analyzer/data"
  },
  "logging": {
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "enable_file_logging": true
  },
  "app": {
    "host": "127.0.0.1",
    "port": 8000,
    "debug": false,
    "api_prefix": "/api"
  },
  "security": {
    "allowed_users": ["admin001", "user001", "user002"],
    "max_file_size_mb": 500,
    "max_files_per_request": 10
  },
  "server_path": {
    "allowed_directories": ["/var/log", "/opt/app/logs"],
    "max_paths": 5
  }
}
EOF
```

#### 4.3.4 配置systemd服务

```bash
# 创建systemd服务文件
cat > /etc/systemd/system/log-analyzer.service << EOF
[Unit]
Description=Log Analyzer Service
After=network.target

[Service]
User=loganalyzer
Group=loganalyzer
WorkingDirectory=/opt/log_analyzer
Environment="PATH=/opt/log_analyzer/venv/bin"
ExecStart=/opt/log_analyzer/venv/bin/uvicorn web.app:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4 \
    --limit-concurrency 200 \
    --backlog 2048 \
    --timeout-keep-alive 30
Restart=always
RestartSec=5
Environment="PYTHONPATH=/opt/log_analyzer"

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
systemctl daemon-reload
systemctl start log-analyzer
systemctl enable log-analyzer
```

#### 4.3.5 配置Nginx反向代理

```bash
# 创建Nginx配置
cat > /etc/nginx/sites-available/log-analyzer << EOF
server {
    listen 80;
    server_name log-analyzer.example.com;

    # 重定向HTTP到HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl;
    server_name log-analyzer.example.com;

    # SSL配置
    ssl_certificate /etc/letsencrypt/live/log-analyzer.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/log-analyzer.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # 静态文件
    location / {
        root /opt/log_analyzer/web/static;
        try_files \$uri \$uri/ /index.html;
    }

    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/api/health;
        access_log off;
    }
}
EOF

# 启用站点
ln -s /etc/nginx/sites-available/log-analyzer /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

#### 4.3.6 配置SSL证书

```bash
# 申请Let's Encrypt证书
certbot --nginx -d log-analyzer.example.com

# 设置自动续期
crontab -e
# 添加：0 3 * * * /usr/bin/certbot renew --quiet
```

### 4.4 回滚机制

#### 4.4.1 版本回滚步骤

```bash
# 1. 停止当前服务
systemctl stop log-analyzer

# 2. 恢复旧版本代码
cd /opt/log_analyzer
git checkout v2.4.0

# 3. 恢复对应依赖
pip install -r requirements.txt

# 4. 恢复旧版本配置（如有必要）
cp config/config.json.backup config/config.json

# 5. 启动服务
systemctl start log-analyzer

# 6. 验证回滚
curl -s http://localhost:8000/api/health
```

#### 4.4.2 数据备份策略

```bash
# 创建备份脚本
cat > /opt/log_analyzer/scripts/backup.sh << EOF
#!/bin/bash
BACKUP_DIR="/backup/log_analyzer"
DATE=\$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p \$BACKUP_DIR

# 备份数据目录
tar -czf \$BACKUP_DIR/data_\$DATE.tar.gz /opt/log_analyzer/data

# 备份配置文件
tar -czf \$BACKUP_DIR/config_\$DATE.tar.gz /opt/log_analyzer/config

# 备份任务文件
tar -czf \$BACKUP_DIR/tasks_\$DATE.tar.gz /opt/log_analyzer/tasks

# 保留最近7天的备份
find \$BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: \$BACKUP_DIR"
EOF

chmod +x /opt/log_analyzer/scripts/backup.sh

# 添加到crontab
crontab -e
# 添加：0 2 * * * /opt/log_analyzer/scripts/backup.sh
```

---

## 5. 部署自动化配置

### 5.1 CI/CD流程设计

#### 5.1.1 流程架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  代码提交    │───▶│   CI构建     │───▶│   测试验证   │───▶│   部署发布   │
│  (Git Push) │    │ (GitHub Actions)│    │ (单元/集成)  │    │ (生产环境)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  镜像构建    │
                   │ (Docker)    │
                   └─────────────┘
```

#### 5.1.2 GitHub Actions配置

```yaml
# .github/workflows/deploy.yml
name: Deploy Log Analyzer

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run unit tests
        run: pytest tests/ -v --tb=short
      
      - name: Run performance tests
        run: python tests/concurrency_test.py
      
      - name: Build Docker image
        run: docker build -t log-analyzer:${{ github.sha }} .
      
      - name: Push to registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Push image
        run: |
          docker tag log-analyzer:${{ github.sha }} ghcr.io/your-repo/log-analyzer:${{ github.sha }}
          docker tag log-analyzer:${{ github.sha }} ghcr.io/your-repo/log-analyzer:latest
          docker push ghcr.io/your-repo/log-analyzer:${{ github.sha }}
          docker push ghcr.io/your-repo/log-analyzer:latest

  deploy-test:
    needs: build
    runs-on: ubuntu-latest
    environment: test
    steps:
      - name: Deploy to test environment
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.TEST_HOST }}
          username: ${{ secrets.TEST_USER }}
          key: ${{ secrets.TEST_SSH_KEY }}
          script: |
            cd /opt/log_analyzer
            git pull origin main
            docker-compose down
            docker-compose up -d
            sleep 10
            curl -s http://localhost:8000/api/health

  deploy-prod:
    needs: deploy-test
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy to production
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /opt/log_analyzer
            docker pull ghcr.io/your-repo/log-analyzer:latest
            docker-compose down
            docker-compose up -d
            sleep 15
            curl -s http://localhost:8000/api/health
```

### 5.2 部署脚本编写

#### 5.2.1 启动脚本

```bash
#!/bin/bash
# scripts/start.sh

set -e

echo "📊 Starting Log Analyzer Service..."
echo "----------------------------------------"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.10 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 检查依赖
echo "Checking dependencies..."
pip check || pip install -r requirements.txt

# 创建必要目录
mkdir -p data/uploads data/reports data/tasks data/action_logs logs

# 启动服务
echo "Starting server on http://localhost:8000..."
uvicorn web.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --limit-concurrency 200 \
    --backlog 2048 \
    --timeout-keep-alive 30
```

#### 5.2.2 停止脚本

```bash
#!/bin/bash
# scripts/stop.sh

echo "🛑 Stopping Log Analyzer Service..."

# 通过PID停止
PID=$(ps aux | grep "uvicorn web.app:app" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    kill -TERM $PID
    sleep 5
    # 强制终止
    kill -KILL $PID 2>/dev/null || true
    echo "Service stopped successfully"
else
    echo "No running service found"
fi
```

#### 5.2.3 健康检查脚本

```bash
#!/bin/bash
# scripts/health_check.sh

URL="${1:-http://localhost:8000/api/health}"
TIMEOUT=10

echo "🔍 Performing health check..."

response=$(curl -s -m $TIMEOUT $URL)

if [ $? -ne 0 ]; then
    echo "❌ Connection failed"
    exit 1
fi

code=$(echo $response | python3 -c "import sys,json; print(json.load(sys.stdin)['code'])")

if [ "$code" -eq 0 ]; then
    echo "✅ Service is healthy"
    exit 0
else
    echo "❌ Service is unhealthy: $response"
    exit 1
fi
```

#### 5.2.4 Docker Compose配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  log-analyzer:
    image: ghcr.io/your-repo/log-analyzer:latest
    container_name: log-analyzer
    ports:
      - "8000:8000"
    volumes:
      - ./data/uploads:/app/data/uploads
      - ./data/reports:/app/data/reports
      - ./data/tasks:/app/data/tasks
      - ./data/action_logs:/app/data/action_logs
      - ./logs:/app/logs
      - ./config:/app/config
    environment:
      - PYTHONPATH=/app
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 6. 监控与日志配置

### 6.1 系统日志配置

#### 6.1.1 日志级别说明

| 级别 | 说明 | 适用场景 |
|------|------|---------|
| DEBUG | 详细调试信息 | 开发环境 |
| INFO | 一般运行信息 | 生产环境 |
| WARNING | 警告信息 | 生产环境 |
| ERROR | 错误信息 | 所有环境 |
| CRITICAL | 严重错误 | 所有环境 |

#### 6.1.2 日志配置示例

```python
# web/app.py 日志配置
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'logs/web.log',
            maxBytes=1024 * 1024 * 50,  # 50MB
            backupCount=10,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

#### 6.1.3 日志轮转配置

```bash
# /etc/logrotate.d/log-analyzer
/opt/log_analyzer/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 loganalyzer loganalyzer
    postrotate
        systemctl reload log-analyzer > /dev/null 2>&1 || true
    endscript
}
```

### 6.2 性能监控

#### 6.2.1 监控指标

| 指标 | 说明 | 采集方式 |
|------|------|---------|
| CPU使用率 | 进程CPU占用 | ps, top |
| 内存使用率 | 进程内存占用 | ps, free |
| 请求响应时间 | API响应耗时 | Prometheus |
| QPS | 每秒请求数 | Prometheus |
| 错误率 | 请求失败比例 | Prometheus |
| 任务队列长度 | 待处理任务数 | 应用内部统计 |

#### 6.2.2 Prometheus配置

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'log-analyzer'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /api/metrics
```

#### 6.2.3 监控脚本

```bash
#!/bin/bash
# scripts/monitor.sh

echo "=== Log Analyzer Monitor ==="
echo "Time: $(date)"
echo ""

# CPU使用率
echo "CPU Usage:"
top -bn1 | grep "uvicorn" | head -5

echo ""
echo "Memory Usage:"
free -h

echo ""
echo "Service Status:"
systemctl status log-analyzer | grep -E "(Active|Main PID)"

echo ""
echo "Recent Errors:"
tail -20 /opt/log_analyzer/logs/web.log | grep -i error

echo ""
echo "Health Check:"
curl -s http://localhost:8000/api/health
```

### 6.3 告警配置

#### 6.3.1 告警规则

| 告警项 | 阈值 | 级别 | 通知方式 |
|--------|------|------|---------|
| 服务不可用 | 连续3次健康检查失败 | 严重 | 邮件+短信 |
| CPU使用率 | >80%持续5分钟 | 警告 | 邮件 |
| 内存使用率 | >85%持续5分钟 | 警告 | 邮件 |
| 响应时间 | P95 > 500ms | 警告 | 邮件 |
| 错误率 | >5% | 严重 | 邮件+短信 |

#### 6.3.2 告警脚本

```bash
#!/bin/bash
# scripts/alert.sh

ALERT_EMAIL="admin@example.com"
ALERT_SUBJECT="Log Analyzer Alert"

# 检查服务健康
if ! curl -s -f http://localhost:8000/api/health > /dev/null; then
    echo "Service is down!" | mail -s "$ALERT_SUBJECT: Service Unavailable" $ALERT_EMAIL
    exit 1
fi

# 检查内存使用率
MEM_USAGE=$(free | grep Mem | awk '{print $3/$2 * 100.0}')
if (( $(echo "$MEM_USAGE > 85" | bc -l) )); then
    echo "Memory usage is ${MEM_USAGE}%" | mail -s "$ALERT_SUBJECT: High Memory Usage" $ALERT_EMAIL
fi

# 检查CPU使用率
CPU_USAGE=$(top -bn1 | grep Cpu | awk '{print $2}')
if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
    echo "CPU usage is ${CPU_USAGE}%" | mail -s "$ALERT_SUBJECT: High CPU Usage" $ALERT_EMAIL
fi
```

---

## 7. 配置管理策略

### 7.1 环境配置分离

#### 7.1.1 配置文件结构

```
config/
├── config.json           # 通用配置（不包含敏感信息）
├── config.test.json      # 测试环境配置
├── config.prod.json      # 生产环境配置
└── .env                  # 环境变量（敏感信息）
```

#### 7.1.2 环境变量管理

```bash
# .env 文件示例
LLM_API_KEY=your-secret-api-key
DATABASE_PASSWORD=your-db-password
SECRET_KEY=your-secret-key
```

#### 7.1.3 配置加载优先级

1. 环境变量（最高优先级）
2. 命令行参数
3. 环境特定配置文件（config.{env}.json）
4. 默认配置文件（config.json）

### 7.2 敏感信息管理

#### 7.2.1 敏感信息清单

| 敏感项 | 存储位置 | 加密方式 |
|--------|---------|---------|
| LLM API Key | 环境变量 | 不存储在代码库 |
| 数据库密码 | 环境变量 | 不存储在代码库 |
| 管理员凭证 | 环境变量 | 不存储在代码库 |

#### 7.2.2 安全实践

- **禁止**在代码中硬编码敏感信息
- **禁止**将敏感配置提交到版本控制
- **必须**使用环境变量或密钥管理服务
- **定期**轮换敏感凭证

### 7.3 配置变更流程

```
┌──────────────────┐
│ 1. 变更请求      │
│ (提交PR)         │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 2. 代码审查      │
│ (团队审核)       │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 3. 测试环境验证   │
│ (部署到测试)     │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 4. 生产环境部署   │
│ (蓝绿部署)       │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 5. 监控验证      │
│ (确认正常运行)   │
└──────────────────┘
```

---

## 8. 附录

### A. 快速部署命令

```bash
# 一键部署测试环境
curl -s https://raw.githubusercontent.com/your-repo/log_analyzer/main/scripts/deploy-test.sh | bash

# 一键部署生产环境
curl -s https://raw.githubusercontent.com/your-repo/log_analyzer/main/scripts/deploy-prod.sh | bash
```

### B. 常用命令参考

| 命令 | 说明 |
|------|------|
| `systemctl start log-analyzer` | 启动服务 |
| `systemctl stop log-analyzer` | 停止服务 |
| `systemctl restart log-analyzer` | 重启服务 |
| `systemctl status log-analyzer` | 查看状态 |
| `journalctl -u log-analyzer -f` | 查看实时日志 |
| `curl http://localhost:8000/api/health` | 健康检查 |

### C. 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 80 | Nginx | HTTP入口 |
| 443 | Nginx | HTTPS入口 |
| 8000 | Uvicorn | 应用服务 |

### D. 目录权限

```bash
# 设置正确的目录权限
chown -R loganalyzer:loganalyzer /opt/log_analyzer
chmod -R 755 /opt/log_analyzer
chmod -R 775 /opt/log_analyzer/data
```

### E. 故障排查

#### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 服务无法启动 | 端口被占用 | 检查端口占用：`netstat -tlnp | grep 8000` |
| 依赖安装失败 | 缺少系统依赖 | 安装依赖：`apt install -y python3-dev` |
| API无响应 | 配置错误 | 检查日志：`tail -20 logs/web.log` |
| 文件上传失败 | 权限不足 | 检查data目录权限 |
| SSL证书过期 | 证书未续期 | 运行：`certbot renew` |

---

*本文档最后更新于 2026-06-05*
