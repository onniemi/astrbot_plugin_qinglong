#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AstrBot 青龙面板管理插件

功能：
1. 环境变量管理（查看、添加、更新、删除、启用、禁用）
2. 定时任务管理（查看、执行、停止、启用、禁用、置顶、删除、日志）
3. 系统信息查询

版本: 1.0.0
"""

import time
import json
from typing import Dict, List, Optional

import httpx

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


class QinglongAPI:
    """青龙面板 API 封装（异步版本）"""
    
    def __init__(self, host: str, client_id: str, client_secret: str):
        """初始化青龙 API"""
        self.host = host.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.token: Optional[str] = None
        self.token_expire: float = 0
    
    async def get_token(self) -> bool:
        """获取访问令牌"""
        try:
            if self.token and time.time() < self.token_expire:
                return True
            
            url = f"{self.host}/open/auth/token"
            params = {
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params)
                result = response.json()
            
            if result.get('code') == 200:
                self.token = result['data']['token']
                self.token_expire = time.time() + 6 * 24 * 3600
                return True
            else:
                logger.error(f"获取token失败: {result.get('message')}")
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
    
    async def get_envs(self, search_value: str = "") -> List[Dict]:
        """获取环境变量列表"""
        if not await self.get_token():
            return []
        
        try:
            url = f"{self.host}/open/envs"
            params = {"searchValue": search_value} if search_value else {}
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=self._get_headers(), params=params)
                result = response.json()
            
            if result.get('code') == 200:
                data = result.get('data', [])
                if isinstance(data, dict):
                    return data.get('data', [])
                return data if isinstance(data, list) else []
            else:
                logger.error(f"获取环境变量失败: {result.get('message')}")
                return []
        
        except Exception as e:
            logger.error(f"获取环境变量异常: {e}")
            return []
    
    async def add_env(self, name: str, value: str, remarks: str = "") -> bool:
        """添加环境变量"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/envs"
            data = [{"name": name, "value": value, "remarks": remarks}]
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, headers=self._get_headers(), json=data)
                result = response.json()
            
            if result.get('code') == 200:
                logger.info(f"添加环境变量成功: {name}")
                return True
            else:
                logger.error(f"添加环境变量失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"添加环境变量异常: {e}")
            return False
    
    async def update_env(self, env_id: int, name: str, value: str, remarks: str = "") -> bool:
        """更新环境变量"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/envs"
            data = {"id": env_id, "name": name, "value": value, "remarks": remarks}
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.put(url, headers=self._get_headers(), json=data)
                result = response.json()
            
            if result.get('code') == 200:
                logger.info(f"更新环境变量成功: {name}")
                return True
            else:
                logger.error(f"更新环境变量失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"更新环境变量异常: {e}")
            return False
    
    async def delete_env(self, env_id: int) -> bool:
        """删除环境变量"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/envs"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.request("DELETE", url, headers=self._get_headers(), json=[env_id])
                result = response.json()
            
            if result.get('code') == 200:
                logger.info(f"删除环境变量成功: ID={env_id}")
                return True
            else:
                logger.error(f"删除环境变量失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"删除环境变量异常: {e}")
            return False
    
    async def enable_env(self, env_ids: List[int]) -> bool:
        """启用环境变量"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/envs/enable"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.put(url, headers=self._get_headers(), json=env_ids)
                result = response.json()
            
            if result.get('code') == 200:
                logger.info("启用环境变量成功")
                return True
            else:
                logger.error(f"启用环境变量失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"启用环境变量异常: {e}")
            return False
    
    async def disable_env(self, env_ids: List[int]) -> bool:
        """禁用环境变量"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/envs/disable"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.put(url, headers=self._get_headers(), json=env_ids)
                result = response.json()
            
            if result.get('code') == 200:
                logger.info("禁用环境变量成功")
                return True
            else:
                logger.error(f"禁用环境变量失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"禁用环境变量异常: {e}")
            return False
    
    async def get_crons(self, search_value: str = "") -> List[Dict]:
        """获取定时任务列表"""
        if not await self.get_token():
            return []
        
        try:
            url = f"{self.host}/open/crons"
            params = {"searchValue": search_value} if search_value else {}
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=self._get_headers(), params=params)
                result = response.json()
            
            if result.get('code') == 200:
                data = result.get('data', [])
                if isinstance(data, dict):
                    return data.get('data', [])
                return data if isinstance(data, list) else []
            else:
                logger.error(f"获取定时任务失败: {result.get('message')}")
                return []
        
        except Exception as e:
            logger.error(f"获取定时任务异常: {e}")
            return []
    
    async def run_cron(self, cron_ids: List[int]) -> bool:
        """执行定时任务"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/crons/run"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.put(url, headers=self._get_headers(), json=cron_ids)
                result = response.json()
            
            if result.get('code') == 200:
                logger.info("执行定时任务成功")
                return True
            else:
                logger.error(f"执行定时任务失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"执行定时任务异常: {e}")
            return False
    
    async def get_cron_log(self, cron_id: int) -> Optional[str]:
        """获取定时任务日志"""
        if not await self.get_token():
            return None
        
        try:
            url = f"{self.host}/open/crons/{cron_id}/log"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=self._get_headers())
                result = response.json()
            
            if result.get('code') == 200:
                return result.get('data', '')
            else:
                logger.error(f"获取任务日志失败: {result.get('message')}")
                return None
        
        except Exception as e:
            logger.error(f"获取任务日志异常: {e}")
            return None
    
    async def stop_cron(self, cron_ids: List[int]) -> bool:
        """停止定时任务"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/crons/stop"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.put(url, headers=self._get_headers(), json=cron_ids)
                result = response.json()
            
            if result.get('code') == 200:
                logger.info("停止定时任务成功")
                return True
            else:
                logger.error(f"停止定时任务失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"停止定时任务异常: {e}")
            return False
    
    async def enable_cron(self, cron_ids: List[int]) -> bool:
        """启用定时任务"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/crons/enable"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.put(url, headers=self._get_headers(), json=cron_ids)
                result = response.json()
            
            if result.get('code') == 200:
                logger.info("启用定时任务成功")
                return True
            else:
                logger.error(f"启用定时任务失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"启用定时任务异常: {e}")
            return False
    
    async def disable_cron(self, cron_ids: List[int]) -> bool:
        """禁用定时任务"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/crons/disable"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.put(url, headers=self._get_headers(), json=cron_ids)
                result = response.json()
            
            if result.get('code') == 200:
                logger.info("禁用定时任务成功")
                return True
            else:
                logger.error(f"禁用定时任务失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"禁用定时任务异常: {e}")
            return False
    
    async def pin_cron(self, cron_ids: List[int]) -> bool:
        """置顶定时任务"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/crons/pin"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.put(url, headers=self._get_headers(), json=cron_ids)
                result = response.json()
            
            if result.get('code') == 200:
                logger.info("置顶定时任务成功")
                return True
            else:
                logger.error(f"置顶定时任务失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"置顶定时任务异常: {e}")
            return False
    
    async def unpin_cron(self, cron_ids: List[int]) -> bool:
        """取消置顶定时任务"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/crons/unpin"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.put(url, headers=self._get_headers(), json=cron_ids)
                result = response.json()
            
            if result.get('code') == 200:
                logger.info("取消置顶定时任务成功")
                return True
            else:
                logger.error(f"取消置顶定时任务失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"取消置顶定时任务异常: {e}")
            return False
    
    async def delete_cron(self, cron_ids: List[int]) -> bool:
        """删除定时任务"""
        if not await self.get_token():
            return False
        
        try:
            url = f"{self.host}/open/crons"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.request("DELETE", url, headers=self._get_headers(), json=cron_ids)
                result = response.json()
            
            if result.get('code') == 200:
                logger.info("删除定时任务成功")
                return True
            else:
                logger.error(f"删除定时任务失败: {result.get('message')}")
                return False
        
        except Exception as e:
            logger.error(f"删除定时任务异常: {e}")
            return False
    
    async def get_system_info(self) -> Optional[Dict]:
        """获取系统信息"""
        if not await self.get_token():
            return None
        
        try:
            url = f"{self.host}/open/system"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=self._get_headers())
                result = response.json()
            
            if result.get('code') == 200:
                return result.get('data', {})
            else:
                logger.error(f"获取系统信息失败: {result.get('message')}")
                return None
        
        except Exception as e:
            logger.error(f"获取系统信息异常: {e}")
            return None


@register("astrbot_plugin_qinglong", "Your Name", "青龙面板管理插件", "1.0.0")
class QinglongPlugin(Star):
    """AstrBot 青龙插件主类"""
    
    def __init__(self, context: Context, config: dict):
        """初始化插件
        
        Args:
            context: AstrBot 上下文
            config: 插件配置（从 _conf_schema.json 解析）
        """
        super().__init__(context)
        self.config = config
        
        # 读取配置项
        ql_host = config.get("qinglong_host", "http://localhost:5700")
        ql_client_id = config.get("qinglong_client_id", "")
        ql_client_secret = config.get("qinglong_client_secret", "")
        
        # 初始化青龙 API
        self.ql_api = QinglongAPI(ql_host, ql_client_id, ql_client_secret)
        
        logger.info("青龙面板插件已加载")
        logger.info(f"  Host: {ql_host}")
    
    @filter.command("ql")
    async def ql_command(self, event: AstrMessageEvent):
        '''青龙面板管理命令，支持环境变量和定时任务的增删改查'''
        if not self.ql_api:
            yield event.plain_result("❌ 插件未正确初始化，请检查配置")
            return
        
        message = event.message_str.strip()
        parts = message.split()
        
        if len(parts) < 2:
            help_text = """📦 青龙面板管理插件 v1.0

📋 环境变量:
/ql envs [关键词] [页码] - 查看环境变量
/ql add <名称> <值> [备注] - 添加
/ql update <名称> <值> [备注] - 更新（按名称）
/ql update id:<ID> <值> [备注] - 更新（按ID）
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
            return
        
        command = parts[1].lower()
        
        # 查看环境变量列表
        if command in ("list", "envs"):
            search_value = ""
            page = 1
            page_size = 10
            
            if len(parts) > 2:
                try:
                    page = int(parts[2])
                except ValueError:
                    search_value = parts[2]
                    if len(parts) > 3:
                        try:
                            page = int(parts[3])
                        except ValueError:
                            pass
            
            envs = await self.ql_api.get_envs(search_value)
            
            if not envs:
                if search_value:
                    yield event.plain_result(f"❌ 未找到包含 '{search_value}' 的环境变量")
                else:
                    yield event.plain_result("📭 暂无环境变量")
                return
            
            total = len(envs)
            start = (page - 1) * page_size
            end = start + page_size
            page_envs = envs[start:end]
            
            if not page_envs:
                yield event.plain_result(f"❌ 页码超出范围 (共 {(total + page_size - 1) // page_size} 页)")
                return
            
            search_info = f" (搜索: {search_value})" if search_value else ""
            result = f"📋 环境变量列表{search_info} (第 {page} 页，共 {total} 个):\n\n"
            
            for env in page_envs:
                status = "🟢" if env.get('status') == 0 else "🔴"
                result += f"{status} {env.get('name')}\n"
                result += f"  ID: {env.get('id')}\n"
                value = env.get('value', '')
                result += f"  值: {value[:50]}{'...' if len(value) > 50 else ''}\n"
                if env.get('remarks'):
                    result += f"  备注: {env.get('remarks')}\n"
                result += "\n"
            
            total_pages = (total + page_size - 1) // page_size
            if page < total_pages:
                next_cmd = f"/ql envs {search_value} {page + 1}" if search_value else f"/ql envs {page + 1}"
                result += f"💡 使用 {next_cmd} 查看下一页"
            
            yield event.plain_result(result)
        
        # 添加环境变量
        elif command == "add":
            if len(parts) < 4:
                yield event.plain_result("使用方法: /ql add <变量名> <变量值> [备注]")
                return
            
            name = parts[2]
            value = parts[3]
            remarks = " ".join(parts[4:]) if len(parts) > 4 else ""
            
            if await self.ql_api.add_env(name, value, remarks):
                yield event.plain_result(f"✅ 添加环境变量成功: {name}")
            else:
                yield event.plain_result(f"❌ 添加环境变量失败: {name}")
        
        # 更新环境变量
        elif command == "update":
            if len(parts) < 4:
                yield event.plain_result("使用方法:\n/ql update <变量名> <值>\n/ql update id:<ID> <值>\n\n💡 值会自动合并所有空格后的内容")
                return
            
            name_or_id = parts[2]
            # 将剩余所有部分作为值（cookie 等值可能包含空格）
            value = " ".join(parts[3:])
            remarks = ""  # 更新时不修改备注，保留原备注
            
            if name_or_id.startswith("id:"):
                try:
                    env_id = int(name_or_id[3:])
                    all_envs = await self.ql_api.get_envs("")
                    target_env = next((e for e in all_envs if e.get('id') == env_id), None)
                    
                    if not target_env:
                        yield event.plain_result(f"❌ 未找到ID为 {env_id} 的环境变量")
                        return
                    
                    original_name = target_env.get('name')
                    final_remarks = target_env.get('remarks', '')  # 保留原备注
                    
                    if await self.ql_api.update_env(env_id, original_name, value, final_remarks):
                        result = f"✅ 更新环境变量成功\nID: {env_id}\n名称: {original_name}"
                        yield event.plain_result(result)
                    else:
                        yield event.plain_result(f"❌ 更新环境变量失败: ID {env_id}")
                    return
                    
                except ValueError:
                    yield event.plain_result(f"❌ 无效的ID格式: {name_or_id}")
                    return
            
            name = name_or_id
            envs = await self.ql_api.get_envs(name)
            
            if not envs:
                yield event.plain_result(f"❌ 未找到环境变量: {name}")
                return
            
            if len(envs) > 1:
                result = f"⚠️ 找到 {len(envs)} 个名为 '{name}' 的变量:\n\n"
                for env in envs:
                    result += f"ID: {env.get('id')} - {env.get('remarks', '无备注')}\n"
                result += f"\n💡 使用 /ql update id:{envs[0].get('id')} <新值> 精确更新"
                yield event.plain_result(result)
                return
            
            env = envs[0]
            original_remarks = env.get('remarks', '')  # 保留原备注
            if await self.ql_api.update_env(env['id'], name, value, original_remarks):
                yield event.plain_result(f"✅ 更新环境变量成功: {name}")
            else:
                yield event.plain_result(f"❌ 更新环境变量失败: {name}")
        
        # 删除环境变量
        elif command == "delete":
            if len(parts) < 3:
                yield event.plain_result("使用方法: /ql delete <变量名>")
                return
            
            name = parts[2]
            envs = await self.ql_api.get_envs(name)
            
            if not envs:
                yield event.plain_result(f"❌ 未找到环境变量: {name}")
                return
            
            env = envs[0]
            if await self.ql_api.delete_env(env['id']):
                yield event.plain_result(f"✅ 删除环境变量成功: {name}")
            else:
                yield event.plain_result(f"❌ 删除环境变量失败: {name}")
        
        # 启用环境变量
        elif command == "enable":
            if len(parts) < 3:
                yield event.plain_result("使用方法: /ql enable <变量名>")
                return
            
            name = parts[2]
            envs = await self.ql_api.get_envs(name)
            
            if not envs:
                yield event.plain_result(f"❌ 未找到环境变量: {name}")
                return
            
            env_ids = [env['id'] for env in envs]
            if await self.ql_api.enable_env(env_ids):
                yield event.plain_result(f"✅ 启用环境变量成功: {name}")
            else:
                yield event.plain_result(f"❌ 启用环境变量失败: {name}")
        
        # 禁用环境变量
        elif command == "disable":
            if len(parts) < 3:
                yield event.plain_result("使用方法: /ql disable <变量名>")
                return
            
            name = parts[2]
            envs = await self.ql_api.get_envs(name)
            
            if not envs:
                yield event.plain_result(f"❌ 未找到环境变量: {name}")
                return
            
            env_ids = [env['id'] for env in envs]
            if await self.ql_api.disable_env(env_ids):
                yield event.plain_result(f"✅ 禁用环境变量成功: {name}")
            else:
                yield event.plain_result(f"❌ 禁用环境变量失败: {name}")
        
        # 查看定时任务列表
        elif command == "ls":
            page = 1
            page_size = 10
            
            if len(parts) > 2:
                try:
                    page = int(parts[2])
                except ValueError:
                    yield event.plain_result("❌ 页码必须是数字")
                    return
            
            crons = await self.ql_api.get_crons()
            
            if not crons:
                yield event.plain_result("📭 暂无定时任务")
                return
            
            total = len(crons)
            start = (page - 1) * page_size
            end = start + page_size
            page_crons = crons[start:end]
            
            if not page_crons:
                yield event.plain_result(f"❌ 页码超出范围 (共 {(total + page_size - 1) // page_size} 页)")
                return
            
            result = f"📋 定时任务列表 (第 {page} 页，共 {total} 个):\n\n"
            for cron in page_crons:
                status = "🟢" if cron.get('status') == 0 else "🔴"
                result += f"{status} {cron.get('name', '未命名')}\n"
                result += f"  ID: {cron.get('id')}\n"
                cmd = cron.get('command', '')
                result += f"  命令: {cmd[:50]}{'...' if len(cmd) > 50 else ''}\n"
                result += f"  定时: {cron.get('schedule', '无')}\n\n"
            
            total_pages = (total + page_size - 1) // page_size
            if page < total_pages:
                result += f"💡 使用 /ql ls {page + 1} 查看下一页"
            
            yield event.plain_result(result)
        
        # 执行定时任务
        elif command == "run":
            if len(parts) < 3:
                yield event.plain_result("使用方法: /ql run <任务ID>")
                return
            
            try:
                cron_id = int(parts[2])
            except ValueError:
                yield event.plain_result("❌ 任务ID必须是数字")
                return
            
            if await self.ql_api.run_cron([cron_id]):
                yield event.plain_result(f"✅ 已启动任务: {cron_id}\n💡 使用 /ql log {cron_id} 查看日志")
            else:
                yield event.plain_result(f"❌ 执行任务失败: {cron_id}")
        
        # 查看任务日志
        elif command == "log":
            if len(parts) < 3:
                yield event.plain_result("使用方法: /ql log <任务ID>")
                return
            
            try:
                cron_id = int(parts[2])
            except ValueError:
                yield event.plain_result("❌ 任务ID必须是数字")
                return
            
            log_content = await self.ql_api.get_cron_log(cron_id)
            
            if log_content is None:
                yield event.plain_result(f"❌ 获取任务日志失败: {cron_id}")
                return
            
            if not log_content:
                yield event.plain_result(f"📝 任务 {cron_id} 暂无日志")
                return
            
            if len(log_content) > 1000:
                log_content = "...\n" + log_content[-1000:]
            
            yield event.plain_result(f"📝 任务 {cron_id} 日志:\n\n{log_content}")
        
        # 停止任务
        elif command == "stop":
            if len(parts) < 3:
                yield event.plain_result("使用方法: /ql stop <任务ID>")
                return
            
            try:
                cron_id = int(parts[2])
            except ValueError:
                yield event.plain_result("❌ 任务ID必须是数字")
                return
            
            if await self.ql_api.stop_cron([cron_id]):
                yield event.plain_result(f"✅ 已停止任务: {cron_id}")
            else:
                yield event.plain_result(f"❌ 停止任务失败: {cron_id}")
        
        # 定时任务管理
        elif command == "cron":
            if len(parts) < 4:
                yield event.plain_result("使用方法:\n/ql cron enable/disable <任务ID>\n/ql cron pin/unpin <任务ID>\n/ql cron delete <任务ID>")
                return
            
            action = parts[2].lower()
            try:
                cron_id = int(parts[3])
            except ValueError:
                yield event.plain_result("❌ 任务ID必须是数字")
                return
            
            if action == "enable":
                if await self.ql_api.enable_cron([cron_id]):
                    yield event.plain_result(f"✅ 已启用任务: {cron_id}")
                else:
                    yield event.plain_result(f"❌ 启用任务失败: {cron_id}")
            
            elif action == "disable":
                if await self.ql_api.disable_cron([cron_id]):
                    yield event.plain_result(f"✅ 已禁用任务: {cron_id}")
                else:
                    yield event.plain_result(f"❌ 禁用任务失败: {cron_id}")
            
            elif action == "pin":
                if await self.ql_api.pin_cron([cron_id]):
                    yield event.plain_result(f"📌 已置顶任务: {cron_id}")
                else:
                    yield event.plain_result(f"❌ 置顶任务失败: {cron_id}")
            
            elif action == "unpin":
                if await self.ql_api.unpin_cron([cron_id]):
                    yield event.plain_result(f"📌 已取消置顶: {cron_id}")
                else:
                    yield event.plain_result(f"❌ 取消置顶失败: {cron_id}")
            
            elif action == "delete":
                if await self.ql_api.delete_cron([cron_id]):
                    yield event.plain_result(f"✅ 已删除任务: {cron_id}")
                else:
                    yield event.plain_result(f"❌ 删除任务失败: {cron_id}")
            
            else:
                yield event.plain_result(f"❌ 未知操作: {action}\n支持: enable, disable, pin, unpin, delete")
        
        # 系统信息
        elif command == "info":
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
        
        else:
            yield event.plain_result(f"❌ 未知命令: {command}\n使用 /ql 查看帮助")
    
    async def terminate(self):
        """插件卸载时调用"""
        logger.info("青龙面板插件已卸载")
