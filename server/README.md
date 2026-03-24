# 猜谜大师服务器

本服务器实现了一个基于本地知识库的猜谜大师角色，可以回答用户提出的脑筋急转弯和谜语问题。

## 运行前准备

1. 确保已安装Python 3.12
2. 建议使用Conda环境：`conda create -n llamaindex python=3.12`
3. 激活环境：`conda activate llamaindex`

## 配置API密钥

本系统使用DeepSeek API进行对话生成。您可以通过以下方式配置API密钥：

1. 复制`config.json.template`为`config.json`，并填入您的DeepSeek API密钥
2. 或者设置环境变量`DEEPSEEK_API_KEY`

## 启动服务器

使用提供的批处理文件启动服务器：

```
start_server.bat
```

该脚本会自动安装所需依赖、检查CUDA支持状态，并启动服务器。

## 故障排除

如果遇到问题，请查看`TROUBLESHOOTING.md`文件获取常见问题的解决方法。

主要的潜在问题：

1. 依赖安装失败：尝试手动执行`pip install -r requirements.txt`
2. API密钥无效：检查`config.json`中的密钥是否正确
3. Embedding模型路径错误：修改`app.py`中的`EMBEDDING_MODEL_PATH`变量

## 系统组件

- **FastAPI**: 提供Web服务
- **LlamaIndex**: 处理知识库向量检索
- **ChromaDB**: 存储向量数据
- **HuggingFace Embedding**: 本地文本向量化
- **DeepSeek API**: 生成对话回复
