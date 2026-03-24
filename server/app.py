from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import uvicorn
import json
from typing import List, Dict, Any, Optional
import requests
import traceback  # 添加traceback模块
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.settings import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

app = FastAPI()

# 添加CORS中间件，允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应限制为实际域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载本地embedding模型
EMBEDDING_MODEL_PATH = r"C:\Users\Boredommm\.cache\modelscope\hub\models\sentence-transformers\paraphrase-multilingual-MiniLM-L12-v2"

# 定义全局变量，用于存储索引实例
riddle_index = None
minecraft_index = None  # 新增：我的世界知识库索引
magic_index = None  # 新增：哈利波特魔法知识库索引
chroma_client = None
riddle_collection = None
minecraft_collection = None  # 新增：我的世界collection
magic_collection = None  # 新增：哈利波特魔法collection

# 数据目录
DATA_DIR = "../data"
PERSIST_DIR = "./chroma_db"

# 定义聊天请求模型
class ChatRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048

# 尝试从环境变量或配置文件中读取API Key
def get_api_key():
    # 首先尝试从环境变量获取
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    
    # 如果环境变量中没有，尝试从config.json读取
    if not api_key:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    api_key = config.get("DEEPSEEK_API_KEY")
                    if api_key:
                        print("成功从config.json读取API密钥")
            except Exception as e:
                print(f"读取配置文件出错: {e}")
    
    # 如果还是没有，使用默认值
    if not api_key:
        api_key = "DEEPSEEK-API"  # 使用与前端相同的默认API密钥
        print("警告: 使用默认API密钥，建议替换为您自己的密钥")
        print("您可以通过创建config.json文件或设置DEEPSEEK_API_KEY环境变量来配置自己的API密钥")
    
    return api_key

