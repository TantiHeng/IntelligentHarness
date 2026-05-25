from src.schemas.marketing import (
    MarketingInput,
    ProductInfo,
    CustomerInfo,
    Channel,
    MarketingContent,
    ReviewResult,
)
from src.services.generator import MarketingGenerator
from src.services.reviewer import MarketingReviewer


class CaptureLLM:
    def __init__(self, response: str):
        self.response = response
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


def build_input() -> MarketingInput:
    return MarketingInput(
        product=ProductInfo(
            name="智能营销助手",
            selling_points=["自动生成营销文案"],
            price="按量计费",
            target_audience="中小企业销售团队",
        ),
        customer=CustomerInfo(
            name="某教育 SaaS 公司",
            segment="教育行业",
            pain_points=["销售跟进效率低"],
            contact="customer@example.com",
        ),
        channel=Channel.EMAIL,
        tone="专业、克制",
    )


def test_generate_prompt_is_rendered_without_placeholders():
    llm = CaptureLLM(
        '{"title":"标题","body":"正文","call_to_action":"联系我","risk_notes":[]}'
    )
    generator = MarketingGenerator(llm)

    generator.generate(build_input())

    prompt = llm.prompts[0]

    assert "{input_json}" not in prompt
    assert "{{" not in prompt
    assert "智能营销助手" in prompt
    assert "某教育 SaaS 公司" in prompt


def test_revise_prompt_is_rendered_with_review_suggestions():
    llm = CaptureLLM(
        '{"title":"改写标题","body":"改写正文","call_to_action":"预约演示","risk_notes":[]}'
    )
    generator = MarketingGenerator(llm)

    content = MarketingContent(
        title="原标题",
        body="原正文，行业第一",
        call_to_action="联系我",
        risk_notes=[],
    )
    review = ReviewResult(
        approved=False,
        score=40,
        reasons=["命中禁用表达: 行业第一"],
        revision_suggestions=["删除绝对化表达"],
    )

    generator.revise(build_input(), content, review)

    prompt = llm.prompts[0]

    assert "{input_json}" not in prompt
    assert "{content_json}" not in prompt
    assert "{review_json}" not in prompt
    assert "{{" not in prompt
    assert "原正文" in prompt
    assert "删除绝对化表达" in prompt


def test_review_prompt_is_rendered_without_placeholders():
    llm = CaptureLLM(
        '{"approved":true,"score":90,"reasons":["通过"],"revision_suggestions":[]}'
    )
    reviewer = MarketingReviewer(llm)

    content = MarketingContent(
        title="标题",
        body="正文",
        call_to_action="预约演示",
        risk_notes=[],
    )

    reviewer.llm_review(content)

    prompt = llm.prompts[0]

    assert "{content_json}" not in prompt
    assert "{{" not in prompt
    assert "预约演示" in prompt
