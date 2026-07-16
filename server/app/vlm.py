from __future__ import annotations

import base64
import json
import os
import re
from urllib.parse import urlsplit, urlunsplit

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

CONTENT_EXTRACTION_PROMPT = """你正在为龙宾楼导览数据库预处理一张管理者上传的现场图片。
只提取图片中可直接观察或清晰阅读到的信息，不要补充未经图片支持的事实。
返回一个 JSON 对象，格式必须是：
{
  "suggested_title_zh": "建议中文标题",
  "suggested_title_en": "建议英文标题",
  "description_zh": "客观中文说明",
  "description_en": "对应英文说明",
  "recognized_texts": ["清晰可见的原文"],
  "visual_tags": ["适合后续视觉定位的外观标签"],
  "visual_description": "能区分该展品或展区的外观描述",
  "uncertain_items": ["无法确定或需要管理员修正的内容"]
}
不要返回 Markdown，不要添加其他字段。管理端提供的上下文如下：
"""


class VlmClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("VLM_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("VLM_API_KEY", "")
        self.model = os.getenv("VLM_MODEL", "")
        self.timeout = float(os.getenv("VLM_TIMEOUT_SECONDS", "45"))

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    @property
    def chat_completions_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        parsed = urlsplit(self.base_url)
        if parsed.hostname in {"dashscope.aliyuncs.com", "dashscope-us.aliyuncs.com"}:
            if parsed.path.rstrip("/") in {"", "/api/v1"}:
                return urlunsplit(
                    (
                        parsed.scheme,
                        parsed.netloc,
                        "/compatible-mode/v1/chat/completions",
                        "",
                        "",
                    )
                )
        return f"{self.base_url}/chat/completions"

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
                    self.chat_completions_url,
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

    async def extract_record(
        self,
        image: bytes,
        content_type: str,
        context: dict,
    ) -> dict:
        if not self.configured:
            raise VlmNotConfiguredError(
                "请设置 VLM_BASE_URL、VLM_API_KEY 和 VLM_MODEL"
            )

        encoded = base64.b64encode(image).decode("ascii")
        prompt = CONTENT_EXTRACTION_PROMPT + json.dumps(
            context, ensure_ascii=False, separators=(",", ":")
        )
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
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
                    self.chat_completions_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            content = body["choices"][0]["message"]["content"]
            result = self._extract_json(content)
        except VlmResponseError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise VlmResponseError(f"VLM 内容预处理失败：{exc}") from exc

        for field in (
            "suggested_title_zh",
            "suggested_title_en",
            "description_zh",
            "description_en",
            "visual_description",
        ):
            if not isinstance(result.get(field, ""), str):
                raise VlmResponseError(f"VLM 内容字段 {field} 必须是字符串")
        for field in ("recognized_texts", "visual_tags", "uncertain_items"):
            if not isinstance(result.get(field, []), list):
                raise VlmResponseError(f"VLM 内容字段 {field} 必须是数组")
        return result
