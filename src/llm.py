from dataclasses import dataclass, field
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import Config
from src.logger import logger


@dataclass
class LLMClient:
    config: Config = field(default_factory=Config)
    llm: ChatOpenAI = field(init=False)

    def __post_init__(self) -> None:
        if not self.config.MODEL_NAME:
            raise ValueError("MODEL_NAME 未在 .env 中设置。请在项目 .env 文件中配置。")

        self.llm = ChatOpenAI(
            api_key=self.config.MODEL_API_KEY,
            base_url=self.config.MODEL_BASE_URL,
            model=self.config.MODEL_NAME,
            temperature=self.config.LLM_TEMPERATURE,
            max_tokens=self.config.LLM_MAX_TOKENS,
            timeout=self.config.LLM_TIMEOUT,
        )

        logger.info(
            "LLMClient 初始化完成: model=%s, temperature=%s, max_tokens=%s, timeout=%s",
            self.config.MODEL_NAME,
            self.config.LLM_TEMPERATURE,
            self.config.LLM_MAX_TOKENS,
            self.config.LLM_TIMEOUT,
        )

    def invoke(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=prompt))

        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as exc:
            logger.error("LLM 调用失败: %s", exc)
            raise

    async def ainvoke(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=prompt))

        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as exc:
            logger.error("LLM 异步调用失败: %s", exc)
            raise

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=prompt))

        try:
            for chunk in self.llm.stream(messages):
                if chunk.content:
                    yield chunk.content
        except Exception as exc:
            logger.error("LLM 流式调用失败: %s", exc)
            raise
