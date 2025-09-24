"""即梦 API HTTP 客户端封装。"""

from __future__ import annotations

import json
import logging
import math
import secrets
import time
import uuid
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import httpx

from ..models.tasks import TaskStatus

logger = logging.getLogger(__name__)

BASE_URL = "https://jimeng.jianying.com"
AID = "513695"
APP_VERSION = "5.8.0"
APP_SDK_VERSION = "48.0.0"
DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)

MODEL_REQ_KEYS: Dict[str, str] = {
    "4.0": "high_aes_general_v40",
    "3.1": "high_aes_general_v30l_art_fangzhou:general_v3.0_18b",
    "3.0": "high_aes_general_v30l:general_v3.0_18b",
    "2.1": "high_aes_general_v21_L:general_v2.1_L",
    "2.0p": "high_aes_general_v20_L:general_v2.0_L",
    "2.0": "high_aes_general_v20:general_v2.0",
}

MODEL_ALIASES: Dict[str, str] = {
    "sdxl": "3.0",
    "sdxl-turbo": "3.0",
    "sdxl-lightning": "3.0",
    "v40": "4.0",
    "v31": "3.1",
    "v30": "3.0",
    "v21": "2.1",
    "v20p": "2.0p",
    "v20": "2.0",
}


class JimengApiError(RuntimeError):
    """封装即梦 API 调用中返回的错误。"""

    def __init__(self, message: str, *, code: str | None = None, payload: Dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.payload = payload or {}


@dataclass(slots=True)
class JimengSubmissionResult:
    """表示一次任务提交或轮询返回的结构化结果。"""

    history_id: str
    status: TaskStatus
    result_urls: List[str]
    queue_message: Optional[str] = None
    queue_info: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class JimengTokenManager:
    """负责生成即梦 API 调用所需的动态签名与 Cookie。"""

    def __init__(self, *, sessionid: str, account_name: str | None = None) -> None:
        token = (sessionid or "").strip()
        if not token:
            raise ValueError("即梦 sessionid 不能为空")
        self._sessionid = token
        self._account_name = account_name or "default"
        self._random = secrets.SystemRandom()
        self._web_id = self._generate_web_id()
        self._user_id = self._generate_web_id()

    @property
    def account_label(self) -> str:
        return self._account_name

    def get_web_id(self) -> str:
        return self._web_id

    def get_token(self, api_path: str) -> Dict[str, str]:
        timestamp = str(int(time.time()))
        ms_token = self._generate_random_string(107)
        sign = self._generate_sign(api_path, timestamp)
        a_bogus = self._generate_random_string(32)
        cookie = self._generate_cookie(timestamp)
        return {
            "cookie": cookie,
            "msToken": ms_token,
            "sign": sign,
            "a_bogus": a_bogus,
            "device_time": timestamp,
        }

    def _generate_sign(self, api_path: str, timestamp: str) -> str:
        suffix = api_path[-7:] if api_path else "/mweb/v1/aigc_draft/generate"[-7:]
        sign_str = f"9e2c|{suffix}|7|{APP_VERSION}|{timestamp}||11ac"
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest()

    def _generate_cookie(self, timestamp: str) -> str:
        now = int(timestamp)
        expire_time = now + 60 * 24 * 60 * 60
        expire_date = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", time.gmtime(expire_time))
        hashed = hashlib.md5(f"{self._sessionid}{timestamp}".encode("utf-8")).hexdigest()
        parts = [
            f"sessionid={self._sessionid}",
            f"sessionid_ss={self._sessionid}",
            f"_tea_web_id={self._web_id}",
            f"web_id={self._web_id}",
            f"_v2_spipe_web_id={self._web_id}",
            f"uid_tt={self._user_id}",
            f"uid_tt_ss={self._user_id}",
            f"sid_tt={self._sessionid}",
            f"sid_guard={self._sessionid}%7C{timestamp}%7C5184000%7C{expire_date}",
            f"ssid_ucp_v1=1.0.0-{hashed}",
            f"sid_ucp_v1=1.0.0-{hashed}",
            "store-region=cn-gd",
            "store-region-src=uid",
            "is_staff_user=false",
        ]
        return "; ".join(parts)

    def _generate_web_id(self) -> str:
        return "".join(self._random.choice("0123456789") for _ in range(19))

    def _generate_random_string(self, length: int) -> str:
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(self._random.choice(alphabet) for _ in range(length))


class JimengClient:
    """异步即梦 API 客户端，用于发起生成与轮询任务。"""

    def __init__(
        self,
        *,
        sessionid: str,
        account_name: str | None = None,
        proxies: Dict[str, str] | str | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        self._token_manager = JimengTokenManager(sessionid=sessionid, account_name=account_name)
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=timeout, proxies=self._normalized_proxies(proxies))

    async def aclose(self) -> None:
        await self._client.aclose()

    def _normalized_proxies(self, proxies: Dict[str, str] | str | None) -> Dict[str, str] | str | None:
        if isinstance(proxies, dict):
            result = {k: v for k, v in proxies.items() if isinstance(v, str) and v.strip()}
            return result or None
        if isinstance(proxies, str) and proxies.strip():
            return proxies.strip()
        return None

    def _build_headers(self, api_path: str, token: Dict[str, str], *, include_tokens: bool) -> Dict[str, str]:
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "app-sdk-version": APP_SDK_VERSION,
            "appid": AID,
            "appvr": APP_VERSION,
            "content-type": "application/json",
            "cookie": token["cookie"],
            "device-time": token["device_time"],
            "lan": "zh-Hans",
            "loc": "cn",
            "origin": "https://jimeng.jianying.com",
            "pf": "7",
            "priority": "u=1, i",
            "referer": "https://jimeng.jianying.com/ai-tool/generate",
            "sec-ch-ua": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sign": token["sign"],
            "sign-ver": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        }
        if include_tokens:
            headers["msToken"] = token["msToken"]
            headers["a-bogus"] = token["a_bogus"]
        return headers

    async def _request(
        self,
        method: str,
        api_path: str,
        *,
        params: Dict[str, Any] | None = None,
        json_payload: Dict[str, Any] | None = None,
        include_query_tokens: bool = False,
    ) -> Dict[str, Any]:
        token = self._token_manager.get_token(api_path)
        headers = self._build_headers(api_path, token, include_tokens=not include_query_tokens)
        query = dict(params or {})
        if include_query_tokens:
            if token.get("msToken"):
                query["msToken"] = token["msToken"]
            if token.get("a_bogus"):
                query["a_bogus"] = token["a_bogus"]
        url = api_path if api_path.startswith("/") else f"/{api_path}"
        try:
            response = await self._client.request(method, url, params=query or None, json=json_payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - 网络异常
            logger.exception("即梦 API 网络请求失败：%s", exc)
            raise JimengApiError("即梦 API 请求失败", code=str(exc.response.status_code)) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - 网络异常
            logger.exception("即梦 API 网络错误：%s", exc)
            raise JimengApiError("即梦 API 网络异常") from exc

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            logger.exception("即梦 API 返回非 JSON：%s", response.text)
            raise JimengApiError("即梦 API 返回格式错误") from exc
        return payload

    async def fetch_resource(self, url: str) -> bytes:
        """下载生成结果资源，带上必要的鉴权头。"""

        headers = {
            "referer": "https://jimeng.jianying.com/ai-tool/generate",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        }
        try:
            response = await self._client.get(url, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - 网络异常
            logger.warning("下载即梦资源失败：%s", exc)
            raise JimengApiError("即梦资源下载失败", code=str(exc.response.status_code)) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - 网络异常
            logger.warning("下载即梦资源出现网络错误：%s", exc)
            raise JimengApiError("即梦资源下载网络异常") from exc
        return response.content
    def _resolve_model(self, alias: str | None) -> str:
        name = (alias or "3.0").strip()
        key = MODEL_ALIASES.get(name.lower(), name)
        if key not in MODEL_REQ_KEYS:
            logger.warning("未知模型 %s，回退为 3.0", name)
            return "3.0"
        return key

    def _resolve_dimensions(self, size: str | None) -> tuple[int, int, str, str]:
        if not size:
            return 1024, 1024, "1:1", "1k"
        cleaned = size.lower().replace("*", "x").replace("×", "x")
        if ":" in cleaned:
            parts = cleaned.split(":")
        else:
            parts = cleaned.split("x")
        try:
            width = int(parts[0])
            height = int(parts[1])
        except (IndexError, ValueError):
            width, height = 1024, 1024
        gcd = math.gcd(width, height) or 1
        ratio = f"{width // gcd}:{height // gcd}"
        max_side = max(width, height)
        if max_side <= 1664:
            resolution = "1k"
        elif max_side <= 2688:
            resolution = "2k"
        else:
            resolution = "4k"
        return width, height, ratio, resolution

    def _ratio_value(self, ratio: str) -> int:
        try:
            first, _ = ratio.split(":", 1)
            return int(first)
        except Exception:
            return 1
    def _build_generation_payload(
        self,
        *,
        prompt: str,
        model_key: str,
        width: int,
        height: int,
        ratio: str,
        resolution: str,
        batch: int,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        now_ms = int(time.time() * 1000)
        submit_id = str(uuid.uuid4())
        draft_id = str(uuid.uuid4())
        component_id = str(uuid.uuid4())

        metrics_extra = {
            "templateId": "",
            "generateCount": batch,
            "promptSource": "custom",
            "templateSource": "",
            "lastRequestId": "",
            "originRequestId": "",
            "originSubmitId": "",
            "isDefaultSeed": 1,
            "originTemplateId": "",
            "imageNameMapping": {},
            "isUseAiGenPrompt": False,
            "batchNumber": batch,
        }

        babi_param = {
            "scenario": "image_video_generation",
            "feature_key": "aigc_to_image",
            "feature_entrance": "to_image",
            "feature_entrance_detail": "to_image",
        }

        core_param = {
            "type": "",
            "id": str(uuid.uuid4()),
            "model": MODEL_REQ_KEYS[model_key],
            "prompt": prompt,
            "negative_prompt": "",
            "seed": secrets.randbelow(999_999_999) + 1,
            "sample_strength": 0.5,
            "image_ratio": self._ratio_value(ratio),
            "generate_count": batch,
            "num_images": batch,
            "large_image_info": {
                "type": "",
                "id": str(uuid.uuid4()),
                "height": height,
                "width": width,
                "resolution_type": resolution,
            },
        }

        draft_content = {
            "type": "draft",
            "id": draft_id,
            "min_version": "3.0.2",
            "min_features": [],
            "is_from_tsn": True,
            "version": "3.2.8",
            "main_component_id": component_id,
            "component_list": [
                {
                    "type": "image_base_component",
                    "id": component_id,
                    "min_version": "3.0.2",
                    "aigc_mode": "workbench",
                    "metadata": {
                        "type": "",
                        "id": str(uuid.uuid4()),
                        "created_platform": 3,
                        "created_platform_version": "",
                        "created_time_in_ms": str(now_ms),
                        "created_did": "",
                    },
                    "generate_type": "generate",
                    "abilities": {
                        "type": "",
                        "id": str(uuid.uuid4()),
                        "generate": {
                            "type": "",
                            "id": str(uuid.uuid4()),
                            "core_param": core_param,
                            "history_option": {"type": "", "id": str(uuid.uuid4())},
                        },
                    },
                }
            ],
        }

        payload = {
            "extend": {"root_model": MODEL_REQ_KEYS[model_key], "template_id": ""},
            "submit_id": submit_id,
            "metrics_extra": json.dumps(metrics_extra, ensure_ascii=False, separators=(",", ":")),
            "draft_content": json.dumps(draft_content, ensure_ascii=False, separators=(",", ":")),
            "http_common_info": {"aid": AID},
        }
        return payload, babi_param
    async def submit_generation(
        self,
        *,
        prompt: str,
        model: str | None,
        size: str | None,
        batch: int,
    ) -> JimengSubmissionResult:
        model_key = self._resolve_model(model)
        width, height, ratio, resolution = self._resolve_dimensions(size)
        payload, babi_param = self._build_generation_payload(
            prompt=prompt,
            model_key=model_key,
            width=width,
            height=height,
            ratio=ratio,
            resolution=resolution,
            batch=max(1, min(batch, 4)),
        )
        params = {
            "babi_param": json.dumps(babi_param, ensure_ascii=False, separators=(",", ":")),
            "aid": AID,
            "device_platform": "web",
            "region": "CN",
            "web_id": self._token_manager.get_web_id(),
        }
        response = await self._request(
            "POST",
            "/mweb/v1/aigc_draft/generate",
            params=params,
            json_payload=payload,
            include_query_tokens=True,
        )
        ret = str(response.get("ret"))
        if ret != "0":
            code = response.get("ret") if isinstance(response.get("ret"), str) else ret
            message = (
                response.get("message")
                or response.get("msg")
                or response.get("error_msg")
                or "即梦生成请求被拒绝"
            )
            raise JimengApiError(message, code=str(code), payload=response)

        history_id = (
            response.get("data", {})
            .get("aigc_data", {})
            .get("history_record_id")
        )
        if not history_id:
            raise JimengApiError("即梦返回缺少历史记录 ID", payload=response)

        try:
            history = await self.fetch_history(history_id)
        except JimengApiError as exc:
            logger.warning("首次轮询历史记录失败：%s", exc)
            history = JimengSubmissionResult(
                history_id=history_id,
                status=TaskStatus.RUNNING,
                result_urls=[],
                raw=response,
            )
        return history
    async def fetch_history(self, history_id: str) -> JimengSubmissionResult:
        params = {
            "aid": AID,
            "device_platform": "web",
            "region": "CN",
            "web_id": self._token_manager.get_web_id(),
        }
        payload = {
            "history_ids": [history_id],
            "image_info": {
                "width": 2048,
                "height": 2048,
                "format": "webp",
                "image_scene_list": [
                    {"scene": "normal", "width": 2400, "height": 2400, "uniq_key": "2400", "format": "webp"},
                    {"scene": "loss", "width": 1080, "height": 1080, "uniq_key": "1080", "format": "webp"},
                ],
            },
            "http_common_info": {"aid": AID},
        }
        response = await self._request(
            "POST",
            "/mweb/v1/get_history_by_ids",
            params=params,
            json_payload=payload,
            include_query_tokens=False,
        )
        ret = str(response.get("ret"))
        if ret != "0":
            code = response.get("ret") if isinstance(response.get("ret"), str) else ret
            message = response.get("message") or response.get("msg") or "查询任务状态失败"
            raise JimengApiError(message, code=str(code), payload=response)

        history_data = response.get("data", {}).get(history_id, {})
        if not history_data:
            return JimengSubmissionResult(
                history_id=history_id,
                status=TaskStatus.RUNNING,
                result_urls=[],
                raw=response,
            )

        queue_info = history_data.get("queue_info")
        queue_message = self._format_queue_message(queue_info) if queue_info else None
        error_code = self._extract_error_code(history_data)
        error_message = self._extract_error_message(history_data)
        result_urls = self._extract_images(history_data)
        status_code = history_data.get("status")

        if status_code == 50 and result_urls:
            status = TaskStatus.SUCCEEDED
        elif error_code:
            status = TaskStatus.FAILED
        elif status_code in {60, 70}:
            status = TaskStatus.FAILED
        elif queue_info:
            status = TaskStatus.QUEUED
        else:
            status = TaskStatus.RUNNING

        return JimengSubmissionResult(
            history_id=history_id,
            status=status,
            result_urls=result_urls,
            queue_message=queue_message,
            queue_info=queue_info,
            error_code=error_code,
            error_message=error_message,
            raw=history_data,
        )
    def _extract_error_code(self, history: Dict[str, Any]) -> str | None:
        for key in ("err_code", "task_err_code", "error_code"):
            value = history.get(key)
            if value:
                return str(value)
        return None

    def _extract_error_message(self, history: Dict[str, Any]) -> str | None:
        for key in ("err_msg", "task_err_msg", "status_msg", "error_msg"):
            value = history.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _extract_images(self, history: Dict[str, Any]) -> List[str]:
        result: List[str] = []
        uploaded = self._extract_uploaded_uris(history)
        resources = history.get("resources") or []
        for resource in resources:
            if resource.get("type") != "image":
                continue
            info = resource.get("image_info") or {}
            uri = resource.get("key")
            url = info.get("image_url")
            if url and (not uploaded or uri not in uploaded):
                result.append(url)
        if result:
            return result
        item_list = history.get("item_list") or []
        for item in item_list:
            image = item.get("image") or {}
            large_images = image.get("large_images") or []
            for large_image in large_images:
                url = large_image.get("image_url")
                if url:
                    result.append(url)
            if not large_images:
                url = image.get("image_url")
                if url:
                    result.append(url)
        # 去重保持顺序
        seen = set()
        unique: List[str] = []
        for url in result:
            if url not in seen:
                seen.add(url)
                unique.append(url)
        return unique

    def _extract_uploaded_uris(self, history: Dict[str, Any]) -> set[str]:
        draft_content = history.get("draft_content")
        if not draft_content:
            return set()
        try:
            data = json.loads(draft_content)
        except (TypeError, json.JSONDecodeError):
            return set()
        uploaded: set[str] = set()
        for component in data.get("component_list", []):
            abilities = component.get("abilities", {})
            blend_data = abilities.get("blend", {})
            for ability in blend_data.get("ability_list", []):
                if ability.get("image_uri_list"):
                    uploaded.update(ability["image_uri_list"])
        return uploaded

    def _format_queue_message(self, queue_info: Dict[str, Any]) -> str:
        try:
            queue_idx = queue_info.get("queue_idx", 0)
            queue_length = queue_info.get("queue_length", 0)
            status = queue_info.get("queue_status", 0)
            threshold = queue_info.get("priority_queue_display_threshold", {})
            waiting = int(threshold.get("waiting_time_threshold", 0))
            minutes, seconds = divmod(waiting, 60)
            if minutes > 0:
                time_desc = f"{minutes}分{seconds}秒" if seconds else f"{minutes}分钟"
            else:
                time_desc = f"{seconds}秒"
            if status == 1:
                if queue_idx and queue_length:
                    return (
                        "📊 总队列长度：{length}人\n"
                        "🔄 当前排队位置：第{idx}位\n"
                        "⏰ 预计等待时间：{time}"
                    ).format(length=queue_length, idx=queue_idx, time=time_desc)
                return f"🔄 任务已进入队列，预计等待时间：{time_desc}"
            return "🚀 当前无需排队，正在加速生成..."
        except Exception:  # pragma: no cover - 容错
            return "🔄 任务正在排队处理中，请稍候..."

    @property
    def account_label(self) -> str:
        return self._token_manager.account_label
