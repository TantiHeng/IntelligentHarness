from src.schemas.marketing import MarketingInput, MarketingContent, SendResult, Channel


class MarketingSender:
    """营销内容发送服务。当前为 mock email 发送。"""

    def send(self, marketing_input: MarketingInput, content: MarketingContent) -> SendResult:
        if marketing_input.channel == Channel.EMAIL:
            return self._send_email(marketing_input, content)

        return SendResult(
            success=False,
            error=f"暂不支持的发送渠道: {marketing_input.channel.value}",
        )

    def _send_email(self, marketing_input: MarketingInput, content: MarketingContent) -> SendResult:
        customer = marketing_input.customer

        if not customer.contact:
            return SendResult(success=False, error="客户 contact 为空，无法发送邮件。")

        return SendResult(
            success=True,
            provider_message_id="mock-email-message-id",
        )