# 初始化函数，用于加载或创建向量索引
def init_index():
    global riddle_index, minecraft_index, magic_index, chroma_client, riddle_collection, minecraft_collection, magic_collection
    
    # 创建embedding模型
    embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL_PATH)
    
    # 初始化Chroma客户端
    chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)
    
    # 设置全局Settings
    Settings.embed_model = embed_model
    # 注意：我们不再设置LLM，因为我们不使用查询引擎，而是直接使用检索器
    
    # ====== 加载猜谜大师知识库 ======
    # 判断是否已经存在索引
    index_exists = False
    if os.path.exists(PERSIST_DIR):
        try:
            # 尝试获取collection
            if "riddles" in [col.name for col in chroma_client.list_collections()]:
                # 检查索引文件是否存在
                if os.path.exists(os.path.join(PERSIST_DIR, "docstore.json")):
                    index_exists = True
        except Exception as e:
            print(f"检查猜谜索引时出错: {e}")
            index_exists = False
    
    if index_exists:
        # 加载已存在的索引
        print("正在加载已存在的猜谜索引...")
        try:
            riddle_collection = chroma_client.get_collection("riddles")
            chroma_vector_store = ChromaVectorStore(chroma_collection=riddle_collection)
            storage_context = StorageContext.from_defaults(vector_store=chroma_vector_store, persist_dir=PERSIST_DIR)
            riddle_index = load_index_from_storage(storage_context)
            print("猜谜索引加载完成")
        except Exception as e:
            print(f"加载猜谜索引时出错: {e}")
            index_exists = False  # 如果加载失败，重新创建索引
    
    if not index_exists:
        # 第一次运行，创建索引
        print("正在创建新的猜谜索引...")
        # 确保数据目录存在
        riddle_data_path = os.path.join(DATA_DIR, "riddle")
        
        # 删除已存在的collection（如果有）
        try:
            if "riddles" in [col.name for col in chroma_client.list_collections()]:
                print("发现已存在的riddles集合，正在删除...")
                chroma_client.delete_collection("riddles")
                print("已删除旧集合")
        except Exception as e:
            print(f"尝试删除旧集合时出错: {e}")
        
        # 读取JSON文件并准备文档
        with open(os.path.join(riddle_data_path, "data.json"), "r", encoding="utf-8") as f:
            riddles_data = json.load(f)
        
        # 将JSON数据转换为文本文档
        documents = []
        from llama_index.core.schema import Document
        for idx, riddle in enumerate(riddles_data):
            doc_text = f"问题: {riddle['instruction']}\n回答: {riddle['output']}"
            documents.append(Document(text=doc_text, id=f"riddle_{idx}"))
        
        # 创建向量存储和索引
        riddle_collection = chroma_client.create_collection("riddles")
        chroma_vector_store = ChromaVectorStore(chroma_collection=riddle_collection)
        storage_context = StorageContext.from_defaults(vector_store=chroma_vector_store)
        # 不再需要传递service_context
        riddle_index = VectorStoreIndex.from_documents(
            documents, 
            storage_context=storage_context
        )
        
        # 保存索引
        storage_context.persist(persist_dir=PERSIST_DIR)
        print("猜谜索引创建完成")
    
    # ====== 加载我的世界知识库 ======
    minecraft_index_exists = False
    minecraft_persist_dir = os.path.join(PERSIST_DIR, "minecraft")
    os.makedirs(minecraft_persist_dir, exist_ok=True)
    
    if os.path.exists(minecraft_persist_dir):
        try:
            # 尝试获取collection
            if "minecraft" in [col.name for col in chroma_client.list_collections()]:
                # 检查索引文件是否存在
                if os.path.exists(os.path.join(minecraft_persist_dir, "docstore.json")):
                    minecraft_index_exists = True
        except Exception as e:
            print(f"检查我的世界索引时出错: {e}")
            minecraft_index_exists = False
    
    if minecraft_index_exists:
        # 加载已存在的索引
        print("正在加载已存在的我的世界索引...")
        try:
            minecraft_collection = chroma_client.get_collection("minecraft")
            minecraft_vector_store = ChromaVectorStore(chroma_collection=minecraft_collection)
            minecraft_storage_context = StorageContext.from_defaults(vector_store=minecraft_vector_store, persist_dir=minecraft_persist_dir)
            minecraft_index = load_index_from_storage(minecraft_storage_context)
            print("我的世界索引加载完成")
        except Exception as e:
            print(f"加载我的世界索引时出错: {e}")
            minecraft_index_exists = False  # 如果加载失败，重新创建索引
    
    if not minecraft_index_exists:
        # 第一次运行，创建索引
        print("正在创建新的我的世界索引...")
        minecraft_data_path = os.path.join(DATA_DIR, "minecraft")
        
        # 删除已存在的collection（如果有）+
        try:
            if "minecraft" in [col.name for col in chroma_client.list_collections()]:
                print("发现已存在的minecraft集合，正在删除...")
                chroma_client.delete_collection("minecraft")
                print("已删除旧集合")
        except Exception as e:
            print(f"尝试删除旧集合时出错: {e}")
        
        # 读取JSON文件并准备文档
        with open(os.path.join(minecraft_data_path, "minecraft.json"), "r", encoding="utf-8") as f:
            minecraft_data = json.load(f)
        
        # 将JSON数据转换为文本文档
        minecraft_documents = []
        from llama_index.core.schema import Document
        for idx, item in enumerate(minecraft_data):
            # 注意这里根据train.json的具体结构进行调整
            if isinstance(item, dict) and "instruction" in item and "output" in item:
                doc_text = f"Question: {item['instruction']}\nAnswer: {item['output']}"
                minecraft_documents.append(Document(text=doc_text, id=f"minecraft_{idx}"))
        
        # 创建向量存储和索引
        minecraft_collection = chroma_client.create_collection("minecraft")
        minecraft_vector_store = ChromaVectorStore(chroma_collection=minecraft_collection)
        minecraft_storage_context = StorageContext.from_defaults(vector_store=minecraft_vector_store)
        minecraft_index = VectorStoreIndex.from_documents(
            minecraft_documents, 
            storage_context=minecraft_storage_context
        )
        
        # 保存索引
        minecraft_storage_context.persist(persist_dir=minecraft_persist_dir)
        print("我的世界索引创建完成")
    
    # ====== 加载哈利波特魔法知识库 ======
    magic_index_exists = False
    magic_persist_dir = os.path.join(PERSIST_DIR, "magic")
    os.makedirs(magic_persist_dir, exist_ok=True)
    
    if os.path.exists(magic_persist_dir):
        try:
            # 尝试获取collection
            if "magic" in [col.name for col in chroma_client.list_collections()]:
                # 检查索引文件是否存在
                if os.path.exists(os.path.join(magic_persist_dir, "docstore.json")):
                    magic_index_exists = True
        except Exception as e:
            print(f"检查哈利波特魔法索引时出错: {e}")
            magic_index_exists = False
    
    if magic_index_exists:
        # 加载已存在的索引
        print("正在加载已存在的哈利波特魔法索引...")
        try:
            magic_collection = chroma_client.get_collection("magic")
            magic_vector_store = ChromaVectorStore(chroma_collection=magic_collection)
            magic_storage_context = StorageContext.from_defaults(vector_store=magic_vector_store, persist_dir=magic_persist_dir)
            magic_index = load_index_from_storage(magic_storage_context)
            print("哈利波特魔法索引加载完成")
        except Exception as e:
            print(f"加载哈利波特魔法索引时出错: {e}")
            magic_index_exists = False  # 如果加载失败，重新创建索引
    
    if not magic_index_exists:
        # 第一次运行，创建索引
        print("正在创建新的哈利波特魔法索引...")
        magic_data_path = os.path.join(DATA_DIR, "magic")
        
        # 删除已存在的collection（如果有）
        try:
            if "magic" in [col.name for col in chroma_client.list_collections()]:
                print("发现已存在的magic集合，正在删除...")
                chroma_client.delete_collection("magic")
                print("已删除旧集合")
        except Exception as e:
            print(f"尝试删除旧集合时出错: {e}")
        
        # 读取JSON文件并准备文档
        with open(os.path.join(magic_data_path, "harry_potter_spells_clean.json"), "r", encoding="utf-8") as f:
            magic_data = json.load(f)
        
        # 将JSON数据转换为文本文档
        magic_documents = []
        from llama_index.core.schema import Document
        for idx, spell in enumerate(magic_data):
            # 注意这里根据harry_potter_spells_clean.json的具体结构进行调整
            if isinstance(spell, dict):
                # 构建魔法咒语文档，根据实际JSON结构调整字段
                fields = []
                for key, value in spell.items():
                    if value and isinstance(value, (str, int, float, bool)):
                        fields.append(f"{key}: {value}")
                
                doc_text = "\n".join(fields)
                magic_documents.append(Document(text=doc_text, id=f"magic_{idx}"))
        
        # 创建向量存储和索引
        magic_collection = chroma_client.create_collection("magic")
        magic_vector_store = ChromaVectorStore(chroma_collection=magic_collection)
        magic_storage_context = StorageContext.from_defaults(vector_store=magic_vector_store)
        magic_index = VectorStoreIndex.from_documents(
            magic_documents, 
            storage_context=magic_storage_context
        )
        
        # 保存索引
        magic_storage_context.persist(persist_dir=magic_persist_dir)
        print("哈利波特魔法索引创建完成")

