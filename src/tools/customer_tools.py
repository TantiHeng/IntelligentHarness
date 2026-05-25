from typing import Optional
from pydantic import BaseModel, Field

try:
    from langchain_core.tools import tool
except ImportError:
    tool = None


class CustomerProfile(BaseModel):
    id: str
    name: str
    segment: str | None = None
    pain_points: list[str] = Field(default_factory=list)
    contact: str | None = None
    notes: str | None = None


MOCK_CUSTOMERS: dict[str, CustomerProfile] = {
    "edu_saas_001": CustomerProfile(
        id="edu_saas_001",
        name="某教育 SaaS 公司",
        segment="教育行业",
        pain_points=[
            "销售跟进效率低",
            "客户分层不清晰",
            "营销内容质量不稳定",
        ],
        contact="customer@example.com",
        notes="偏 B2B 销售场景，适合专业克制的顾问式话术。",
    ),
    "finance_001": CustomerProfile(
        id="finance_001",
        name="某金融科技公司",
        segment="金融科技",
        pain_points=[
            "合规审核成本高",
            "客户触达链路长",
            "内容生成需要留痕",
        ],
        contact="finance_customer@example.com",
        notes="金融行业表达需保守，避免收益承诺。",
    ),
}


class CustomerNotFoundError(KeyError):
    """客户不存在。"""


def get_customer_by_id(customer_id: str) -> CustomerProfile:
    if not customer_id or not customer_id.strip():
        raise ValueError("customer_id 不能为空。")

    customer = MOCK_CUSTOMERS.get(customer_id)

    if customer is None:
        raise CustomerNotFoundError(f"未找到客户: {customer_id}")

    return customer


def search_customers(keyword: str) -> list[CustomerProfile]:
    if not keyword or not keyword.strip():
        return list(MOCK_CUSTOMERS.values())

    keyword = keyword.strip().lower()

    return [
        customer
        for customer in MOCK_CUSTOMERS.values()
        if keyword in customer.id.lower()
        or keyword in customer.name.lower()
        or keyword in (customer.segment or "").lower()
    ]


if tool is not None:
    @tool
    def get_customer_profile(customer_id: str) -> dict:
        """
        根据客户 ID 查询客户画像信息。

        参数:
            customer_id: 客户 ID，例如 edu_saas_001。

        返回:
            客户画像字典。
        """
        return get_customer_by_id(customer_id).model_dump()

    @tool
    def search_customer_profiles(keyword: str) -> list[dict]:
        """
        根据关键词搜索客户画像。

        参数:
            keyword: 客户名、行业、客户 ID 关键词。

        返回:
            客户画像列表。
        """
        return [customer.model_dump() for customer in search_customers(keyword)]
else:
    get_customer_profile = None
    search_customer_profiles = None