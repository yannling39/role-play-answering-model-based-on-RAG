# 猜谜大师常见问题解决

## 依赖问题

如果遇到依赖相关的错误消息，如：
```
处理猜谜请求时出错: 500: 查询处理出错: `llama-index-llms-openai` ... please run `pip install llama-index-llms-openai`
```

请使用以下命令安装缺少的依赖：
```bash
pip install llama-index-llms-openai
```

或者更简单地重新运行`start_server.bat`，它会自动安装更新后的依赖。

## 索引创建问题

如果遇到索引创建失败相关的错误，可以尝试删除现有的索引：
1. 停止服务器
2. 删除`server/chroma_db`目录
3. 重新启动服务器

## API密钥问题

如果遇到API调用失败的错误，可能是API密钥无效。请确保：
1. 复制`server/config.json.template`为`server/config.json`
2. 在`config.json`中填入有效的DeepSeek API密钥

## 嵌入模型问题

如果遇到嵌入模型加载失败的错误，请确保：
1. 检查`app.py`中的`EMBEDDING_MODEL_PATH`是否指向正确的本地模型路径
2. 如果没有该模型，它会自动下载（需要网络连接）

## 网络连接问题

如果遇到DeepSeek API连接失败的错误，请确保：
1. 网络连接正常
2. 如果需要，配置适当的代理设置
