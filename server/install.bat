@echo off
rem 设置代码页为UTF-8，解决中文乱码问题
chcp 65001
echo ===================================
echo 猜谜大师API服务器 - 高级安装脚本
echo ===================================

rem 确保当前目录正确
cd %~dp0
echo 当前工作目录: %CD%

rem 检查Python版本
echo 检查Python版本...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 未找到Python，请安装Python 3.12
    pause
    exit /b %ERRORLEVEL%
)

rem 检查Conda环境
echo 检查Conda环境...
conda env list | findstr llamaindex
if %ERRORLEVEL% NEQ 0 (
    echo 创建新的Conda环境: llamaindex
    conda create -n llamaindex python=3.12 -y
    if %ERRORLEVEL% NEQ 0 (
        echo 错误: 无法创建Conda环境
        pause
        exit /b %ERRORLEVEL%
    )
)

rem 激活Conda环境
echo 激活Conda环境: llamaindex
call conda activate llamaindex
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 无法激活llamaindex环境
    pause
    exit /b %ERRORLEVEL%
)

rem 清理可能冲突的包
echo 清理可能存在冲突的包...
pip uninstall -y llama-index llama-index-llms-openai

rem 安装依赖
echo 安装依赖...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo 警告: 依赖安装可能不完整
    echo 尝试单独安装核心包...
    pip install fastapi uvicorn
    pip install llama-index-core>=0.12.0,<0.13.0
    pip install llama-index-embeddings-huggingface>=0.5.0,<0.6.0
    pip install llama-index-vector-stores-chroma>=0.4.0,<0.5.0
    pip install chromadb>=0.5.17,<0.6.0
    pip install sentence-transformers==2.7.0
    pause
)

rem 检查Torch和CUDA支持
echo 检查Torch和CUDA支持...
python -c "import torch; print('CUDA可用性:', torch.cuda.is_available())"
if %ERRORLEVEL% NEQ 0 (
    echo 安装PyTorch...
    pip install torch
) else (
    python -c "import torch; is_available = torch.cuda.is_available(); print('CUDA:', '可用' if is_available else '不可用'); print('如果不可用，Embedding将使用CPU模式，速度较慢')"
)

rem 检查配置文件
if not exist "config.json" (
    echo 创建配置文件...
    copy config.json.template config.json
    echo 请编辑config.json文件，填入您的DeepSeek API密钥
    notepad config.json
)

echo ===================================
echo 安装完成！现在可以运行start_server.bat启动服务器
echo ===================================
pause
