import asyncio
import json
import re
from datetime import datetime
from typing import Tuple, Union

import aiohttp
from loguru import logger
from nonebot import get_driver
import base64
from PIL import Image
import io
from ...common.database import Database
from ..chat.config import global_config

driver = get_driver()
config = driver.config


class LLM_request:
    def __init__(self, model, **kwargs):
        try:
            self.api_key = getattr(config, model["key"])
            self.base_url = getattr(config, model["base_url"])
        except AttributeError as e:
            logger.error(f"原始 model dict 信息：{model}")
            logger.error(f"配置错误：找不到对应的配置项 - {str(e)}")
            raise ValueError(f"配置错误：找不到对应的配置项 - {str(e)}") from e
        self.model_name = model["name"]
        self.params = kwargs

        self.pri_in = model.get("pri_in", 0)
        self.pri_out = model.get("pri_out", 0)

        self.db = Database.get_instance()
        self._init_database()

    def _init_database(self):
        try:
            self.db.db.llm_usage.create_index([("timestamp", 1)])
            self.db.db.llm_usage.create_index([("model_name", 1)])
            self.db.db.llm_usage.create_index([("user_id", 1)])
            self.db.db.llm_usage.create_index([("request_type", 1)])
        except Exception as e:
            logger.error(f"创建数据库索引失败: {str(e)}")

    def _record_usage(self, prompt_tokens: int, completion_tokens: int, total_tokens: int,
                      user_id: str = "system", request_type: str = "chat",
                      endpoint: str = "/chat/completions"):
        try:
            usage_data = {
                "model_name": self.model_name,
                "user_id": user_id,
                "request_type": request_type,
                "endpoint": endpoint,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost": self._calculate_cost(prompt_tokens, completion_tokens),
                "status": "success",
                "timestamp": datetime.now()
            }
            self.db.db.llm_usage.insert_one(usage_data)
            logger.info(
                f"Token使用情况 - 模型: {self.model_name}, 用户: {user_id}, 类型: {request_type}, "
                f"提示词: {prompt_tokens}, 完成: {completion_tokens}, 总计: {total_tokens}"
            )
        except Exception as e:
            logger.error(f"记录token使用情况失败: {str(e)}")

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        input_cost = (prompt_tokens / 1000000) * self.pri_in
        output_cost = (completion_tokens / 1000000) * self.pri_out
        return round(input_cost + output_cost, 6)

    async def _execute_request(
            self,
            endpoint: str,
            prompt: str = None,
            image_base64: str = None,
            payload: dict = None,
            retry_policy: dict = None,
            response_handler: callable = None,
            user_id: str = "system",
            request_type: str = "chat"
    ):
        default_retry = {
            "max_retries": 3, "base_wait": 15,
            "retry_codes": [429, 413, 500, 503],
            "abort_codes": [400, 401, 402, 403]
        }
        policy = {**default_retry, **(retry_policy or {})}

        error_code_mapping = {
            400: "参数不正确",
            401: "API key 错误，认证失败",
            402: "账号余额不足",
            403: "需要实名,或余额不足",
            404: "Not Found",
            429: "请求过于频繁，请稍后再试",
            500: "服务器内部故障",
            503: "服务器负载过高"
        }

        api_url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        stream_mode = self.params.get("stream", False)
        logger.debug(f"发送请求到URL: {api_url}, 流式模式: {stream_mode}")
        logger.info(f"使用模型: {self.model_name}")

        if image_base64:
            payload = await self._build_payload(prompt, image_base64)
        elif payload is None:
            payload = await self._build_payload(prompt)

        for retry in range(policy["max_retries"]):
            try:
                headers = await self._build_headers()
                if stream_mode:
                    headers["Accept"] = "text/event-stream"

                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, headers=headers, json=payload) as response:
                        if response.status in policy["retry_codes"]:
                            wait_time = policy["base_wait"] * (2 ** retry)
                            logger.warning(f"错误码: {response.status}, 等待 {wait_time}秒后重试")
                            if response.status == 413 and image_base64:
                                logger.warning("请求体过大，尝试压缩图片...")
                                image_base64 = compress_base64_image_by_scale(image_base64)
                                payload = await self._build_payload(prompt, image_base64)
                            await asyncio.sleep(wait_time)
                            continue
                        elif response.status in policy["abort_codes"]:
                            logger.error(f"错误码: {response.status} - {error_code_mapping.get(response.status)}")
                            raise RuntimeError(f"请求被拒绝: {error_code_mapping.get(response.status)}")

                        response.raise_for_status()

                        if stream_mode:
                            accumulated_content = ""
                            usage = None
                            async for line_bytes in response.content:
                                line = line_bytes.decode("utf-8").strip()
                                if not line or line == "data: [DONE]":
                                    break
                                if line.startswith("data:"):
                                    chunk = json.loads(line[5:].strip())
                                    delta = chunk["choices"][0]["delta"]
                                    content = delta.get("content", "")
                                    accumulated_content += content
                                    if chunk["choices"][0].get("finish_reason") == "stop":
                                        usage = chunk.get("usage")
                                        break
                            content = accumulated_content
                            result = {"choices": [{"message": {"content": content}}], "usage": usage}
                            return response_handler(result) if response_handler else self._default_response_handler(
                                result, user_id, request_type, endpoint)
                        else:
                            result = await response.json()
                            return response_handler(result) if response_handler else self._default_response_handler(
                                result, user_id, request_type, endpoint)

            except Exception as e:
                if retry < policy["max_retries"] - 1:
                    wait_time = policy["base_wait"] * (2 ** retry)
                    logger.error(f"请求失败，等待{wait_time}秒后重试... 错误: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.critical(f"请求失败: {str(e)}")
                    logger.critical(f"请求头: {await self._build_headers(no_key=True)} 请求体: {payload}")
                    raise RuntimeError(f"API请求失败: {str(e)}")

        raise RuntimeError("达到最大重试次数，API请求仍然失败")

    async def _transform_parameters(self, params: dict) -> dict:
        new_params = dict(params)
        models_needing_transformation = ["o3-mini", "o1-mini", "o1-preview", "o1-2024-12-17", "o1-preview-2024-09-12",
                                         "o3-mini-2025-01-31", "o1-mini-2024-09-12"]
        if self.model_name.lower() in models_needing_transformation:
            new_params.pop("temperature", None)
            if "max_tokens" in new_params:
                new_params["max_completion_tokens"] = new_params.pop("max_tokens")
        return new_params

    async def _build_payload(self, prompt: str, image_base64: str = None) -> dict:
        params_copy = await self._transform_parameters(self.params)
        if image_base64:
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                        ]
                    }
                ],
                "max_tokens": global_config.max_response_length,
                **params_copy
            }
        else:
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": global_config.max_response_length,
                **params_copy
            }
        return payload

    def _default_response_handler(self, result: dict, user_id: str = "system",
                                  request_type: str = "chat", endpoint: str = "/chat/completions") -> Tuple:
        if "choices" in result and result["choices"]:
            message = result["choices"][0]["message"]
            content = message.get("content", "")
            reasoning_content = message.get("reasoning_content", "")

            usage = result.get("usage", {})
            if usage:
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                self._record_usage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    user_id=user_id,
                    request_type=request_type,
                    endpoint=endpoint
                )
            return content, reasoning_content
        return "没有返回结果", ""

    async def _build_headers(self, no_key: bool = False) -> dict:
        if no_key:
            return {
                "Authorization": "Bearer **********",
                "Content-Type": "application/json"
            }
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate_response(self, prompt: str) -> Tuple[str, str]:
        return await self._execute_request(
            endpoint="/chat/completions",
            prompt=prompt
        )

    async def generate_response_for_image(self, prompt: str, image_base64: str) -> Tuple[str, str]:
        return await self._execute_request(
            endpoint="/chat/completions",
            prompt=prompt,
            image_base64=image_base64
        )

    async def generate_response_async(self, prompt: str, **kwargs) -> Union[str, Tuple[str, str]]:
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": global_config.max_response_length,
            **self.params
        }
        return await self._execute_request(
            endpoint="/chat/completions",
            payload=data,
            prompt=prompt
        )

    async def get_embedding(self, text: str) -> Union[list, None]:
        def embedding_handler(result):
            if "data" in result and len(result["data"]) > 0:
                return result["data"][0].get("embedding", None)
            return None

        return await self._execute_request(
            endpoint="/embeddings",
            prompt=text,
            payload={
                "model": self.model_name,
                "input": text,
                "encoding_format": "float"
            },
            retry_policy={"max_retries": 2, "base_wait": 6},
            response_handler=embedding_handler
        )


