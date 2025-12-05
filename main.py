#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AstrBot 青龙面板管理插件

功能：
1. 环境变量管理（查看、添加、更新、删除、启用、禁用）
2. 定时任务管理（查看、执行、停止、启用、禁用、置顶、删除、日志）
3. 系统信息查询

版本: 1.0.1
"""

import time
from typing import Dict, List, Optional, Tuple, Any

import httpx

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


# 常量配置
DEFAULT_TIMEOUT = 10
TOKEN_EXPIRE_SECONDS = 6 * 24 * 3600  # 6天


class QinglongAPI:
    """青龙面板 API 封装（异步版本）
    
    使用共享的 HTTP 客户端以复用连接池，提高性能。
    """
    
    def __init__(self, host: str, client_id: str, client_secret: str):
        """初始化青龙 API"""
        self.host = host.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.token: Optional[str] = None
        self.token_expire: float = 0
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端（复用连接池）"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        return self._client
    
    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def get_token(self) -> bool:
        """获取访问令牌"""
        try:
            if self.token and time.time() < self.token_expire:
                return True
            
            client = await self._get_client()
            response = await client.get(
                f"{self.host}/open/auth/token",
                params={"client_id": self.client_id, "client_secret": self.client_secret}
            )
            result = response.json()
            
            if result.get('code') == 200:
                self.token = result['data']['token']
                self.token_expire = time.time() + TOKEN_EXPIRE_SECONDS
                return True
            else:
                logger.error(f"获取token失败: {result.get('message')}")
                return False
        
        except httpx.TimeoutException:
            logger.error("获取token超时，请检查网络连接")
            return False
        except httpx.ConnectError:
            logger.error("无法连接到青龙面板，请检查地址配置")
            return False
        except Exception as e:
            logger.error(f"获取token异常: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json_data: Any = None
    ) -> Tuple[bool, Any]:
        """统一的请求方法
        
        Returns:
            (success, data) - 成功时返回 (True, data)，失败时返回 (False, error_message)
        """
        if not await self.get_token():
            return False, "认证失败"
        
        try:
            client = await self._get_client()
            url = f"{self.host}{endpoint}"
            
            if method.upper() == "GET":
                response = await client.get(url, headers=self._get_headers(), params=params)
            elif method.upper() == "DELETE":
                response = await client.request("DELETE", url, headers=self._get_headers(), json=json_data)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=self._get_headers(), json=json_data)
            else:  # POST
                response = await client.post(url, headers=self._get_headers(), json=json_data)
            
            result = response.json()
            
            if result.get('code') == 200:
                return True, result.get('data', {})
            else:
                return False, result.get('message', '未知错误')
                
        except httpx.TimeoutException:
            return False, "请求超时"
        except httpx.ConnectError:
            return False, "连接失败"
        except Exception as e:
            return False, str(e)
    
    async def get_envs(self, search_value: str = "") -> List[Dict]:
        """获取环境变量列表"""
        params = {"searchValue": search_value} if search_value else None
        success, data = await self._request("GET", "/open/envs", params=params)
        
        if not success:
            return []
        
        if isinstance(data, dict):
            return data.get('data', [])
        return data if isinstance(data, list) else []
    
    async def add_env(self, name: str, value: str, remarks: str = "") -> Tuple[bool, str]:
        """添加环境变量"""
        success, data = await self._request("POST", "/open/envs", json_data=[{"name": name, "value": value, "remarks": remarks}])
        return success, "添加成功" if success else data
    
    async def update_env(self, env_id: int, name: str, value: str, remarks: str = "") -> Tuple[bool, str]:
        """更新环境变量"""
        success, data = await self._request("PUT", "/open/envs", json_data={"id": env_id, "name": name, "value": value, "remarks": remarks})
        return success, "更新成功" if success else data
    
    async def delete_env(self, env_id: int) -> Tuple[bool, str]:
        """删除环境变量"""
        success, data = await self._request("DELETE", "/open/envs", json_data=[env_id])
        return success, "删除成功" if success else data
    
    async def enable_env(self, env_ids: List[int]) -> Tuple[bool, str]:
        """启用环境变量"""
        success, data = await self._request("PUT", "/open/envs/enable", json_data=env_ids)
        return success, "启用成功" if success else data
    
    async def disable_env(self, env_ids: List[int]) -> Tuple[bool, str]:
        """禁用环境变量"""
        success, data = await self._request("PUT", "/open/envs/disable", json_data=env_ids)
        return success, "禁用成功" if success else data
    
    async def get_crons(self, search_value: str = "") -> List[Dict]:
        """获取定时任务列表"""
        params = {"searchValue": search_value} if search_value else None
        success, data = await self._request("GET", "/open/crons", params=params)
        
        if not success:
            return []
        
        if isinstance(data, dict):
            return data.get('data', [])
        return data if isinstance(data, list) else []
    
    async def run_cron(self, cron_ids: List[int]) -> Tuple[bool, str]:
        """执行定时任务"""
        success, data = await self._request("PUT", "/open/crons/run", json_data=cron_ids)
        return success, "执行成功" if success else data
    
    async def stop_cron(self, cron_ids: List[int]) -> Tuple[bool, str]:
        """停止定时任务"""
        success, data = await self._request("PUT", "/open/crons/stop", json_data=cron_ids)
        return success, "停止成功" if success else data
    
    async def enable_cron(self, cron_ids: List[int]) -> Tuple[bool, str]:
        """启用定时任务"""
        success, data = await self._request("PUT", "/open/crons/enable", json_data=cron_ids)
        return success, "启用成功" if success else data
    
    async def disable_cron(self, cron_ids: List[int]) -> Tuple[bool, str]:
        """禁用定时任务"""
        success, data = await self._request("PUT", "/open/crons/disable", json_data=cron_ids)
        return success, "禁用成功" if success else data
    
    async def pin_cron(self, cron_ids: List[int]) -> Tuple[bool, str]:
        """置顶定时任务"""
        success, data = await self._request("PUT", "/open/crons/pin", json_data=cron_ids)
        return success, "置顶成功" if success else data
    
    async def unpin_cron(self, cron_ids: List[int]) -> Tuple[bool, str]:
        """取消置顶定时任务"""
        success, data = await self._request("PUT", "/open/crons/unpin", json_data=cron_ids)
        return success, "取消置顶成功" if success else data
    
    async def delete_cron(self, cron_ids: List[int]) -> Tuple[bool, str]:
        """删除定时任务"""
        success, data = await self._request("DELETE", "/open/crons", json_data=cron_ids)
        return success, "删除成功" if success else data
    
    async def get_cron_log(self, cron_id: int) -> Tuple[bool, str]:
        """获取定时任务日志"""
        success, data = await self._request("GET", f"/open/crons/{cron_id}/log")
        return success, data if success else data
    
    async def get_system_info(self) -> Optional[Dict]:
        """获取系统信息"""
        success, data = await self._request("GET", "/open/system")
        return data if success and isinstance(data, dict) else None


@register("astrbot_plugin_qinglong", "Haitun", "青龙面板管理插件", "1.0.1")
class QinglongPlugin(Star):
    """AstrBot 青龙插件主类"""
    
    PAGE_SIZE = 10
    
    def __init__(self, context: Context, config: dict):
        """初始化插件"""
        super().__init__(context)
        self.config = config
        
        ql_host = config.get("qinglong_host", "http://localhost:5700")
        ql_client_id = config.get("qinglong_client_id", "")
        ql_client_secret = config.get("qinglong_client_secret", "")
        
        self.ql_api = QinglongAPI(ql_host, ql_client_id, ql_client_secret)
        
        logger.info("青龙面板插件已加载")
        logger.info(f"  Host: {ql_host}")
    
    @filter.command("ql")
    async def ql_command(self, event: AstrMessageEvent):
        '''青龙面板管理命令，支持环境变量和定时任务的增删改查'''
        if not self.ql_api:
            yield event.plain_result("❌ 插件未正确初始化，请检查配置")
            return
        
        parts = event.message_str.strip().split()
        command = parts[1].lower() if len(parts) > 1 else "help"
        
        # 命令路由
        handlers = {
            "help": self._handle_help,
            "envs": self._handle_envs,
            "list": self._handle_envs,
            "add": self._handle_add_env,
            "update": self._handle_update_env,
            "delete": self._handle_delete_env,
            "enable": self._handle_enable_env,
            "disable": self._handle_disable_env,
            "ls": self._handle_crons,
            "run": self._handle_run_cron,
            "stop": self._handle_stop_cron,
            "log": self._handle_cron_log,
            "cron": self._handle_cron_action,
            "info": self._handle_info,
        }
        
        handler = handlers.get(command)
        if handler:
            async for result in handler(event, parts):
                yield result
        else:
            yield event.plain_result(f"❌ 未知命令: {command}\n使用 /ql 查看帮助")
    
    async def _handle_help(self, event: AstrMessageEvent, parts: list):
        """显示帮助信息"""
        help_text = """📦 青龙面板管理插件 v1.0.1

