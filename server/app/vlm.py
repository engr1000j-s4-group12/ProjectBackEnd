from __future__ import annotations

import base64
import json
import os
import re

import httpx
from pydantic import ValidationError

from .errors import VlmNotConfiguredError, VlmResponseError
from .schemas import VisualLocalizeRequest


VLM_PROMPT = """分析这张室内照片，只提取能够帮助定位的客观视觉特征。
返回一个 JSON 对象，格式必须是：
{
  "objects": [{"label": "物品或建筑特征", "confidence": 0.0到1.0}],
  "recognized_texts": ["照片中清晰可见的文字"],
  "scene_description": "一句简短的客观场景描述",
  "floor_hint": 楼层数字或null
}
不要猜测具体位置，不要返回 Markdown，不要添加其他字段。"""


class VlmClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("VLM_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("VLM_API_KEY", "")
        self.model = os.getenv("VLM_MODEL", "")
        self.timeout = float(os.getenv("VLM_TIMEOUT_SECONDS", "45"))

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def _extract_json(self, content: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        try:
            value = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise VlmResponseError("VLM 未返回合法 JSON") from exc
        if not isinstance(value, dict):
            raise VlmResponseError("VLM 返回值必须是 JSON 对象")
        return value

    async def analyze(self, image: bytes, content_type: str) -> VisualLocalizeRequest:
        if not self.configured:
            raise VlmNotConfiguredError(
                "请设置 VLM_BASE_URL、VLM_API_KEY 和 VLM_MODEL"
            )

        encoded = base64.b64encode(image).decode("ascii")
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VLM_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{content_type};base64,{encoded}"
                            },
                        },
                    ],
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise VlmResponseError(f"VLM 请求失败：{exc}") from exc

        try:
            content = body["choices"][0]["message"]["content"]
            return VisualLocalizeRequest.model_validate(self._extract_json(content))
        except (KeyError, IndexError, TypeError, ValidationError) as exc:
            raise VlmResponseError("VLM 响应缺少有效的结构化视觉特征") from exc
