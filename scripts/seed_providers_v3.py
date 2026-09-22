# -*- coding: utf-8 -*-
"""
种子脚本 v3：根据 模型.docx 5 张图片提取的全部供应商刷新数据库
图片1: 34个 LLM 供应商
图片2: 14个 Embedding/Rerank 供应商
图片3: 8个 TTS 供应商
图片4: 5个 STT 供应商
图片5: 5个 额外 LLM 供应商
总计: 66 个唯一供应商
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from config import get_db

PROVIDERS = [
    # ==================== 图片1: LLM 供应商（34个） ====================
    {"n":"360ai","l":"360 AI","d":"360GPT、360AI 搜索等大模型服务","i":"360","c":"#10B981","t":["llm"],"u":"https://api.360.cn/v1","h":"https://ai.360.cn/"},
    {"n":"anthropic","l":"Anthropic","d":"Claude 3.5 Sonnet、Claude 3 Opus 等安全 AI 模型","i":"🟠","c":"#D4A574","t":["llm"],"u":"https://api.anthropic.com","h":"https://console.anthropic.com/settings/keys"},
    {"n":"anyscale","l":"Anyscale","d":"基于 Ray 的分布式 AI 平台，支持 Llama、Mistral 等","i":"⚡","c":"#6366F1","t":["llm"],"u":"https://api.endpoints.anyscale.com/v1","h":"https://app.anyscale.com/credentials"},
    {"n":"bedrock","l":"AWS Bedrock","d":"亚马逊托管 AI 服务，支持 Claude、Llama、Mistral 等","i":"🅰️","c":"#FF9900","t":["llm"],"u":"","h":"https://aws.amazon.com/bedrock/"},
    {"n":"sagemaker","l":"AWS SageMaker","d":"亚马逊机器学习平台，支持自定义模型部署","i":"🅰️","c":"#232F3E","t":["llm"],"u":"","h":"https://aws.amazon.com/sagemaker/"},
    {"n":"azure_openai","l":"Azure OpenAI","d":"通过 Azure 托管的 OpenAI 模型服务，企业级安全","i":"🔷","c":"#0078D4","t":["llm"],"u":"","h":"https://azure.microsoft.com/products/ai-services/openai-service"},
    {"n":"baidu_qianfan","l":"Baidu Qianfan","d":"百度文心大模型 ERNIE 系列，支持多种 AI 能力","i":"🐾","c":"#2563EB","t":["llm","embedding","rerank"],"u":"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop","h":"https://console.bce.baidu.com/qianfan/"},
    {"n":"baichuan","l":"Baichuan","d":"Baichuan4、Baichuan2 等大语言模型","i":"⚪","c":"#EF4444","t":["llm"],"u":"https://api.baichuan-ai.com/v1","h":"https://platform.baichuan-ai.com/console/apikey"},
    {"n":"cloudflare_workers_ai","l":"Cloudflare Workers AI","d":"边缘计算 AI 推理，支持 Llama、Mistral 等开源模型","i":"☁️","c":"#F6821F","t":["llm"],"u":"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1","h":"https://developers.cloudflare.com/workers-ai/"},
    {"n":"cohere","l":"Cohere","d":"Command R/R+ 等企业级大语言模型，擅长 RAG","i":"🔵","c":"#39594D","t":["llm","embedding","rerank"],"u":"https://api.cohere.com/v1","h":"https://dashboard.cohere.com/api-keys"},
    {"n":"deepseek","l":"DeepSeek","d":"DeepSeek-V3、DeepSeek-R1 等高性价比推理模型","i":"🔵","c":"#4D6BFE","t":["llm"],"u":"https://api.deepseek.com/v1","h":"https://platform.deepseek.com/api_keys"},
    {"n":"google","l":"Google Gemini","d":"Gemini Pro、Gemini Ultra 等多模态大语言模型","i":"🔴","c":"#4285F4","t":["llm"],"u":"https://generativelanguage.googleapis.com","h":"https://aistudio.google.com/app/apikey"},
    {"n":"groq","l":"Groq","d":"基于 LPU 的超高速推理引擎，支持 Llama、Mixtral 等","i":"🔶","c":"#F59E0B","t":["llm"],"u":"https://api.groq.com/openai/v1","h":"https://console.groq.com/keys"},
    {"n":"huggingface","l":"Hugging Face","d":"全球最大的开源模型社区，支持 Inference API","i":"🤗","c":"#FFD21E","t":["llm","embedding"],"u":"https://api-inference.huggingface.co/models","h":"https://huggingface.co/settings/tokens"},
    {"n":"spark","l":"iFlytek Spark","d":"讯飞星火大模型，支持语音、图像、文本多模态","i":"⭐","c":"#EF4444","t":["llm"],"u":"https://spark-api-open.xf-yun.com/v1","h":"https://console.xfyun.cn/services/cbm"},
    {"n":"lingyiwanwu","l":"Lingyiwanwu","d":"Yi 系列开源大语言模型，支持中英文","i":"🌀","c":"#8B5CF6","t":["llm"],"u":"https://api.lingyiwanwu.com/v1","h":"https://platform.lingyiwanwu.com/apikeys"},
    {"n":"localai","l":"LocalAI","d":"本地 OpenAI 兼容 API，支持 GGML/GGUF 格式模型","i":"🏠","c":"#10B981","t":["llm","embedding"],"u":"http://localhost:8080/v1","h":"https://localai.io/"},
    {"n":"ollama","l":"Ollama","d":"本地 LLM 部署工具，支持 Llama、Mistral、Qwen 等开源模型","i":"🦙","c":"#000000","t":["llm","embedding"],"u":"http://localhost:11434/v1","h":"https://ollama.com/"},
    {"n":"minimax","l":"MiniMax","d":"abab 系列大语言模型，支持多轮对话","i":"🟤","c":"#8B5CF6","t":["llm"],"u":"https://api.minimax.chat/v1","h":"https://platform.minimax.chat/user-center/basic-information/interface-key"},
    {"n":"mistral","l":"Mistral AI","d":"Mistral Large、Mixtral 等欧洲高性能开源模型","i":"🌊","c":"#FF7000","t":["llm"],"u":"https://api.mistral.ai/v1","h":"https://console.mistral.ai/api-keys/"},
    {"n":"moonshot","l":"Moonshot (Kimi)","d":"Kimi 大模型，支持超长上下文窗口（128K+）","i":"🌙","c":"#6366F1","t":["llm"],"u":"https://api.moonshot.cn/v1","h":"https://platform.moonshot.cn/console/api-keys"},
    {"n":"nvidia_nim","l":"NVIDIA NIM","d":"NVIDIA 推理微服务，支持 Llama、Mistral 等优化模型","i":"🎮","c":"#76B900","t":["llm"],"u":"https://integrate.api.nvidia.com/v1","h":"https://catalog.ngc.nvidia.com/"},
    {"n":"openai","l":"OpenAI","d":"GPT-4o、GPT-4o-mini、o1 系列等先进大语言模型","i":"🟢","c":"#10A37F","t":["llm"],"u":"https://api.openai.com/v1","h":"https://platform.openai.com/api-keys"},
    {"n":"openllm","l":"OpenLLM","d":"BentoML 开源 LLM 部署框架，支持 vLLM/TGI 后端","i":"📦","c":"#3B82F6","t":["llm"],"u":"http://localhost:3000/v1","h":"https://docs.bentoml.com/"},
    {"n":"perplexity","l":"Perplexity","d":"基于搜索的 AI 推理模型，支持实时信息检索","i":"🔮","c":"#06B6D4","t":["llm"],"u":"https://api.perplexity.ai","h":"https://www.perplexity.ai/settings/api"},
    {"n":"replicate","l":"Replicate","d":"开源模型托管平台，支持数千个机器学习模型","i":"🔄","c":"#10B981","t":["llm"],"u":"https://api.replicate.com/v1","h":"https://replicate.com/account/api-tokens"},
    {"n":"sensenova","l":"SenseNova","d":"商汤科技大模型，支持多模态与代码生成","i":"🔬","c":"#6366F1","t":["llm"],"u":"https://api.sensenova.cn/v1/llm","h":"https://console.sensecore.cn/"},
    {"n":"stability_ai","l":"Stability AI","d":"Stable Diffusion 图像生成与 Stable LM 语言模型","i":"🎨","c":"#8B5CF6","t":["llm"],"u":"https://api.stability.ai","h":"https://platform.stability.ai/account/keys"},
    {"n":"stepfun","l":"StepFun","d":"Step 系列大语言模型，支持多模态与超长上下文","i":"🚀","c":"#F59E0B","t":["llm"],"u":"https://api.stepfun.com/v1","h":"https://platform.stepfun.com/interface-key"},
    {"n":"together_ai","l":"Together AI","d":"开源模型云平台，支持 Llama、Mistral、Qwen 等","i":"🤝","c":"#10B981","t":["llm"],"u":"https://api.together.xyz/v1","h":"https://api.together.xyz/settings/api-keys"},
    {"n":"tongyi","l":"Tongyi (Qwen)","d":"通义千问 Qwen 系列大语言模型，支持中英文","i":"🟣","c":"#6366F1","t":["llm"],"u":"https://dashscope.aliyuncs.com/compatible-mode/v1","h":"https://dashscope.console.aliyun.com/apiKey"},
    {"n":"upstage","l":"Upstage","d":"Solar 大语言模型，擅长英语与韩语处理","i":"☀️","c":"#F59E0B","t":["llm"],"u":"https://api.upstage.ai/v1/solar","h":"https://console.upstage.ai/api-keys"},
    {"n":"volcengine","l":"Volcengine","d":"字节跳动旗下云平台，提供豆包大模型等 AI 服务","i":"🌋","c":"#3B82F6","t":["llm","embedding"],"u":"https://ark.cn-beijing.volces.com/api/v3","h":"https://console.volcengine.com/ark/"},
    {"n":"xinference","l":"Xinference","d":"本地开源模型部署框架，支持 LLM、Embedding、Rerank","i":"🧠","c":"#6366F1","t":["llm","embedding","rerank"],"u":"http://localhost:9997/v1","h":"https://inference.readthedocs.io/"},
    {"n":"zhipuai","l":"Zhipu AI (GLM)","d":"GLM-4、GLM-4V 系列大语言模型与多模态模型","i":"🟡","c":"#3B82F6","t":["llm"],"u":"https://open.bigmodel.cn/api/paas/v4","h":"https://open.bigmodel.cn/usercenter/apikeys"},

    # ==================== 图片2: Embedding/Rerank 供应商（14个） ====================
    {"n":"bge_reranker","l":"BGE Reranker","d":"BGE-reranker-v2-m3 等中英文 Rerank 模型","i":"B","c":"#3B82F6","t":["rerank"],"u":"http://localhost:9997/v1","h":"https://github.com/FlagOpen/FlagEmbedding"},
    {"n":"jina","l":"Jina AI","d":"jina-embeddings-v3 等多语言 Embedding 模型","i":"J","c":"#FF6B6B","t":["embedding","rerank"],"u":"https://api.jina.ai/v1","h":"https://jina.ai/"},
    {"n":"tongyi_embedding","l":"Tongyi Embedding","d":"text-embedding-v1/v2/v3 等通义千问 Embedding 模型","i":"🟣","c":"#6366F1","t":["embedding"],"u":"https://dashscope.aliyuncs.com/compatible-mode/v1","h":"https://dashscope.console.aliyun.com/apiKey"},
    {"n":"volcengine_embedding","l":"Volcengine Embedding","d":"火山引擎 Doubao Embedding 模型","i":"🌋","c":"#3B82F6","t":["embedding"],"u":"https://ark.cn-beijing.volces.com/api/v3","h":"https://console.volcengine.com/ark/"},
    {"n":"zhipuai_embedding","l":"Zhipu AI Embedding","d":"Embedding-2、Embedding-3 等向量化模型","i":"🟡","c":"#3B82F6","t":["embedding"],"u":"https://open.bigmodel.cn/api/paas/v4","h":"https://open.bigmodel.cn/usercenter/apikeys"},
    {"n":"localai_embedding","l":"LocalAI Embedding","d":"本地部署的 Embedding 模型，支持 GGML/GGUF 格式","i":"🏠","c":"#10B981","t":["embedding"],"u":"http://localhost:8080/v1","h":"https://localai.io/"},
    {"n":"xinference_embedding","l":"Xinference Embedding","d":"本地开源 Embedding 模型部署框架","i":"🧠","c":"#6366F1","t":["embedding"],"u":"http://localhost:9997/v1","h":"https://inference.readthedocs.io/"},
    {"n":"cohere_embedding","l":"Cohere Embedding","d":"embed-multilingual-v3.0 等多语言 Embedding 模型","i":"🔵","c":"#39594D","t":["embedding"],"u":"https://api.cohere.com/v1","h":"https://dashboard.cohere.com/api-keys"},
    {"n":"mistral_embedding","l":"Mistral Embedding","d":"mistral-embed 等 Embedding 模型","i":"🌊","c":"#FF7000","t":["embedding"],"u":"https://api.mistral.ai/v1","h":"https://console.mistral.ai/api-keys/"},
    {"n":"huggingface_embedding","l":"Hugging Face Embedding","d":"sentence-transformers 等开源 Embedding 模型","i":"🤗","c":"#FFD21E","t":["embedding"],"u":"https://api-inference.huggingface.co/models","h":"https://huggingface.co/settings/tokens"},
    {"n":"together_embedding","l":"Together AI Embedding","d":"M2-BERT、e5 等开源 Embedding 模型","i":"🤝","c":"#10B981","t":["embedding"],"u":"https://api.together.xyz/v1","h":"https://api.together.xyz/settings/api-keys"},
    {"n":"openai_embedding","l":"OpenAI Embedding","d":"text-embedding-3-small/large 等 OpenAI Embedding 模型","i":"🟢","c":"#10A37F","t":["embedding"],"u":"https://api.openai.com/v1","h":"https://platform.openai.com/api-keys"},
    {"n":"azure_embedding","l":"Azure OpenAI Embedding","d":"通过 Azure 托管的 OpenAI Embedding 模型","i":"🔷","c":"#0078D4","t":["embedding"],"u":"","h":"https://azure.microsoft.com/products/ai-services/openai-service"},
    {"n":"baidu_embedding","l":"百度千帆 Embedding","d":"bce-reranker-base 等百度 Embedding/Rerank 模型","i":"🐾","c":"#2563EB","t":["embedding","rerank"],"u":"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop","h":"https://console.bce.baidu.com/qianfan/"},

    # ==================== 图片3: TTS 供应商（8个） ====================
    {"n":"azure_tts","l":"Azure TTS","d":"Azure 认知服务语音合成，支持多种语言","i":"🔷","c":"#0078D4","t":["tts"],"u":"","h":"https://azure.microsoft.com/products/ai-services/speech"},
    {"n":"baidu_tts","l":"百度语音合成","d":"百度文心语音合成服务，支持多种音色","i":"🐾","c":"#2563EB","t":["tts"],"u":"https://tsip.baidu.com","h":"https://console.bce.baidu.com/ai/"},
    {"n":"elevenlabs","l":"ElevenLabs","d":"高质量多语言语音合成，支持声音克隆","i":"🎙️","c":"#8B5CF6","t":["tts"],"u":"https://api.elevenlabs.io/v1","h":"https://elevenlabs.io/app/speech-synthesis"},
    {"n":"localai_tts","l":"LocalAI TTS","d":"本地部署的 TTS 模型","i":"🏠","c":"#10B981","t":["tts"],"u":"http://localhost:8080/v1","h":"https://localai.io/"},
    {"n":"minimax_tts","l":"MiniMax TTS","d":"MiniMax 语音合成服务，支持多语言","i":"🟤","c":"#8B5CF6","t":["tts"],"u":"https://api.minimax.chat/v1","h":"https://platform.minimax.chat/"},
    {"n":"openai_tts","l":"OpenAI TTS","d":"tts-1、tts-1-hd 等文本转语音模型","i":"🟢","c":"#10A37F","t":["tts"],"u":"https://api.openai.com/v1","h":"https://platform.openai.com/api-keys"},
    {"n":"tongyi_tts","l":"Tongyi TTS","d":"通义千问语音合成服务","i":"🟣","c":"#6366F1","t":["tts"],"u":"https://dashscope.aliyuncs.com/compatible-mode/v1","h":"https://dashscope.console.aliyun.com/apiKey"},
    {"n":"volcengine_tts","l":"Volcengine TTS","d":"火山引擎语音合成服务，支持多种音色","i":"🌋","c":"#3B82F6","t":["tts"],"u":"https://ark.cn-beijing.volces.com/api/v3","h":"https://console.volcengine.com/ark/"},

    # ==================== 图片4: STT 供应商（5个） ====================
    {"n":"azure_stt","l":"Azure STT","d":"Azure 认知服务语音转文本","i":"🔷","c":"#0078D4","t":["stt"],"u":"","h":"https://azure.microsoft.com/products/ai-services/speech"},
    {"n":"baidu_stt","l":"百度语音识别","d":"百度文心语音识别服务","i":"🐾","c":"#2563EB","t":["stt"],"u":"https://tsip.baidu.com","h":"https://console.bce.baidu.com/ai/"},
    {"n":"localai_stt","l":"LocalAI STT","d":"本地部署的 STT 模型","i":"🏠","c":"#10B981","t":["stt"],"u":"http://localhost:8080/v1","h":"https://localai.io/"},
    {"n":"openai_stt","l":"OpenAI Whisper","d":"whisper-1 语音转文本模型","i":"🟢","c":"#10A37F","t":["stt"],"u":"https://api.openai.com/v1","h":"https://platform.openai.com/api-keys"},
    {"n":"volcengine_stt","l":"Volcengine STT","d":"火山引擎语音识别服务","i":"🌋","c":"#3B82F6","t":["stt"],"u":"https://ark.cn-beijing.volces.com/api/v3","h":"https://console.volcengine.com/ark/"},

    # ==================== 图片5: 额外 LLM 供应商（5个） ====================
    {"n":"tencent_hunyuan","l":"Tencent Hunyuan","d":"腾讯混元大模型，支持文本生成、图像理解等","i":"🐧","c":"#10B981","t":["llm"],"u":"https://api.hunyuan.cloud.tencent.com/v1","h":"https://console.cloud.tencent.com/hunyuan/"},
    {"n":"baidu_qianfan_llm","l":"百度文心一言","d":"ERNIE-Bot 4.0、ERNIE-Speed 等大语言模型","i":"文","c":"#2563EB","t":["llm"],"u":"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat","h":"https://console.bce.baidu.com/qianfan/"},
    {"n":"xunfei_spark","l":"讯飞星火大模型","d":"Spark 4.0、Spark Pro 等大语言模型","i":"星","c":"#EF4444","t":["llm"],"u":"https://spark-api-open.xf-yun.com/v1","h":"https://console.xfyun.cn/"},
    {"n":"hunyuan","l":"腾讯混元大模型","d":"混元 Turbo、混元 Pro 等大语言模型","i":"混","c":"#10B981","t":["llm"],"u":"https://api.hunyuan.cloud.tencent.com/v1","h":"https://console.cloud.tencent.com/hunyuan"},
    {"n":"loong","l":"Loong (龙猫)","d":"龙猫大语言模型，支持中英文对话与代码生成","i":"🐉","c":"#6366F1","t":["llm"],"u":"https://api.loong.ai/v1","h":"https://loong.ai/"},
]


def main():
    db = get_db()
    try:
        cur = db.cursor()

        # 1. 删除旧数据
        cur.execute("DELETE FROM model_provider_configs")
        cur.execute("DELETE FROM model_definitions")
        db.commit()
        print("[清理] 已删除旧供应商数据")

        # 2. 插入新供应商
        inserted = 0
        for p in PROVIDERS:
            try:
                cur.execute("""
                    INSERT INTO model_provider_configs
                    (provider_name, provider_label, description, icon, icon_background,
                     credential_type, default_base_url, supported_model_types,
                     help_url, help_text, is_built_in, status, install_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 1, 0)
                """, (
                    p["n"], p["l"], p["d"], p["i"], p["c"],
                    "api_key", p["u"], json.dumps(p["t"], ensure_ascii=False),
                    p.get("h",""), p.get("ht","")
                ))

                # 为每个供应商插入默认模型定义
                _insert_default_models(cur, p["n"], p["l"], p["t"])
                inserted += 1
            except Exception as e:
                print(f"[警告] 插入 {p['n']} 失败: {e}")

        db.commit()
        print(f"[完成] 成功插入 {inserted} 个供应商")

    finally:
        db.close()


def _insert_default_models(cur, provider_name, label, types):
    """为供应商插入默认模型定义"""
    for t in types:
        if t == "llm":
            cur.execute("""
                INSERT INTO model_definitions
                (provider_name, model_name, model_label, model_type, context_size,
                 max_output_tokens, supports_vision, supports_function_calling, supports_streaming, status)
                VALUES (%s, %s, %s, 'llm', 4096, 2048, 0, 0, 1, 1)
            """, (provider_name, "default", f"{label} Default"))
        elif t == "embedding":
            cur.execute("""
                INSERT INTO model_definitions
                (provider_name, model_name, model_label, model_type,
                 context_size, status)
                VALUES (%s, %s, %s, 'embedding', 8191, 1)
            """, (provider_name, "default-embedding", f"{label} Embedding"))
        elif t == "rerank":
            cur.execute("""
                INSERT INTO model_definitions
                (provider_name, model_name, model_label, model_type, status)
                VALUES (%s, %s, %s, 'rerank', 1)
            """, (provider_name, "default-rerank", f"{label} Rerank"))
        elif t == "tts":
            cur.execute("""
                INSERT INTO model_definitions
                (provider_name, model_name, model_label, model_type, status)
                VALUES (%s, %s, %s, 'tts', 1)
            """, (provider_name, "default-tts", f"{label} TTS"))
        elif t == "stt":
            cur.execute("""
                INSERT INTO model_definitions
                (provider_name, model_name, model_label, model_type, status)
                VALUES (%s, %s, %s, 'stt', 1)
            """, (provider_name, "default-stt", f"{label} STT"))


if __name__ == "__main__":
    main()
