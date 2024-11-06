FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装 SimHei 字体
RUN apt-get update && apt-get install -y fonts-wqy-zenhei

# 安装依赖包
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用程序代码
COPY . .

# 运行应用程序
CMD ["python", "main.py"]