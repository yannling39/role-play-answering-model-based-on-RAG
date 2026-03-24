@echo off
rem 设置代码页为UTF-8，解决中文乱码问题
chcp 65001
echo 正在启动猜谜大师API服务器...

rem 确保当前目录正确
cd %~dp0
echo 当前工作目录: %CD%

rem 激活conda环境
call conda activate llamaindex
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 无法激活llamaindex环境
    pause
    exit /b %ERRORLEVEL%
)

rem 安装依赖
echo 正在安装依赖...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo 警告: 依赖安装可能不完整，但仍将继续尝试启动服务器
    echo 如果服务器无法正常启动，请手动执行: pip install -r requirements.txt
    pause
)

rem 检查CUDA支持
python -c "import torch; print('CUDA可用性:', torch.cuda.is_available())"
if %ERRORLEVEL% NEQ 0 (
    echo 警告: 无法检测CUDA支持状态
) else (
    python -c "import torch; is_available = torch.cuda.is_available(); print('CUDA:', '可用' if is_available else '不可用'); print('如果不可用，Embedding将使用CPU模式，速度较慢')"
)

rem 检查配置文件
if not exist "config.json" (
    echo 提示: 未找到config.json配置文件
    echo 如需使用自己的API密钥，请复制config.json.template并填写密钥
)

rem 启动服务器
echo 正在启动Python服务器...
python app.py

if %ERRORLEVEL% NEQ 0 (
    echo 服务器启动失败，请检查错误信息
    pause
)