📋 环境变量:
/ql envs [关键词] [页码] - 查看环境变量
/ql add <名称> <值> [备注] - 添加
/ql update <名称> <值> - 更新（按名称）
/ql update id:<ID> <值> - 更新（按ID）
/ql delete <名称> - 删除
/ql enable/disable <名称> - 启用/禁用

⏰ 定时任务:
/ql ls [页码] - 查看任务列表
/ql run <任务ID> - 执行任务
/ql stop <任务ID> - 停止任务
/ql log <任务ID> - 查看日志
/ql cron enable/disable <任务ID> - 启用/禁用
/ql cron pin/unpin <任务ID> - 置顶/取消
/ql cron delete <任务ID> - 删除任务

📊 系统信息:
/ql info - 查看系统信息"""
        yield event.plain_result(help_text)
    
    async def _handle_envs(self, event: AstrMessageEvent, parts: list):
        """查看环境变量列表"""
        search_value = ""
        page = 1
        
        if len(parts) > 2:
            if parts[2].isdigit():
                page = int(parts[2])
            else:
                search_value = parts[2]
                if len(parts) > 3 and parts[3].isdigit():
                    page = int(parts[3])
        
        envs = await self.ql_api.get_envs(search_value)
        
        if not envs:
            msg = f"❌ 未找到包含 '{search_value}' 的环境变量" if search_value else "📭 暂无环境变量"
            yield event.plain_result(msg)
            return
        
        total = len(envs)
        start = (page - 1) * self.PAGE_SIZE
        page_envs = envs[start:start + self.PAGE_SIZE]
        
        if not page_envs:
            yield event.plain_result(f"❌ 页码超出范围 (共 {(total + self.PAGE_SIZE - 1) // self.PAGE_SIZE} 页)")
            return
        
        search_info = f" (搜索: {search_value})" if search_value else ""
        result = f"📋 环境变量列表{search_info} (第 {page} 页，共 {total} 个):\n\n"
        
        for env in page_envs:
            status = "🟢" if env.get('status') == 0 else "🔴"
            value = env.get('value', '')
            result += f"{status} {env.get('name')}\n"
            result += f"  ID: {env.get('id')}\n"
            result += f"  值: {value[:50]}{'...' if len(value) > 50 else ''}\n"
            if env.get('remarks'):
                result += f"  备注: {env.get('remarks')}\n"
            result += "\n"
        
        total_pages = (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        if page < total_pages:
            next_cmd = f"/ql envs {search_value} {page + 1}" if search_value else f"/ql envs {page + 1}"
            result += f"💡 使用 {next_cmd} 查看下一页"
        
        yield event.plain_result(result)
    
    async def _handle_add_env(self, event: AstrMessageEvent, parts: list):
        """添加环境变量"""
        if len(parts) < 4:
            yield event.plain_result("使用方法: /ql add <变量名> <变量值> [备注]")
            return
        
        name, value = parts[2], parts[3]
        remarks = " ".join(parts[4:]) if len(parts) > 4 else ""
        
        success, msg = await self.ql_api.add_env(name, value, remarks)
        yield event.plain_result(f"{'✅' if success else '❌'} {msg}: {name}")
    
    async def _handle_update_env(self, event: AstrMessageEvent, parts: list):
        """更新环境变量"""
        if len(parts) < 4:
            yield event.plain_result("使用方法:\n/ql update <变量名> <值>\n/ql update id:<ID> <值>")
            return
        
        name_or_id = parts[2]
        value = " ".join(parts[3:])  # 值可能包含空格
        
        # 按 ID 更新
        if name_or_id.startswith("id:"):
            try:
                env_id = int(name_or_id[3:])
            except ValueError:
                yield event.plain_result(f"❌ 无效的ID格式: {name_or_id}")
                return
            
            all_envs = await self.ql_api.get_envs("")
            target_env = next((e for e in all_envs if e.get('id') == env_id), None)
            
            if not target_env:
                yield event.plain_result(f"❌ 未找到ID为 {env_id} 的环境变量")
                return
            
            success, msg = await self.ql_api.update_env(env_id, target_env.get('name'), value, target_env.get('remarks', ''))
            if success:
                yield event.plain_result(f"✅ 更新成功\nID: {env_id}\n名称: {target_env.get('name')}")
            else:
                yield event.plain_result(f"❌ 更新失败: {msg}")
            return
        
        # 按名称更新
        envs = await self.ql_api.get_envs(name_or_id)
        
        if not envs:
            yield event.plain_result(f"❌ 未找到环境变量: {name_or_id}")
            return
        
        if len(envs) > 1:
            result = f"⚠️ 找到 {len(envs)} 个名为 '{name_or_id}' 的变量:\n\n"
            for env in envs:
                result += f"ID: {env.get('id')} - {env.get('remarks', '无备注')}\n"
            result += f"\n💡 使用 /ql update id:{envs[0].get('id')} <新值> 精确更新"
            yield event.plain_result(result)
            return
        
        env = envs[0]
        success, msg = await self.ql_api.update_env(env['id'], name_or_id, value, env.get('remarks', ''))
        yield event.plain_result(f"{'✅' if success else '❌'} {msg}: {name_or_id}")
    
    async def _handle_delete_env(self, event: AstrMessageEvent, parts: list):
        """删除环境变量"""
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql delete <变量名>")
            return
        
        name = parts[2]
        envs = await self.ql_api.get_envs(name)
        
        if not envs:
            yield event.plain_result(f"❌ 未找到环境变量: {name}")
            return
        
        success, msg = await self.ql_api.delete_env(envs[0]['id'])
        yield event.plain_result(f"{'✅' if success else '❌'} {msg}: {name}")
    
    async def _handle_enable_env(self, event: AstrMessageEvent, parts: list):
        """启用环境变量"""
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql enable <变量名>")
            return
        
        name = parts[2]
        envs = await self.ql_api.get_envs(name)
        
        if not envs:
            yield event.plain_result(f"❌ 未找到环境变量: {name}")
            return
        
        success, msg = await self.ql_api.enable_env([env['id'] for env in envs])
        yield event.plain_result(f"{'✅' if success else '❌'} {msg}: {name}")
    
    async def _handle_disable_env(self, event: AstrMessageEvent, parts: list):
        """禁用环境变量"""
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql disable <变量名>")
            return
        
        name = parts[2]
        envs = await self.ql_api.get_envs(name)
        
        if not envs:
            yield event.plain_result(f"❌ 未找到环境变量: {name}")
            return
        
        success, msg = await self.ql_api.disable_env([env['id'] for env in envs])
        yield event.plain_result(f"{'✅' if success else '❌'} {msg}: {name}")
    
    async def _handle_crons(self, event: AstrMessageEvent, parts: list):
        """查看定时任务列表"""
        page = 1
        if len(parts) > 2 and parts[2].isdigit():
            page = int(parts[2])
        
        crons = await self.ql_api.get_crons()
        
        if not crons:
            yield event.plain_result("📭 暂无定时任务")
            return
        
        total = len(crons)
        start = (page - 1) * self.PAGE_SIZE
        page_crons = crons[start:start + self.PAGE_SIZE]
        
        if not page_crons:
            yield event.plain_result(f"❌ 页码超出范围 (共 {(total + self.PAGE_SIZE - 1) // self.PAGE_SIZE} 页)")
            return
        
        result = f"📋 定时任务列表 (第 {page} 页，共 {total} 个):\n\n"
        for cron in page_crons:
            status = "🟢" if cron.get('status') == 0 else "🔴"
            cmd = cron.get('command', '')
            result += f"{status} {cron.get('name', '未命名')}\n"
            result += f"  ID: {cron.get('id')}\n"
            result += f"  命令: {cmd[:50]}{'...' if len(cmd) > 50 else ''}\n"
            result += f"  定时: {cron.get('schedule', '无')}\n\n"
        
        total_pages = (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        if page < total_pages:
            result += f"💡 使用 /ql ls {page + 1} 查看下一页"
        
        yield event.plain_result(result)
    
    async def _handle_run_cron(self, event: AstrMessageEvent, parts: list):
        """执行定时任务"""
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql run <任务ID>")
            return
        
        try:
            cron_id = int(parts[2])
        except ValueError:
            yield event.plain_result("❌ 任务ID必须是数字")
            return
        
        success, msg = await self.ql_api.run_cron([cron_id])
        if success:
            yield event.plain_result(f"✅ 已启动任务: {cron_id}\n💡 使用 /ql log {cron_id} 查看日志")
        else:
            yield event.plain_result(f"❌ 执行失败: {msg}")
    
    async def _handle_stop_cron(self, event: AstrMessageEvent, parts: list):
        """停止定时任务"""
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql stop <任务ID>")
            return
        
        try:
            cron_id = int(parts[2])
        except ValueError:
            yield event.plain_result("❌ 任务ID必须是数字")
            return
        
        success, msg = await self.ql_api.stop_cron([cron_id])
        yield event.plain_result(f"{'✅ 已停止任务' if success else '❌ 停止失败'}: {cron_id}")
    
    async def _handle_cron_log(self, event: AstrMessageEvent, parts: list):
        """查看任务日志"""
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql log <任务ID>")
            return
        
        try:
            cron_id = int(parts[2])
        except ValueError:
            yield event.plain_result("❌ 任务ID必须是数字")
            return
        
        success, log_content = await self.ql_api.get_cron_log(cron_id)
        
        if not success:
            yield event.plain_result(f"❌ 获取日志失败: {log_content}")
            return
        
        if not log_content:
            yield event.plain_result(f"📝 任务 {cron_id} 暂无日志")
            return
        
        if len(log_content) > 1000:
            log_content = "...\n" + log_content[-1000:]
        
        yield event.plain_result(f"📝 任务 {cron_id} 日志:\n\n{log_content}")
    
    async def _handle_cron_action(self, event: AstrMessageEvent, parts: list):
        """定时任务操作（启用/禁用/置顶/删除）"""
        if len(parts) < 4:
            yield event.plain_result("使用方法:\n/ql cron enable/disable <任务ID>\n/ql cron pin/unpin <任务ID>\n/ql cron delete <任务ID>")
            return
        
        action = parts[2].lower()
        try:
            cron_id = int(parts[3])
        except ValueError:
            yield event.plain_result("❌ 任务ID必须是数字")
            return
        
        actions = {
            "enable": (self.ql_api.enable_cron, "启用"),
            "disable": (self.ql_api.disable_cron, "禁用"),
            "pin": (self.ql_api.pin_cron, "置顶"),
            "unpin": (self.ql_api.unpin_cron, "取消置顶"),
            "delete": (self.ql_api.delete_cron, "删除"),
        }
        
        if action not in actions:
            yield event.plain_result(f"❌ 未知操作: {action}\n支持: enable, disable, pin, unpin, delete")
            return
        
        func, action_name = actions[action]
        success, msg = await func([cron_id])
        icon = "📌" if action in ("pin", "unpin") else ("✅" if success else "❌")
        yield event.plain_result(f"{icon} {action_name}任务 {cron_id}: {msg}")
    
    async def _handle_info(self, event: AstrMessageEvent, parts: list):
        """查看系统信息"""
        system_info = await self.ql_api.get_system_info()
        
        if not system_info:
            yield event.plain_result("❌ 获取系统信息失败")
            return
        
        result = "📊 青龙面板系统信息:\n\n"
        
        if 'version' in system_info:
            result += f"🖥️ 版本: {system_info['version']}"
            if 'branch' in system_info:
                result += f" ({system_info['branch']})"
            result += "\n"
        
        if 'isInitialized' in system_info:
            status = "✅ 已初始化" if system_info['isInitialized'] else "⚠️ 未初始化"
            result += f"📌 状态: {status}\n"
        
        yield event.plain_result(result)
    
    async def terminate(self):
        """插件卸载时调用"""
        await self.ql_api.close()
        logger.info("青龙面板插件已卸载")
