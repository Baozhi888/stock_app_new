# 构建阶段
FROM python:3.9-slim-bullseye as builder

WORKDIR /app

# 只安装必要的构建工具
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装依赖
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 最终阶段
FROM python:3.9-slim-bullseye

WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 只安装必要的运行时依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 创建必要的目录
RUN mkdir -p /app/output /app/static/images

# 创建非root用户
RUN useradd -u 1000 -m appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod -R 777 /app/output && \
    chmod -R 777 /app/static/images

# 复制应用程序代码
COPY . .
RUN chown -R appuser:appuser /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 使用非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 运行应用程序
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]