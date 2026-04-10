#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""青龙插件命令处理与权限逻辑。"""

from typing import Any, Optional

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from qinglong_formatters import (
    build_cron_list_message,
    build_cron_log_message,
    build_env_list_message,
    build_env_selection_message,
    build_help_text,
    build_system_info_message,
    build_whitelist_list_message,
    build_whoami_message,
)


def normalize_user_id(user_id: object) -> str:
    """统一用户 ID 格式，避免字符串/整数混用导致权限判断失效。"""
    return str(user_id).strip()


def normalize_user_ids(user_ids: object) -> list[str]:
    """归一化白名单并去重，同时保持原有顺序。"""
    normalized_users: list[str] = []
    seen: set[str] = set()

    for user_id in user_ids or []:
        normalized_user_id = normalize_user_id(user_id)
        if normalized_user_id and normalized_user_id not in seen:
            seen.add(normalized_user_id)
            normalized_users.append(normalized_user_id)

    return normalized_users


def try_parse_id_reference(value: str) -> tuple[bool, Optional[int]]:
    """解析 id:123 形式的环境变量引用。"""
    if not value.lower().startswith("id:"):
        return False, None

    try:
        return True, int(value[3:])
    except ValueError:
        return True, None


class QinglongCommandHandlers:
    """命令处理与权限逻辑。"""

    def __init__(self, plugin: Any):
        self.plugin = plugin

    def _get_user_id(self, event: AstrMessageEvent) -> str:
        return normalize_user_id(event.get_sender_id())

    def _is_whitelisted(self, user_id: str) -> bool:
        return user_id in self.plugin._whitelist_lookup

    def _refresh_whitelist_cache(self):
        self.plugin.whitelist_users = normalize_user_ids(self.plugin.whitelist_users)
        self.plugin._whitelist_lookup = set(self.plugin.whitelist_users)

    def _save_whitelist(self):
        try:
            self._refresh_whitelist_cache()
            self.plugin.config["whitelist_users"] = list(self.plugin.whitelist_users)
            self.plugin.context.update_config(self.plugin.config)
            logger.info(f"青龙插件白名单已更新，当前用户数: {len(self.plugin.whitelist_users)}")
        except Exception as error:
            logger.error(f"保存青龙插件白名单失败: {error}")

    def _check_permission(self, event: AstrMessageEvent) -> tuple[bool, str]:
        if not self.plugin.enable_whitelist:
            return True, ""

        user_id = self._get_user_id(event)
        if self._is_whitelisted(user_id):
            return True, ""

        return False, f"❌ 权限不足\n\n您的ID: {user_id}\n此命令仅限授权用户使用"

    async def _find_env_by_id(self, env_id: int) -> Optional[dict]:
        all_envs = await self.plugin.ql_api.get_envs("")
        return next((env for env in all_envs if env.get("id") == env_id), None)

    async def _resolve_single_env(self, env_ref: str, usage_hint: str) -> tuple[Optional[dict], Optional[str]]:
        is_id_ref, env_id = try_parse_id_reference(env_ref)
        if is_id_ref:
            if env_id is None:
                return None, f"❌ 无效的ID格式: {env_ref}"

            target_env = await self._find_env_by_id(env_id)
            if not target_env:
                return None, f"❌ 未找到ID为 {env_id} 的环境变量"
            return target_env, None

        envs = await self.plugin.ql_api.get_envs(env_ref)
        if not envs:
            return None, f"❌ 未找到环境变量: {env_ref}"

        exact_envs = [env for env in envs if env.get("name") == env_ref]
        if len(exact_envs) == 1:
            return exact_envs[0], None

        if len(exact_envs) > 1:
            return None, build_env_selection_message(env_ref, exact_envs, usage_hint, exact_match=True)

        return None, build_env_selection_message(env_ref, envs, usage_hint, exact_match=False)

    async def handle_ql_command(self, event: AstrMessageEvent):
        if not self.plugin.ql_api:
            yield event.plain_result("❌ 插件未正确初始化，请检查配置")
            return

        parts = event.message_str.strip().split()
        command = parts[1].lower() if len(parts) > 1 else "help"

        commands_without_global_permission = {"help", "whoami", "whitelist"}
        commands_without_api_credentials = {"help", "whoami", "whitelist"}

        if command not in commands_without_global_permission:
            has_permission, error_msg = self._check_permission(event)
            if not has_permission:
                yield event.plain_result(error_msg)
                return

        if command not in commands_without_api_credentials and not self.plugin.ql_api.is_configured():
            yield event.plain_result(
                "❌ 插件未配置青龙凭据，请在插件设置中填写面板地址、Client ID 和 Client Secret"
            )
            return

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
            "whoami": self._handle_whoami,
            "whitelist": self._handle_whitelist,
        }

        handler = handlers.get(command)
        if not handler:
            yield event.plain_result(f"❌ 未知命令: {command}\n使用 /ql 查看帮助")
            return

        async for result in handler(event, parts):
            yield result

    async def _handle_help(self, event: AstrMessageEvent, parts: list[str]):
        user_id = self._get_user_id(event)
        is_authorized = self._is_whitelisted(user_id) if self.plugin.enable_whitelist else None
        yield event.plain_result(
            build_help_text(self.plugin.VERSION, self.plugin.enable_whitelist, user_id, is_authorized)
        )

    async def _handle_envs(self, event: AstrMessageEvent, parts: list[str]):
        search_value = ""
        page = 1

        if len(parts) > 2:
            if parts[2].isdigit():
                page = int(parts[2])
            else:
                search_value = parts[2]
                if len(parts) > 3 and parts[3].isdigit():
                    page = int(parts[3])

        envs = await self.plugin.ql_api.get_envs(search_value)
        if not envs:
            message = f"❌ 未找到包含 '{search_value}' 的环境变量" if search_value else "📭 暂无环境变量"
            yield event.plain_result(message)
            return

        total = len(envs)
        start = (page - 1) * self.plugin.PAGE_SIZE
        page_envs = envs[start : start + self.plugin.PAGE_SIZE]
        if not page_envs:
            total_pages = max((total + self.plugin.PAGE_SIZE - 1) // self.plugin.PAGE_SIZE, 1)
            yield event.plain_result(f"❌ 页码超出范围 (共 {total_pages} 页)")
            return

        yield event.plain_result(
            build_env_list_message(page_envs, page, total, self.plugin.PAGE_SIZE, search_value)
        )

    async def _handle_add_env(self, event: AstrMessageEvent, parts: list[str]):
        if len(parts) < 4:
            yield event.plain_result("使用方法: /ql add <变量名> <变量值> [备注]")
            return

        name = parts[2]
        value = parts[3]
        remarks = " ".join(parts[4:]) if len(parts) > 4 else ""
        success, message = await self.plugin.ql_api.add_env(name, value, remarks)
        yield event.plain_result(f"{'✅' if success else '❌'} {message}: {name}")

    async def _handle_update_env(self, event: AstrMessageEvent, parts: list[str]):
        if len(parts) < 4:
            yield event.plain_result("使用方法:\n/ql update <变量名> <新值>\n/ql update id:<ID> <新值>")
            return

        env_ref = parts[2]
        value = " ".join(parts[3:])

        env, error_msg = await self._resolve_single_env(env_ref, "/ql update id:<ID> <新值>")
        if not env:
            yield event.plain_result(error_msg)
            return

        success, message = await self.plugin.ql_api.update_env(
            env["id"],
            env.get("name", env_ref),
            value,
            env.get("remarks", ""),
        )
        yield event.plain_result(f"{'✅' if success else '❌'} {message}: {env.get('name', env_ref)}")

    async def _handle_delete_env(self, event: AstrMessageEvent, parts: list[str]):
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql delete <变量名>|id:<ID>")
            return

        env_ref = parts[2]
        env, error_msg = await self._resolve_single_env(env_ref, "/ql delete id:<ID>")
        if not env:
            yield event.plain_result(error_msg)
            return

        success, message = await self.plugin.ql_api.delete_env(env["id"])
        yield event.plain_result(f"{'✅' if success else '❌'} {message}: {env.get('name', env_ref)}")

    async def _handle_enable_env(self, event: AstrMessageEvent, parts: list[str]):
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql enable <变量名>|id:<ID>")
            return

        env_ref = parts[2]
        env, error_msg = await self._resolve_single_env(env_ref, "/ql enable id:<ID>")
        if not env:
            yield event.plain_result(error_msg)
            return

        success, message = await self.plugin.ql_api.enable_env([env["id"]])
        yield event.plain_result(f"{'✅' if success else '❌'} {message}: {env.get('name', env_ref)}")

    async def _handle_disable_env(self, event: AstrMessageEvent, parts: list[str]):
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql disable <变量名>|id:<ID>")
            return

        env_ref = parts[2]
        env, error_msg = await self._resolve_single_env(env_ref, "/ql disable id:<ID>")
        if not env:
            yield event.plain_result(error_msg)
            return

        success, message = await self.plugin.ql_api.disable_env([env["id"]])
        yield event.plain_result(f"{'✅' if success else '❌'} {message}: {env.get('name', env_ref)}")

    async def _handle_crons(self, event: AstrMessageEvent, parts: list[str]):
        page = 1
        if len(parts) > 2 and parts[2].isdigit():
            page = int(parts[2])

        crons = await self.plugin.ql_api.get_crons()
        if not crons:
            yield event.plain_result("📭 暂无定时任务")
            return

        total = len(crons)
        start = (page - 1) * self.plugin.PAGE_SIZE
        page_crons = crons[start : start + self.plugin.PAGE_SIZE]
        if not page_crons:
            total_pages = max((total + self.plugin.PAGE_SIZE - 1) // self.plugin.PAGE_SIZE, 1)
            yield event.plain_result(f"❌ 页码超出范围 (共 {total_pages} 页)")
            return

        yield event.plain_result(build_cron_list_message(page_crons, page, total, self.plugin.PAGE_SIZE))

    async def _handle_run_cron(self, event: AstrMessageEvent, parts: list[str]):
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql run <任务ID>")
            return

        try:
            cron_id = int(parts[2])
        except ValueError:
            yield event.plain_result("❌ 任务ID必须是数字")
            return

        success, message = await self.plugin.ql_api.run_cron([cron_id])
        if success:
            yield event.plain_result(f"✅ 已启动任务: {cron_id}\n💡 使用 /ql log {cron_id} 查看日志")
            return

        yield event.plain_result(f"❌ 执行失败: {message}")

    async def _handle_stop_cron(self, event: AstrMessageEvent, parts: list[str]):
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql stop <任务ID>")
            return

        try:
            cron_id = int(parts[2])
        except ValueError:
            yield event.plain_result("❌ 任务ID必须是数字")
            return

        success, message = await self.plugin.ql_api.stop_cron([cron_id])
        if success:
            yield event.plain_result(f"✅ 已停止任务: {cron_id}")
            return

        yield event.plain_result(f"❌ 停止失败: {message}")

    async def _handle_cron_log(self, event: AstrMessageEvent, parts: list[str]):
        if len(parts) < 3:
            yield event.plain_result("使用方法: /ql log <任务ID>")
            return

        try:
            cron_id = int(parts[2])
        except ValueError:
            yield event.plain_result("❌ 任务ID必须是数字")
            return

        success, log_content = await self.plugin.ql_api.get_cron_log(cron_id)
        if not success:
            yield event.plain_result(f"❌ 获取日志失败: {log_content}")
            return

        if not log_content:
            yield event.plain_result(f"📝 任务 {cron_id} 暂无日志")
            return

        yield event.plain_result(build_cron_log_message(cron_id, log_content))

    async def _handle_cron_action(self, event: AstrMessageEvent, parts: list[str]):
        if len(parts) < 4:
            yield event.plain_result(
                "使用方法:\n"
                "/ql cron enable/disable <任务ID>\n"
                "/ql cron pin/unpin <任务ID>\n"
                "/ql cron delete <任务ID>"
            )
            return

        action = parts[2].lower()
        try:
            cron_id = int(parts[3])
        except ValueError:
            yield event.plain_result("❌ 任务ID必须是数字")
            return

        actions = {
            "enable": (self.plugin.ql_api.enable_cron, "启用"),
            "disable": (self.plugin.ql_api.disable_cron, "禁用"),
            "pin": (self.plugin.ql_api.pin_cron, "置顶"),
            "unpin": (self.plugin.ql_api.unpin_cron, "取消置顶"),
            "delete": (self.plugin.ql_api.delete_cron, "删除"),
        }
        if action not in actions:
            yield event.plain_result(f"❌ 未知操作: {action}\n支持: enable, disable, pin, unpin, delete")
            return

        func, action_name = actions[action]
        success, message = await func([cron_id])
        icon = "📌" if success and action in ("pin", "unpin") else ("✅" if success else "❌")
        yield event.plain_result(f"{icon} {action_name}任务 {cron_id}: {message}")

    async def _handle_info(self, event: AstrMessageEvent, parts: list[str]):
        system_info = await self.plugin.ql_api.get_system_info()
        if not system_info:
            yield event.plain_result("❌ 获取系统信息失败")
            return

        yield event.plain_result(build_system_info_message(system_info))

    async def _handle_whoami(self, event: AstrMessageEvent, parts: list[str]):
        user_id = self._get_user_id(event)
        yield event.plain_result(
            build_whoami_message(
                user_id=user_id,
                enable_whitelist=self.plugin.enable_whitelist,
                is_whitelisted=self._is_whitelisted(user_id),
                whitelist_count=len(self.plugin.whitelist_users),
            )
        )

    async def _handle_whitelist(self, event: AstrMessageEvent, parts: list[str]):
        if len(parts) < 3:
            yield event.plain_result(
                "❌ 请指定子命令\n\n"
                "用法:\n"
                "/ql whitelist list - 查看白名单\n"
                "/ql whitelist add <用户ID> - 添加用户\n"
                "/ql whitelist remove <用户ID> - 移除用户"
            )
            return

        sub_cmd = parts[2].lower()

        if sub_cmd == "list":
            if not self.plugin.enable_whitelist:
                yield event.plain_result("ℹ️ 白名单功能未启用\n\n所有用户都可以使用此插件")
                return

            yield event.plain_result(build_whitelist_list_message(self.plugin.whitelist_users))
            return

        if sub_cmd not in {"add", "remove"}:
            yield event.plain_result(f"❌ 未知子命令: {sub_cmd}\n\n可用命令: list, add, remove")
            return

        operator_id = self._get_user_id(event)
        if self.plugin.enable_whitelist and self.plugin.whitelist_users and not self._is_whitelisted(operator_id):
            yield event.plain_result(
                f"❌ 权限不足\n\n只有白名单用户才能管理白名单\n您的ID: {operator_id}"
            )
            return

        if len(parts) < 4:
            yield event.plain_result(f"❌ 请指定用户ID\n\n用法: /ql whitelist {sub_cmd} <用户ID>")
            return

        target_user_id = normalize_user_id(parts[3])
        if not target_user_id:
            yield event.plain_result(f"❌ 用户ID不能为空\n\n用法: /ql whitelist {sub_cmd} <用户ID>")
            return

        if sub_cmd == "add":
            if self._is_whitelisted(target_user_id):
                yield event.plain_result(f"ℹ️ 用户 {target_user_id} 已在白名单中")
                return

            self.plugin.whitelist_users.append(target_user_id)
            self._save_whitelist()
            extra_hint = ""
            if self.plugin.enable_whitelist and len(self.plugin.whitelist_users) == 1:
                extra_hint = "\n\n💡 首个白名单用户已建立，后续仅白名单用户可管理权限"
            yield event.plain_result(
                f"✅ 已将用户 {target_user_id} 添加到白名单\n\n当前白名单用户数: {len(self.plugin.whitelist_users)}个"
                f"{extra_hint}"
            )
            return

        if not self._is_whitelisted(target_user_id):
            yield event.plain_result(f"ℹ️ 用户 {target_user_id} 不在白名单中")
            return

        if target_user_id == operator_id and len(self.plugin.whitelist_users) == 1:
            yield event.plain_result("❌ 不能移除最后一个白名单用户")
            return

        if target_user_id == operator_id:
            yield event.plain_result("❌ 不能移除自己")
            return

        self.plugin.whitelist_users.remove(target_user_id)
        self._save_whitelist()
        yield event.plain_result(
            f"✅ 已将用户 {target_user_id} 从白名单移除\n\n当前白名单用户数: {len(self.plugin.whitelist_users)}个"
        )