# 在应用启动时执行初始化
@app.on_event("startup")
async def startup_event():
    init_index()

# 查询接口
@app.post("/query")
async def query_riddle(query: str):
    global riddle_index
    
    try:
        if riddle_index is None:
            raise HTTPException(status_code=500, detail="索引尚未初始化")
        
        # 直接使用向量检索，不依赖LLM进行查询
        # 创建一个检索器而不是查询引擎
        retriever = riddle_index.as_retriever(similarity_top_k=3)
        print(f"执行查询: {query}")
        # 获取最相关的文档节点
        nodes = retriever.retrieve(query)
        
        # 提取检索到的文档内容
        result_texts = []
        for node in nodes:
            result_texts.append(node.get_content())
        
        response_text = "\n\n".join(result_texts)
        print(f"查询结果: {response_text}")
        
        return {"response": response_text}
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"查询过程出错: {str(e)}")
        print(f"详细错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"查询处理出错: {str(e)}")

# 查询我的世界知识库
@app.post("/query-minecraft")
async def query_minecraft(query: str):
    global minecraft_index
    
    try:
        if minecraft_index is None:
            raise HTTPException(status_code=500, detail="我的世界索引尚未初始化")
        
        # 直接使用向量检索，不依赖LLM进行查询
        # 创建一个检索器而不是查询引擎
        retriever = minecraft_index.as_retriever(similarity_top_k=5)  # 多检索几条，增加覆盖面
        print(f"执行我的世界查询: {query}")
        # 获取最相关的文档节点
        nodes = retriever.retrieve(query)
        
        # 提取检索到的文档内容
        result_texts = []
        for node in nodes:
            result_texts.append(node.get_content())
        
        response_text = "\n\n".join(result_texts)
        print(f"我的世界查询结果长度: {len(response_text)}")
        
        return {"response": response_text}
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"我的世界查询过程出错: {str(e)}")
        print(f"详细错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"我的世界查询处理出错: {str(e)}")

# 查询哈利波特魔法知识库
@app.post("/query-magic")
async def query_magic(query: str):
    global magic_index
    
    try:
        if magic_index is None:
            raise HTTPException(status_code=500, detail="哈利波特魔法索引尚未初始化")
        
        # 直接使用向量检索，不依赖LLM进行查询
        # 创建一个检索器而不是查询引擎
        retriever = magic_index.as_retriever(similarity_top_k=4)
        print(f"执行哈利波特魔法查询: {query}")
        # 获取最相关的文档节点
        nodes = retriever.retrieve(query)
        
        # 提取检索到的文档内容
        result_texts = []
        for node in nodes:
            result_texts.append(node.get_content())
        
        response_text = "\n\n".join(result_texts)
        print(f"哈利波特魔法查询结果长度: {len(response_text)}")
        
        return {"response": response_text}
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"哈利波特魔法查询过程出错: {str(e)}")
        print(f"详细错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"哈利波特魔法查询处理出错: {str(e)}")

# DeepSeek API接口
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = get_api_key()  # 使用获取的API密钥

@app.post("/chat/completions")
async def chat_completions(request: ChatRequest):
    # 获取用户的最后一条消息
    user_query = next((msg["content"] for msg in reversed(request.messages) if msg["role"] == "user"), None)
    
    if not user_query:
        raise HTTPException(status_code=400, detail="未找到用户消息")
    
    # 根据不同角色处理请求
    try:
        # 角色1: 猜谜大师
        if "你是模型A，猜谜大师" in request.messages[0]["content"]:
            # 查询本地知识库
            query_response = await query_riddle(user_query)
            context = query_response["response"]
            
            # 限制上下文长度，避免超出API限制
            if len(context) > 2000:
                print(f"上下文过长 ({len(context)} 字符)，截断至2000字符")
                context = context[:1997] + "..."
            
            # 创建给猜谜大师的提示，包含从知识库检索的相关内容
            system_prompt = f"""你是一位猜谜大师，精通各种脑筋急转弯和谜语。
            基于以下参考内容回答用户的问题，如果找到了准确匹配的谜语，请用生动有趣的方式给出答案。
            如果没有找到准确匹配的谜语，可以基于你的知识创造性地回答。
            
            参考内容：
            {context}
            """
            
            # 更新系统提示
            updated_messages = [{"role": "system", "content": system_prompt}]
            # 添加用户查询
            updated_messages.append({"role": "user", "content": user_query})
        
        # 角色2: 我的世界史蒂夫
        elif "你是模型B，专业的技术顾问" in request.messages[0]["content"]:
            # 查询我的世界知识库
            query_response = await query_minecraft(user_query)
            context = query_response["response"]
            
            # 限制上下文长度，避免超出API限制
            if len(context) > 3000:
                print(f"我的世界上下文过长 ({len(context)} 字符)，截断至3000字符")
                context = context[:2997] + "..."
            
            # 创建给我的世界史蒂夫的提示，包含从知识库检索的相关内容
            system_prompt = f"""你是我的世界(Minecraft)中的史蒂夫(Steve)，精通所有与我的世界相关的知识。
            基于以下参考内容（英文）回答用户的问题，理解英文的含义，并翻译成中文。
            当知识库中找到准确的信息时，请基于这些信息回答。如果没有找到相关信息，先道歉！接着可以基于你对我的世界的了解创造性地回答。
            回答时要亲切友好，像一个热爱分享我的世界知识的玩家，可以使用一些与游戏相关的表达方式。
            
            参考内容（英文）：
            {context}
            
            请注意：虽然参考资料是英文的，但你必须用流利的中文回答！
            """
            
            # 更新系统提示
            updated_messages = [{"role": "system", "content": system_prompt}]
            # 添加用户查询
            updated_messages.append({"role": "user", "content": user_query})
        
        # 角色3: 哈利波特魔法师
        elif "你是模型C，幽默的生活小助手" in request.messages[0]["content"]:
            # 查询哈利波特魔法知识库
            query_response = await query_magic(user_query)
            context = query_response["response"]
            
            # 限制上下文长度，避免超出API限制
            if len(context) > 2500:
                print(f"哈利波特魔法上下文过长 ({len(context)} 字符)，截断至2500字符")
                context = context[:2497] + "..."
            
            # 创建给哈利波特魔法师的提示，包含从知识库检索的相关内容
            system_prompt = f"""你是哈利波特世界中的一位魔法师，精通各种魔法咒语和魔法知识。
            基于以下参考内容回答用户的问题，如果找到了相关的魔法咒语或魔法知识，请详细解释其用途和效果。
            回答时要幽默风趣，充满魔法世界的奇妙感，可以偶尔引用哈利波特系列中的经典台词或场景。
            
            参考内容：
            {context}
            """
            
            # 更新系统提示
            updated_messages = [{"role": "system", "content": system_prompt}]
            # 添加用户查询
            updated_messages.append({"role": "user", "content": user_query})
        
        # 其他模型，直接转发原始请求
        else:
            return await forward_to_deepseek(request)
        
        # 调用DeepSeek API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        # 为DeepSeek构建正确的消息格式
        payload = {
            "model": "deepseek-chat",  # 使用DeepSeek Chat模型
            "messages": updated_messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        
        print(f"发送到DeepSeek API的请求: {DEEPSEEK_API_URL}")
        print(f"消息类型: {updated_messages[0]['content'][:50]}...")
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)  # 添加超时设置
        
        if response.status_code != 200:
            print(f"DeepSeek API返回错误，状态码: {response.status_code}")
            print(f"错误详情: {response.text}")
            raise Exception(f"DeepSeek API返回错误 (状态码: {response.status_code}): {response.text}")
        
        response_json = response.json()
        print(f"DeepSeek API响应成功")
        return response_json
            
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"处理角色请求时出错: {str(e)}")
        print(f"详细错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"处理角色请求时出错: {str(e)}")

# 辅助函数：转发请求到DeepSeek API
async def forward_to_deepseek(request: ChatRequest):
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        # 确保消息格式正确
        messages = request.messages
        
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        
        print(f"转发到DeepSeek API，模型: {request.model}")
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)  # 添加超时设置
        
        if response.status_code != 200:
            print(f"DeepSeek API返回错误，状态码: {response.status_code}")
            print(f"错误详情: {response.text}")
            raise Exception(f"DeepSeek API返回错误 (状态码: {response.status_code}): {response.text}")
        
        response_json = response.json()
        print(f"DeepSeek API响应成功")
        return response_json
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"调用DeepSeek API时出错: {str(e)}")
        print(f"详细错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"调用DeepSeek API时出错: {str(e)}")
        
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"调用DeepSeek API时出错: {str(e)}")
        print(f"详细错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"调用DeepSeek API时出错: {str(e)}")

# 测试DeepSeek API连接
@app.get("/test-deepseek")
async def test_deepseek_api():
    """测试DeepSeek API是否可用"""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你好，这是一个测试请求。"},
                {"role": "user", "content": "你好吗？"}
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            return {
                "status": "error",
                "code": response.status_code,
                "message": response.text
            }
        
        return {
            "status": "success",
            "response": response.json()
        }
    except Exception as e:
        error_detail = traceback.format_exc()
        return {
            "status": "error",
            "message": str(e),
            "detail": error_detail
        }

if __name__ == "__main__":
    print("正在启动服务器，监听地址: http://127.0.0.1:8000")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
