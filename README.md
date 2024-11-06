# 奇点AI股票及股指期货复盘及预测系统

> 基于 FastAPI、Tushare 和 OpenAI 的智能股票分析系统，支持股票、期货和指数的技术分析及AI预测。

## 📚 功能特点

- 🔍 支持股票、期货和指数数据分析
- 🤖 集成 OpenAI 进行智能分析和预测
- 📊 提供技术指标可视化
- 📂 支持数据导出和图表展示
- 🐳 完整的 Docker 部署支持

## 🚀 快速开始

### 使用 Docker Compose 部署

1.克隆仓库：

```bash
git clone https://github.com/Baozhi888/stock_app_new.git
cd stock_app_new
```

2.配置环境：

```bash
cp .env.example .env
```

3.编辑 `.env` 文件：

```ini
OPENAI_API_KEY=your_openai_api_key_here
API_URL=your_api_url_here
TUSHARE_TOKEN=your_tushare_token_here
```

4.启动服务：

```bash
docker-compose up -d
```

5.访问应用：

打开浏览器访问 [http://localhost:9008](http://localhost:9008)

### 手动部署

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 💡 使用说明

### 支持的数据类型

| 类型 | 代码格式 | 示例 |
|------|----------|------|
| 股票 | 6位数字 | 000001（平安银行）|
| 期货 | 品种+月份 | IF2403（中金所股指期货）|
| 指数 | 6位数字 | 000300（沪深300）|

### 分析功能

- ⚙️ 技术指标分析（MACD、RSI、布林带等）
- 🧠 AI 驱动的趋势分析
- 💡 交易建议生成
- 📈 图表可视化
- 📊 数据导出

## ⚙️ 环境变量

| 变量名 | 必填 | 描述 | 示例 |
|--------|------|------|------|
| OPENAI_API_KEY | ✅ | OpenAI API密钥 | sk-... |
| API_URL | ✅ | OpenAI API地址 | [https://api.openai.com/v1/chat/completions ]|
| TUSHARE_TOKEN | ✅ | Tushare数据接口令牌 | xxxxxxxxxxxxxxxxxxxxxxxx |

## 📁 目录结构

```plaintext
project_root/
├── .env.example          # 环境变量示例
├── .gitignore           # Git忽略配置
├── docker-compose.yml   # Docker Compose配置
├── Dockerfile          # Docker构建文件
├── requirements.txt    # Python依赖
├── README.md          # 项目说明
├── main.py           # 主入口
├── config.py        # 配置文件
├── data_service.py    # 数据服务
├── analysis_service.py # 分析服务
├── models.py          # 数据模型
├── static/           # 静态文件
│   ├── index.html    # 主页面
│   ├── images/      # 图片目录
│   └── fonts/      # 字体文件
└── output/         # 输出目录
```

## 📖 API 文档

启动服务后，访问以下地址查看 API 文档：

- Swagger UI: [http://localhost:9008/docs](http://localhost:9008/docs)
- ReDoc: [http://localhost:9008/redoc](http://localhost:9008/redoc)

## ❓ 常见问题

### 1. 无法获取数据？

- ✔️ 检查 Tushare Token 是否正确
- ✔️ 确认股票代码格式是否正确
- ✔️ 验证日期范围是否有效

### 2. 分析结果未显示？

- ✔️ 检查 OpenAI API 密钥是否正确
- ✔️ 确认网络连接是否正常
- ✔️ 查看应用日志获取详细错误信息

## 📝 版本历史

### v1.0.0 (2024-02-08)

- 🎉 初始版本发布
- ✨ 支持股票、期货和指数分析
- 🤖 集成 OpenAI 智能分析
- 🐳 Docker 部署支持

## 🤝 贡献指南

1. Fork 项目
1. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
1. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
1. 推送到分支 (`git push origin feature/AmazingFeature`)
1. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

- 👨‍💻 项目维护者：[King John]
- 📧 Email：[kj331704@gmail.com]
- 🔗 项目链接：[https://github.com/Baozhi888/stock_app_new](https://github.com/Baozhi888/stock_app_new)

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [Tushare](https://tushare.pro/)
- [OpenAI](https://openai.com/)
