"""
营销工作流演示入口。

该脚本使用固定的示例产品/客户信息启动一次完整工作流。
它不是通用 CLI；如果需要命令行参数输入，应另行封装 argparse / Typer。
"""

import sys

from src.exceptions import MarketingWorkflowError
from src.logger import logger
from src.schemas.marketing import (
    Channel,
    CustomerInfo,
    MarketingInput,
    MarketingWorkflowState,
    ProductInfo,
)
from src.workflows.marketing_workflow import MarketingWorkflow


def render_marketing_content(state: MarketingWorkflowState) -> str:
    if state.content is None:
        raise ValueError("工作流未生成营销内容。")
    content = state.content
    return f"""标题：{content.title}

正文：
{content.body}

行动引导：
{content.call_to_action}"""


def build_demo_state() -> MarketingWorkflowState:
    return MarketingWorkflowState(
        input=MarketingInput(
            product=ProductInfo(
                name="智能营销助手",
                selling_points=["自动生成客户画像营销文案", "支持审核流程", "支持发送记录追踪"],
                price="按量计费",
                target_audience="中小企业销售团队",
            ),
            customer=CustomerInfo(
                name="某教育 SaaS 公司",
                segment="教育行业",
                pain_points=["销售跟进效率低", "客户分层不清晰", "营销内容质量不稳定"],
                contact="customer@example.com",
            ),
            channel=Channel.EMAIL,
            tone="专业、克制、偏B2B销售顾问口吻",
        )
    )


def main() -> int:
    workflow = MarketingWorkflow()
    state = build_demo_state()

    try:
        result = workflow.invoke(state)
        logger.info("工作流执行成功: record_id=%s, retry_count=%s", result.record_id, result.retry_count)
        print(render_marketing_content(result))
        return 0
    except MarketingWorkflowError as exc:
        logger.exception("营销工作流执行失败: %s", exc)
        print(f"营销工作流执行失败: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("未知异常导致工作流失败: %s", exc)
        print(f"未知异常导致工作流失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
