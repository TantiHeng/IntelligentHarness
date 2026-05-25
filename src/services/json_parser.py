import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)


class JsonParseError(ValueError):
    """模型输出无法解析为目标 JSON schema。"""


def extract_json_object(text: str) -> dict:
    """
    从模型输出中提取 JSON object。

    支持：
    1. 纯 JSON
    2. ```json ... ```
    3. 前后夹杂解释文本的 JSON object

    注意：
    这里只适合解析 object，不适合解析 array。
    """
    if not text or not text.strip():
        raise JsonParseError("模型输出为空，无法解析 JSON。")

    cleaned = text.strip()

    fenced_match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced_match:
        cleaned = fenced_match.group(1).strip()

    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise JsonParseError(f"未找到 JSON object: {text[:300]}")
        cleaned = cleaned[start:end + 1]

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise JsonParseError(f"JSON 解析失败: {exc}; 原始输出: {text[:500]}") from exc

    if not isinstance(value, dict):
        raise JsonParseError("模型输出不是 JSON object。")

    return value


def parse_model_json(text: str, schema: Type[T]) -> T:
    """
    将模型输出解析为 Pydantic 对象。
    """
    data = extract_json_object(text)

    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        raise JsonParseError(f"JSON schema 校验失败: {exc}") from exc