"""Embedding 适配器：将文本批量转换为语义向量。"""

from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from intelligent_harness.adapters.settings import RuntimeConfig


class EmbeddingClient:
    """Use an OpenAI-compatible embedding endpoint behind the local protocol."""

    def __init__(self, config: RuntimeConfig) -> None:
        if not config.embedding_model_name:
            raise ValueError(
                "EMBEDDING_MODEL_NAME 未配置。semantic_layered 场景需要 embedding 模型；"
                "如 embedding 与对话模型供应商不同，请同时配置 EMBEDDING_BASE_URL "
                "和 EMBEDDING_API_KEY。"
            )
        self.embeddings = OpenAIEmbeddings(
            api_key=SecretStr(config.embedding_api_key or config.model_api_key),
            base_url=config.embedding_base_url or config.model_base_url,
            model=config.embedding_model_name,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            return self.embeddings.embed_documents(texts)
        except Exception as exc:
            raise ValueError(
                "Embedding 服务调用失败。请检查 EMBEDDING_BASE_URL、"
                "EMBEDDING_API_KEY 和 EMBEDDING_MODEL_NAME；对话模型不能直接替代 embedding 模型。"
            ) from exc
