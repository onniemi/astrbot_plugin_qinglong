#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
from typing import Any, Optional

import httpx

from astrbot.api import logger


DEFAULT_TIMEOUT = 10
TOKEN_EXPIRE_SECONDS = 6 * 24 * 3600  # 6天


class QinglongAPI:
    """青龙面板 API 封装。"""

    def __init__(self, host: str, client_id: str, client_secret: str):
        self.host = host.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.token: Optional[str] = None
        self.token_expire: float = 0
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def is_configured(self) -> bool:
        return bool(self.host and self.client_id and self.client_secret)

    def _invalidate_token(self):
        self.token = None
        self.token_expire = 0

    async def get_token(self, force_refresh: bool = False) -> bool:
        try:
            if not self.is_configured():
                logger.error("青龙面板凭据未配置完整，无法获取 token")
                return False

            if not force_refresh and self.token and time.time() < self.token_expire:
                return True

            client = await self._get_client()
            response = await client.get(
                f"{self.host}/open/auth/token",
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            result = response.json()

            if not isinstance(result, dict):
                logger.error(f"获取 token 响应格式异常: {type(result).__name__}")
                return False

            token_data = result.get("data")
            if result.get("code") == 200 and isinstance(token_data, dict) and token_data.get("token"):
                self.token = token_data["token"]
                self.token_expire = time.time() + TOKEN_EXPIRE_SECONDS
                return True

            logger.error(f"获取 token 失败: {result.get('message')}")
            return False
        except httpx.TimeoutException:
            logger.error("获取 token 超时，请检查网络连接")
            return False
        except httpx.ConnectError:
            logger.error("无法连接到青龙面板，请检查地址配置")
            return False
        except httpx.HTTPStatusError as error:
            logger.error(f"获取 token 失败: HTTP {error.response.status_code}")
            return False
        except json.JSONDecodeError:
            logger.error("获取 token 失败: 响应不是合法 JSON")
            return False
        except Exception as error:
            logger.error(f"获取 token 异常: {error}")
            return False

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Any = None,
        retry_on_auth_failure: bool = True,
    ) -> tuple[bool, Any]:
        if not await self.get_token():
            return False, "认证失败"

        try:
            client = await self._get_client()
            request_kwargs: dict[str, Any] = {"headers": self._get_headers()}
            if params:
                request_kwargs["params"] = params
            if method.upper() != "GET":
                request_kwargs["json"] = json_data

            response = await client.request(method.upper(), f"{self.host}{endpoint}", **request_kwargs)

            if response.status_code == 401 and retry_on_auth_failure:
                self._invalidate_token()
                if await self.get_token(force_refresh=True):
                    return await self._request(
                        method,
                        endpoint,
                        params=params,
                        json_data=json_data,
                        retry_on_auth_failure=False,
                    )
                return False, "认证已失效，请检查青龙凭据"

            response.raise_for_status()
            result = response.json()

            if not isinstance(result, dict):
                return False, "响应格式错误"

            if result.get("code") in (401, 403) and retry_on_auth_failure:
                self._invalidate_token()
                if await self.get_token(force_refresh=True):
                    return await self._request(
                        method,
                        endpoint,
                        params=params,
                        json_data=json_data,
                        retry_on_auth_failure=False,
                    )
                return False, "认证已失效，请检查青龙凭据"

            if result.get("code") == 200:
                return True, result.get("data", {})
            return False, result.get("message", "未知错误")
        except httpx.TimeoutException:
            return False, "请求超时"
        except httpx.ConnectError:
            return False, "连接失败"
        except httpx.HTTPStatusError as error:
            return False, f"HTTP {error.response.status_code}"
        except json.JSONDecodeError:
            return False, "响应解析失败"
        except Exception as error:
            return False, str(error)

    async def get_envs(self, search_value: str = "") -> list[dict]:
        params = {"searchValue": search_value} if search_value else None
        success, data = await self._request("GET", "/open/envs", params=params)
        if not success:
            return []
        if isinstance(data, dict):
            return data.get("data", [])
        return data if isinstance(data, list) else []

    async def add_env(self, name: str, value: str, remarks: str = "") -> tuple[bool, str]:
        success, data = await self._request(
            "POST",
            "/open/envs",
            json_data=[{"name": name, "value": value, "remarks": remarks}],
        )
        return success, "添加成功" if success else str(data)

    async def update_env(self, env_id: int, name: str, value: str, remarks: str = "") -> tuple[bool, str]:
        success, data = await self._request(
            "PUT",
            "/open/envs",
            json_data={"id": env_id, "name": name, "value": value, "remarks": remarks},
        )
        return success, "更新成功" if success else str(data)

    async def delete_env(self, env_id: int) -> tuple[bool, str]:
        success, data = await self._request("DELETE", "/open/envs", json_data=[env_id])
        return success, "删除成功" if success else str(data)

    async def enable_env(self, env_ids: list[int]) -> tuple[bool, str]:
        success, data = await self._request("PUT", "/open/envs/enable", json_data=env_ids)
        return success, "启用成功" if success else str(data)

    async def disable_env(self, env_ids: list[int]) -> tuple[bool, str]:
        success, data = await self._request("PUT", "/open/envs/disable", json_data=env_ids)
        return success, "禁用成功" if success else str(data)

    async def get_crons(self, search_value: str = "") -> list[dict]:
        params = {"searchValue": search_value} if search_value else None
        success, data = await self._request("GET", "/open/crons", params=params)
        if not success:
            return []
        if isinstance(data, dict):
            return data.get("data", [])
        return data if isinstance(data, list) else []

    async def run_cron(self, cron_ids: list[int]) -> tuple[bool, str]:
        success, data = await self._request("PUT", "/open/crons/run", json_data=cron_ids)
        return success, "执行成功" if success else str(data)

    async def stop_cron(self, cron_ids: list[int]) -> tuple[bool, str]:
        success, data = await self._request("PUT", "/open/crons/stop", json_data=cron_ids)
        return success, "停止成功" if success else str(data)

    async def enable_cron(self, cron_ids: list[int]) -> tuple[bool, str]:
        success, data = await self._request("PUT", "/open/crons/enable", json_data=cron_ids)
        return success, "启用成功" if success else str(data)

    async def disable_cron(self, cron_ids: list[int]) -> tuple[bool, str]:
        success, data = await self._request("PUT", "/open/crons/disable", json_data=cron_ids)
        return success, "禁用成功" if success else str(data)

    async def pin_cron(self, cron_ids: list[int]) -> tuple[bool, str]:
        success, data = await self._request("PUT", "/open/crons/pin", json_data=cron_ids)
        return success, "置顶成功" if success else str(data)

    async def unpin_cron(self, cron_ids: list[int]) -> tuple[bool, str]:
        success, data = await self._request("PUT", "/open/crons/unpin", json_data=cron_ids)
        return success, "取消置顶成功" if success else str(data)

    async def delete_cron(self, cron_ids: list[int]) -> tuple[bool, str]:
        success, data = await self._request("DELETE", "/open/crons", json_data=cron_ids)
        return success, "删除成功" if success else str(data)

    async def get_cron_log(self, cron_id: int) -> tuple[bool, str]:
        success, data = await self._request("GET", f"/open/crons/{cron_id}/log")
        return success, data if isinstance(data, str) else str(data or "")

    async def get_system_info(self) -> Optional[dict]:
        success, data = await self._request("GET", "/open/system")
        return data if success and isinstance(data, dict) else None
