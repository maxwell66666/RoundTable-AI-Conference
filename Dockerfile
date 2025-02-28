FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# 将requirements.txt文件复制到工作目录
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件到工作目录
COPY . .

# 运行数据库迁移
RUN python db_migrations.py

# 创建备份目录
RUN mkdir -p /app/backups

# 设置自动备份的cron任务（如果启用）
RUN echo '#!/bin/bash\n\
if [ "$ENABLE_AUTO_BACKUP" = "true" ]; then\n\
  echo "0 2 * * * python /app/backup.py create" | crontab -\n\
  service cron start\n\
fi\n\
\n\
# 启动应用\n\
exec "$@"' > /app/docker-entrypoint.sh \
    && chmod +x /app/docker-entrypoint.sh

# 暴露应用端口
EXPOSE 8000

# 创建数据卷，用于持久化数据
VOLUME ["/app/data", "/app/backups"]

# 设置健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/version || exit 1

# 设置入口点
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# 默认命令
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 