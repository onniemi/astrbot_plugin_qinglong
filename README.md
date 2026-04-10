# AstrBot 青龙面板管理插件

通过 AstrBot 管理青龙面板的环境变量、定时任务与基础系统信息。

## 功能

- ✅ 环境变量管理：查看、添加、更新、删除、启用、禁用
- ✅ 定时任务管理：查看、执行、停止、启用、禁用、置顶、删除、日志
- ✅ 系统信息查询
- ✅ 分页显示，支持关键词搜索
- ✅ 敏感环境变量值自动脱敏预览，降低聊天泄露风险
- ✅ 可选白名单权限管理

## 安装

### 方式一：通过 GitHub 安装

在 AstrBot 管理面板的插件市场中搜索 `qinglong`，或直接填入仓库地址安装。

### 方式二：手动安装

1. 下载本仓库
2. 将文件夹放入 `AstrBot/data/plugins/` 目录
3. 重启 AstrBot

## 配置

先在青龙面板创建应用：

1. 进入 `系统设置` -> `应用设置`
2. 创建应用，获取 `Client ID` 和 `Client Secret`
3. 在 AstrBot 插件配置中填入：
   - `qinglong_host`：青龙面板地址，例如 `http://192.168.1.100:5700`
   - `qinglong_client_id`：青龙应用的 Client ID
   - `qinglong_client_secret`：青龙应用的 Client Secret

可选权限配置：

- `enable_whitelist`：是否启用白名单权限控制
- `whitelist_users`：白名单用户 ID 列表，可先通过 `/ql whoami` 获取自己的 ID

说明：

- 开启白名单后，普通业务命令只允许白名单用户执行。
- `/ql help`、`/ql whoami`、`/ql whitelist ...` 不依赖青龙凭据，便于排查和授权。
- 当白名单刚启用且列表为空时，可先添加首个白名单用户完成初始化。

## 命令

### 环境变量

```text
/ql envs
/ql envs 2
/ql envs COOKIE
/ql add <名称> <值> [备注]
/ql update <名称>|id:<ID> <新值>
/ql delete <名称>|id:<ID>
/ql enable <名称>|id:<ID>
/ql disable <名称>|id:<ID>
```

说明：

- 更新、删除、启用、禁用时，会优先按“精确名称”匹配，避免误操作模糊搜索结果。
- 如果同名变量有多个，插件会提示使用 `id:<ID>` 精确操作。
- 环境变量列表中的敏感值默认只显示脱敏预览。

### 定时任务

```text
/ql ls
/ql ls 2
/ql run <任务ID>
/ql stop <任务ID>
/ql log <任务ID>
/ql cron enable <任务ID>
/ql cron disable <任务ID>
/ql cron pin <任务ID>
/ql cron unpin <任务ID>
/ql cron delete <任务ID>
```

### 系统信息

```text
/ql info
```

### 权限管理

```text
/ql whoami
/ql whitelist list
/ql whitelist add <用户ID>
/ql whitelist remove <用户ID>
```

## 项目结构

- `main.py`：插件入口与配置装配
- `qinglong_api.py`：青龙 API 封装
- `qinglong_command_handlers.py`：命令路由、权限校验与业务处理
- `qinglong_formatters.py`：文本格式化与消息拼装

## 开发说明

- 使用 `httpx` 异步 HTTP 客户端
- 青龙 token 失效时会自动清理并重试一次
- 支持更稳妥的环境变量精确匹配与 `id:<ID>` 操作

## 许可

MIT License
