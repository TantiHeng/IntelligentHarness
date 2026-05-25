class MarketingWorkflowError(Exception):
    """营销工作流基础异常。"""


class MarketingReviewRejectedError(MarketingWorkflowError):
    """营销内容未通过审核。"""


class MarketingContentMissingError(MarketingWorkflowError):
    """营销内容为空。"""


class MarketingSendFailedError(MarketingWorkflowError):
    """营销内容发送失败。"""
