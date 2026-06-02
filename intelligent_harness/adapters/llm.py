"""模型适配器：将统一文本调用转换为 LangChain 模型请求，不处理审核。"""

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from intelligent_harness.adapters.settings import RuntimeConfig


class LLMClient:
    def __init__(self, config: RuntimeConfig) -> None:
        if not config.model_name:
            raise ValueError("MODEL_NAME 未配置。")
        self.llm = ChatOpenAI(
            api_key=SecretStr(config.model_api_key),
            base_url=config.model_base_url,
            model=config.model_name,
            temperature=config.llm_temperature,
            max_completion_tokens=config.llm_max_tokens,
            timeout=config.llm_timeout,
        )

    def invoke(self, prompt: str) -> str:
        content = self.llm.invoke([HumanMessage(content=prompt)]).content
        if not isinstance(content, str):
            raise TypeError("模型响应 content 不是字符串。")
        return content
