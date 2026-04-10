#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AstrBot 青龙面板管理插件

功能：
1. 环境变量管理（查看、添加、更新、删除、启用、禁用）
2. 定时任务管理（查看、执行、停止、启用、禁用、置顶、删除、日志）
3. 系统信息查询
4. 可选白名单权限控制

版本: 1.1.0
"""

import sys
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))


from qinglong_command_handlers import QinglongCommandHandlers, normalize_user_ids
from qinglong_api import QinglongAPI


@register("astrbot_plugin_qinglong", "Haitun", "青龙面板管理插件", "1.1.0")
class QinglongPlugin(Star):
    """AstrBot 青龙插件主类。"""

    VERSION = "1.1.0"
    PAGE_SIZE = 10

    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.context = context
        self.config = config

        ql_host = config.get("qinglong_host", "http://localhost:5700")
        ql_client_id = config.get("qinglong_client_id", "")
        ql_client_secret = config.get("qinglong_client_secret", "")

        self.enable_whitelist = config.get("enable_whitelist", False)
        self.whitelist_users = normalize_user_ids(config.get("whitelist_users", []))
        self._whitelist_lookup = set(self.whitelist_users)
        self.config["whitelist_users"] = list(self.whitelist_users)

        self.ql_api = QinglongAPI(ql_host, ql_client_id, ql_client_secret)
        self.command_handlers = QinglongCommandHandlers(self)

        logger.info("青龙面板插件已加载")
        logger.info(f"  Host: {ql_host}")
        if self.enable_whitelist:
            logger.info(f"  权限管理: 已启用 (白名单用户 {len(self.whitelist_users)} 个)")
        else:
            logger.info("  权限管理: 未启用 (所有用户可用)")

    @filter.command("ql")
    async def ql_command(self, event: AstrMessageEvent):
        """青龙面板管理命令入口。"""
        async for result in self.command_handlers.handle_ql_command(event):
            yield result

    async def terminate(self):
        await self.ql_api.close()
        logger.info("青龙面板插件已卸载")
