import requests
import json
from typing import Optional, List, Any
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.outputs import Generation
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
import jieba
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from pydantic import Field
token = "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"


class DeepSeekLLM(LLM):
    tokenizer: AutoTokenizer = None
    model: AutoModelForCausalLM = None
    model_name: str = Field(default="deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")
    device: str = Field(default="cpu")

    def __init__(self, model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B", **kwargs):
        super().__init__(model_name=model_name, **kwargs)
        self.model_name = model_name  

        # 自动选择设备
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # 初始化 tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        # 判断是否用量化加载
        use_8bit = torch.cuda.is_available()  # 你之前是这样写的

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            low_cpu_mem_usage=True,
            load_in_8bit=use_8bit,
            device_map="auto" if torch.cuda.is_available() else None,
            token=token
        )

        # 如果不是 8bit 才手动 .to(self.device)
        if not use_8bit:
            self.model = self.model.to(self.device)

        print(f"初始化 DeepSeekLLM，模型: {self.model_name}, 运行设备: {self.device}, 8bit={use_8bit}")




    @property
    def _llm_type(self) -> str:
        return "deepseek_local"

    def _call(self, prompt: str, **kwargs):
        if self.model is None:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
                load_in_8bit=True if torch.cuda.is_available() else False,
                device_map="auto" if torch.cuda.is_available() else None
            )
            print(f"加载DeepSeek模型: {self.model_name}")

            # 统一设备
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)

        with torch.no_grad():
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=4096
            ).to(self.device)   # ✅ 输入移到同一个 device

            outputs = self.model.generate(
                **inputs,
                pad_token_id=kwargs.get("pad_token_id", self.tokenizer.eos_token_id),
                max_new_tokens=256
            )
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)


    @property
    def _identifying_params(self) -> dict:
        return {"model_name": self.model_name}  # 确保 model_name 可被识别

class HRLocalEmbeddings(Embeddings):
    def __init__(self, model_name: str = 'paraphrase-multilingual-mpnet-base-v2'):
        self.model = SentenceTransformer(model_name)
        print(f"加载嵌入模型: {model_name}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, convert_to_numpy=True, batch_size=32).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text], convert_to_numpy=True)[0].tolist()

def search_knowledge_base(query: str, vector_store: FAISS) -> str:
    keywords = jieba.cut(query)
    keyword_str = ' '.join(keywords)
    if "薪资" in query or "工资" in query:
        keyword_str += " 工资 薪资发放 工资发放"
    docs_with_scores = vector_store.similarity_search_with_score(keyword_str, k=2)
    relevant_docs = [doc for doc, score in docs_with_scores if score <= 0.9]
    if not relevant_docs:
        return "知识库中没有找到相关信息。"
    relevant_docs = relevant_docs[:1]
    return "\n".join(f"{i}. {doc.page_content} (来源: {doc.metadata.get('source', '未知')}, 相似度: {score:.2f})" 
                     for i, (doc, score) in enumerate([(d, s) for d, s in docs_with_scores if d in relevant_docs], 1))
