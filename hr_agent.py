# hr_agent.py
from pathlib import Path
from typing import Dict
import os
import warnings
import logging
import psutil
import re
import json

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

import polars as pl

from .EechatDeepSeekLLM import DeepSeekLLM
from .warning_document_generator import generate_warning_document  # 生成 Word 文档

# 日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HRKnowledgeBaseAgent:
    def __init__(self,
                 base_dir: str = "C:/Users/feng/Desktop/HR_agent_ds/Labour Check",
                 model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"):
        """
        稳定版 HR agent（流水线）：
         - 只做两步：提取信息 -> 生成文档
         - 正则提取 JSON，数据规范化
         - 不使用 ReAct agent（避免循环）
        """
        warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
        self.base_dir = Path(base_dir)
        self.templates_dir = self.base_dir / "Templates"
        self.output_dir = self.base_dir / "Output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name

        mem = psutil.virtual_memory().percent
        logger.info(f"初始化 HRKnowledgeBaseAgent，内存使用率: {mem}%")
        if mem > 90:
            logger.warning("内存使用率过高，可能影响模型加载")

        # 初始化 LLM（DeepSeekLLM）
        try:
            self.llm = DeepSeekLLM(model_name=self.model_name)
            logger.info(f"LLM 初始化成功，模型: {self.model_name}")
            # 尝试保证 tokenizer pad token 存在（若有）
            if hasattr(self.llm, "tokenizer"):
                tokenizer = self.llm.tokenizer
                if getattr(tokenizer, "pad_token", None) is None:
                    tokenizer.add_special_tokens({'pad_token': '[PAD]'})
                    if hasattr(self.llm, "model") and hasattr(self.llm.model, "resize_token_embeddings"):
                        self.llm.model.resize_token_embeddings(len(tokenizer))
                    tokenizer.pad_token = tokenizer.eos_token
                    try:
                        self.llm.model.generation_config.pad_token_id = tokenizer.eos_token_id
                    except Exception:
                        pass
                    logger.info("Tokenizer 已添加 pad_token（如适用）")
        except Exception as e:
            logger.error(f"LLM 初始化失败: {e}")
            raise

        # 初始化向量库（保留，以备后续检索需求）
        try:
            self.vectorstore = self._initialize_vectorstore()
            self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 2})
        except Exception as e:
            logger.warning(f"向量库初始化失败或无模板可加载: {e}")
            self.vectorstore = None
            self.retriever = None

        # 提取信息的严格 prompt
        self.prompt_template_extract_info = """
从输入的问题中提取员工信息。
你必须只输出一个单行 JSON 对象，包含以下字段：
"name", "employee_id", "job_title", "manager", "department", "infraction"。
不要输出任何解释，不要输出代码块符号 ```，不要输出多余文本。
如果信息缺失，字段值设为 ""。
确保输出是合法 JSON，可直接解析。
问题:
{query}
"""

    # ---------------- helper: 调用 LLM（优先 invoke，回退 __call__） ----------------
    def _call_llm(self, prompt: str) -> str:
        """
        兼容 DeepSeekLLM 接口的调用封装。
        优先使用 .invoke(prompt)，若不存在则回退到 llm(prompt).
        返回：字符串（strip 后）
        """
        try:
            # 许多自定义 LLM 实现返回对象或字符串，这里做兼容处理
            if hasattr(self.llm, "invoke"):
                out = self.llm.invoke(prompt)
            else:
                out = self.llm(prompt)
        except Exception as e:
            # 有时候模型会抛出，需要把异常向上抛
            logger.error(f"调用 LLM 失败: {e}")
            raise

        # 如果返回的是一个对象（比如 OpenAI style），尝试拿 .content 或 .text
        if hasattr(out, "content"):
            raw = out.content
        elif hasattr(out, "text"):
            raw = out.text
        else:
            raw = out

        if raw is None:
            return ""
        return str(raw).strip()

    # ---------------- 提取并规范化信息 ----------------
    def _extract_info_tool(self, query: str) -> Dict:
        """
        从 query 用 LLM 提取员工信息，并进行数据类型规范化（所有值转成字符串，缺失字段为 ""）。
        如果无法找到 JSON 或解析失败，会抛出 RuntimeError。
        """
        prompt = self.prompt_template_extract_info.format(query=query)
        raw = self._call_llm(prompt)
        logger.debug(f"LLM 原始输出: {raw}")

        # 正则提取第一个 {...} 块（跨行）
        match = re.search(r"\{[\s\S]*?\}", raw)
        if not match:
            logger.error(f"未找到 JSON 块，原始输出:\n{raw}")
            raise RuntimeError("信息提取失败：模型未返回 JSON 块。请确保 prompt 指示正确。")

        json_str = match.group(0)
        try:
            parsed = json.loads(json_str)
            if not isinstance(parsed, dict):
                raise ValueError("解析后不是 dict 类型")

            # 规范化：确保所有指定字段存在并转换为字符串
            fields = ["name", "employee_id", "job_title", "manager", "department", "infraction"]
            normalized: Dict[str, str] = {}
            for f in fields:
                v = parsed.get(f, "")
                if v is None:
                    normalized[f] = ""
                elif isinstance(v, (int, float, bool)):
                    normalized[f] = str(v)
                else:
                    normalized[f] = str(v).strip()

            logger.info(f"成功提取并规范化员工信息: {normalized}")
            return normalized
        except Exception as e:
            logger.error(f"JSON 解析失败: {e}, 提取内容: {json_str}")
            raise RuntimeError(f"信息提取失败：{e}")

    # ---------------- 生成文档（再次规范化保障） ----------------
    def _generate_doc_tool(self, employee_data: Dict, template_type: str = "B1") -> Dict:
        """
        调用 warning_document_generator 生成 Word 文档。
        返回 dict {'status':.., 'message':..}
        """
        # 二次规范化，确保所有值都是字符串
        safe_data = {}
        for k, v in (employee_data or {}).items():
            if v is None:
                safe_data[k] = ""
            elif isinstance(v, (int, float, bool)):
                safe_data[k] = str(v)
            else:
                safe_data[k] = str(v).strip()

        # 确保常用字段存在
        for key in ["name", "employee_id", "job_title", "manager", "department", "infraction"]:
            safe_data.setdefault(key, "")

        try:
            generate_warning_document(safe_data, self.output_dir, template_type)
            msg = f"文档生成成功，已保存到 {self.output_dir}"
            logger.info(msg)
            return {"status": "success", "message": msg}
        except Exception as e:
            logger.error(f"文档生成失败: {e}")
            return {"status": "fail", "message": str(e)}

    # ---------------- 文档/向量库加载 ----------------
    def _load_document(self, file_path: str) -> str:
        file_path = Path(file_path)
        try:
            if file_path.suffix.lower() == ".pdf":
                import PyPDF2
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
            elif file_path.suffix.lower() == ".docx":
                from docx import Document as Docx
                doc = Docx(file_path)
                return "\n".join(p.text for p in doc.paragraphs if p.text)
            elif file_path.suffix.lower() == ".xlsx":
                df = pl.read_excel(file_path)
                return "\n".join(" ".join(str(v) for v in row.values() if v is not None) for row in df.to_dicts())
            else:
                logger.warning(f"Unsupported file type: {file_path.suffix}")
                return ""
        except Exception as e:
            logger.error(f"加载文件 {file_path} 出错: {e}")
            return ""

    def _initialize_vectorstore(self) -> FAISS:
        """
        初始化 FAISS 向量库（如果 Templates 中有文件会被加载）
        如遇到 embedding 的弃用警告，可按提示升级包。
        """
        logger.info(f"初始化向量存储，内存使用率: {psutil.virtual_memory().percent}%")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        all_docs = []
        files_found = [f for f in self.templates_dir.glob("*") if f.suffix.lower() in [".pdf", ".docx", ".xlsx"]]
        for file_path in files_found:
            txt = self._load_document(str(file_path))
            if txt:
                all_docs.append(Document(page_content=txt, metadata={"source": file_path.name}))
        if not all_docs:
            logger.info("Templates 目录无支持文件，跳过向量库创建。")
            # 返回一个空 FAISS 可能会报错，故此处直接 raise 让调用方决定是否继续
            raise RuntimeError("没有可用的模板文档用于向量化。")
        splits = text_splitter.split_documents(all_docs)
        logger.info(f"分成了 {len(splits)} 个文档块")
        embeddings = HuggingFaceEmbeddings(model_name="distilbert-base-uncased")
        return FAISS.from_documents(splits, embeddings)

    # ---------------- 主入口：两步流水线 ----------------
    def generate_answer(self, query: str, template_type: str = "B1") -> str:
        """
        对外接口：接受自然语言 query，返回 json 字符串结果并在 Output/ 生成 docx。
        如果信息提取失败或生成失败，会返回 status fail。
        """
        logger.info(f"开始处理输入: {query}")
        try:
            employee_info = self._extract_info_tool(query)
        except Exception as e:
            logger.error(f"信息提取阶段失败: {e}")
            return json.dumps({"status": "fail", "message": f"信息提取失败: {e}"}, ensure_ascii=False)

        result = self._generate_doc_tool(employee_info, template_type=template_type)
        return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    agent = HRKnowledgeBaseAgent()
    print("HRKnowledgeBaseAgent 已启动。输入 'exit' 退出。")
    while True:
        q = input("请输入问题 (输入 exit 退出): ").strip()
        if q.lower() == "exit":
            break
        out = agent.generate_answer(q)
        print(out)
