from src.llm import LLMClient
from src.prompts.marketing_prompts import REVIEW_MARKETING_PROMPT
from src.schemas.marketing import MarketingContent, ReviewResult
from src.services.json_parser import parse_model_json


FORBIDDEN_PHRASES = [
    "100%保证",
    "稳赚",
    "行业第一",
    "绝对有效",
    "永久解决",
]


class MarketingReviewer:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def rule_review(self, content: MarketingContent) -> ReviewResult:
        text = f"{content.title}\n{content.body}\n{content.call_to_action}"

        hits = [phrase for phrase in FORBIDDEN_PHRASES if phrase in text]

        if hits:
            return ReviewResult(
                approved=False,
                score=40,
                reasons=[f"命中禁用表达: {phrase}" for phrase in hits],
                revision_suggestions=[
                    "删除绝对化、承诺式、夸大式表达。",
                    "改为客观描述产品能力和适用场景。",
                ],
            )

        return ReviewResult(
            approved=True,
            score=90,
            reasons=["未命中基础禁用表达。"],
            revision_suggestions=[],
        )

    def llm_review(self, content: MarketingContent) -> ReviewResult:
        prompt = REVIEW_MARKETING_PROMPT.format(
            content_json=content.model_dump_json(ensure_ascii=False)
        )

        raw = self.llm_client.invoke(prompt)
        return parse_model_json(raw, ReviewResult)

    def review(self, content: MarketingContent) -> ReviewResult:
        rule_result = self.rule_review(content)

        if not rule_result.approved:
            return rule_result

        return self.llm_review(content)
