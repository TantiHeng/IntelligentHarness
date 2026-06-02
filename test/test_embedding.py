"""Embedding 适配器错误边界测试。"""

import pytest

from intelligent_harness.adapters.embedding import EmbeddingClient


class FailingEmbeddings:
    def embed_documents(self, texts):
        raise RuntimeError("provider returned 404")


def test_embedding_client_wraps_provider_errors():
    client = object.__new__(EmbeddingClient)
    client.embeddings = FailingEmbeddings()

    with pytest.raises(ValueError, match="Embedding 服务调用失败"):
        client.embed_documents(["sample"])
