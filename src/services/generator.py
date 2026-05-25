from src.llm import LLMClient
from src.prompts.marketing_prompts import (
    GENERATE_MARKETING_PROMPT,
    REVISE_MARKETING_PROMPT,
)
from src.schemas.marketing import MarketingInput, MarketingContent, ReviewResult
from src.services.json_parser import parse_model_json


class MarketingGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def generate(self, marketing_input: MarketingInput) -> MarketingContent:
        prompt = GENERATE_MARKETING_PROMPT.format(
            input_json=marketing_input.model_dump_json(ensure_ascii=False)
        )

        raw = self.llm_client.invoke(prompt)
        return parse_model_json(raw, MarketingContent)

    def revise(
        self,
        marketing_input: MarketingInput,
        content: MarketingContent,
        review: ReviewResult,
    ) -> MarketingContent:
        prompt = REVISE_MARKETING_PROMPT.format(
            input_json=marketing_input.model_dump_json(ensure_ascii=False),
            content_json=content.model_dump_json(ensure_ascii=False),
            review_json=review.model_dump_json(ensure_ascii=False),
        )

        raw = self.llm_client.invoke(prompt)
        return parse_model_json(raw, MarketingContent)
