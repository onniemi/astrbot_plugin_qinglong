#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""青龙插件文本格式化工具。"""

from typing import Any, Optional


SENSITIVE_ENV_KEYWORDS = (
    "cookie",
    "token",
    "secret",
    "password",
    "key",
    "wskey",
    "auth",
    "bearer",
)


def summarize_env_value(name: str, value: Any, max_length: int = 50) -> str:
    """展示环境变量值时做脱敏，避免在聊天中泄露敏感信息。"""
    text = str(value or "")
    if not text:
        return ""

    lowered_name = name.lower()
    if any(keyword in lowered_name for keyword in SENSITIVE_ENV_KEYWORDS):
        if len(text) <= 8:
            return "*" * len(text)
        visible_chars = 4 if len(text) > 12 else 2
        return f"{text[:visible_chars]}***{text[-visible_chars:]}"

    return truncate_text(text, max_length)


def truncate_text(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}..."


def build_help_text(
    version: str,
    enable_whitelist: bool,
    user_id: Optional[str] = None,
    is_authorized: Optional[bool] = None,
) -> str:
    help_text = f"""📦 青龙面板管理插件 v{version}

📋 环境变量:
/ql envs [关键词] [页码] - 查看环境变量
/ql add <名称> <值> [备注] - 添加
/ql update <名称>|id:<ID> <新值> - 更新
/ql delete <名称>|id:<ID> - 删除
/ql enable <名称>|id:<ID> - 启用
/ql disable <名称>|id:<ID> - 禁用

⏰ 定时任务:
/ql ls [页码] - 查看任务列表
/ql run <任务ID> - 执行任务
/ql stop <任务ID> - 停止任务
/ql log <任务ID> - 查看日志
/ql cron enable/disable <任务ID> - 启用/禁用
/ql cron pin/unpin <任务ID> - 置顶/取消置顶
/ql cron delete <任务ID> - 删除任务

📊 系统信息:
/ql info - 查看系统信息

👤 权限管理:
/ql whoami - 查看当前用户ID
/ql whitelist list - 查看白名单
/ql whitelist add <用户ID> - 添加白名单
/ql whitelist remove <用户ID> - 移除白名单"""

    if enable_whitelist and user_id:
        if is_authorized:
            help_text += "\n\n✅ 您已获得授权"
        else:
            help_text += f"\n\n⚠️ 您的ID: {user_id}\n请联系管理员将您添加到白名单"

    return help_text


def build_env_selection_message(env_ref: str, envs: list[dict], usage_hint: str, exact_match: bool) -> str:
    if exact_match:
        title = f"⚠️ 找到 {len(envs)} 个名称为 '{env_ref}' 的环境变量："
    else:
        title = f"⚠️ 未找到名称完全等于 '{env_ref}' 的环境变量，但找到了以下相近项："

    lines = [title, ""]
    for env in envs[:10]:
        remarks = env.get("remarks") or "无备注"
        lines.append(f"ID: {env.get('id')} - {env.get('name')} - {remarks}")

    lines.append("")
    lines.append(f"💡 使用 {usage_hint} 精确操作")
    return "\n".join(lines)


def build_env_list_message(
    page_envs: list[dict],
    page: int,
    total: int,
    page_size: int,
    search_value: str = "",
) -> str:
    search_info = f" (搜索: {search_value})" if search_value else ""
    result = f"📋 环境变量列表{search_info} (第 {page} 页，共 {total} 个):\n\n"

    for env in page_envs:
        status = "🟢" if env.get("status") == 0 else "🔴"
        result += f"{status} {env.get('name')}\n"
        result += f"  ID: {env.get('id')}\n"
        result += f"  值: {summarize_env_value(env.get('name', ''), env.get('value', ''))}\n"
        if env.get("remarks"):
            result += f"  备注: {env.get('remarks')}\n"
        result += "\n"

    total_pages = max((total + page_size - 1) // page_size, 1)
    if page < total_pages:
        next_cmd = f"/ql envs {search_value} {page + 1}" if search_value else f"/ql envs {page + 1}"
        result += f"💡 使用 {next_cmd} 查看下一页"

    return result


def build_cron_list_message(page_crons: list[dict], page: int, total: int, page_size: int) -> str:
    result = f"📋 定时任务列表 (第 {page} 页，共 {total} 个):\n\n"
    for cron in page_crons:
        status = "🟢" if cron.get("status") == 0 else "🔴"
        command = truncate_text(str(cron.get("command", "")), 50)
        result += f"{status} {cron.get('name', '未命名')}\n"
        result += f"  ID: {cron.get('id')}\n"
        result += f"  命令: {command}\n"
        result += f"  定时: {cron.get('schedule', '无')}\n\n"

    total_pages = max((total + page_size - 1) // page_size, 1)
    if page < total_pages:
        result += f"💡 使用 /ql ls {page + 1} 查看下一页"

    return result


def build_cron_log_message(cron_id: int, log_content: str, max_length: int = 1000) -> str:
    if len(log_content) > max_length:
        log_content = "...\n" + log_content[-max_length:]
    return f"📝 任务 {cron_id} 日志:\n\n{log_content}"


def build_system_info_message(system_info: dict) -> str:
    result = "📊 青龙面板系统信息:\n\n"

    if "version" in system_info:
        result += f"🖥️ 版本: {system_info['version']}"
        if "branch" in system_info:
            result += f" ({system_info['branch']})"
        result += "\n"

    if "isInitialized" in system_info:
        status = "✅ 已初始化" if system_info["isInitialized"] else "⚠️ 未初始化"
        result += f"📌 状态: {status}\n"

    if "platform" in system_info:
        result += f"💻 平台: {system_info['platform']}\n"

    return result.rstrip()


def build_whoami_message(
    user_id: str,
    enable_whitelist: bool,
    is_whitelisted: bool,
    whitelist_count: int,
) -> str:
    result = "👤 用户信息\n\n"
    result += f"用户ID: {user_id}\n"

    if enable_whitelist:
        if is_whitelisted:
            result += "权限状态: ✅ 已授权\n"
            result += f"白名单用户数: {whitelist_count}个"
        else:
            result += "权限状态: ❌ 未授权\n"
            result += "💡 如需使用此插件，请联系管理员将您的ID添加到白名单"
    else:
        result += "权限状态: ✅ 所有用户可用\n"
        result += "（管理员未启用白名单）"

    return result


def build_whitelist_list_message(whitelist_users: list[str]) -> str:
    if not whitelist_users:
        return "📋 白名单列表\n\n当前白名单为空"

    result = f"📋 白名单列表 (共 {len(whitelist_users)} 个用户)\n\n"
    for index, user_id in enumerate(whitelist_users, 1):
        result += f"{index}. {user_id}\n"
    return result.rstrip()