def compress_base64_image_by_scale(base64_data: str, target_size: int = 0.8 * 1024 * 1024) -> str:
    try:
        image_data = base64.b64decode(base64_data)
        if len(image_data) <= 2 * 1024 * 1024:
            return base64_data

        img = Image.open(io.BytesIO(image_data))
        original_width, original_height = img.size
        scale = min(1.0, (target_size / len(image_data)) ** 0.5)
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)

        output_buffer = io.BytesIO()
        if getattr(img, "is_animated", False):
            frames = []
            for frame_idx in range(img.n_frames):
                img.seek(frame_idx)
                new_frame = img.copy().resize((new_width // 2, new_height // 2), Image.Resampling.LANCZOS)
                frames.append(new_frame)
            frames[0].save(
                output_buffer, format='GIF', save_all=True, append_images=frames[1:],
                optimize=True, duration=img.info.get('duration', 100), loop=img.info.get('loop', 0)
            )
        else:
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            if img.format == 'PNG' and img.mode in ('RGBA', 'LA'):
                resized_img.save(output_buffer, format='PNG', optimize=True)
            else:
                resized_img.save(output_buffer, format='JPEG', quality=95, optimize=True)

        compressed_data = output_buffer.getvalue()
        logger.success(f"压缩图片: {original_width}x{original_height} -> {new_width}x{new_height}")
        logger.info(f"压缩前大小: {len(image_data)/1024:.1f}KB, 压缩后大小: {len(compressed_data)/1024:.1f}KB")
        return base64.b64encode(compressed_data).decode('utf-8')
    except Exception as e:
        logger.error(f"压缩图片失败: {str(e)}")
        return base64_data
