# AstrBot 青龙面板管理插件

通过 AstrBot 管理青龙面板的环境变量和定时任务。

## 功能

- ✅ 环境变量管理（查看、添加、更新、删除、启用、禁用）
- ✅ 定时任务管理（查看、执行、停止、启用、禁用、置顶、删除、日志）
- ✅ 系统信息查询
- ✅ 分页显示，支持搜索
- ✅ 异步请求，性能更好

## 安装

### 方式一：通过 GitHub 安装（推荐）
在 AstrBot 管理面板的插件市场中搜索 `qinglong` 或输入仓库地址安装。

### 方式二：手动安装
1. 下载本仓库
2. 将文件夹放入 `AstrBot/data/plugins/` 目录
3. 重启 AstrBot

## 配置

在青龙面板创建应用：
1. 进入 `系统设置` → `应用设置`
2. 创建应用，获取 `Client ID` 和 `Client Secret`
3. 在 AstrBot 插件配置中填入：
   - 青龙面板地址（如 `http://192.168.1.100:5700`）
   - Client ID
   - Client Secret

## 命令

### 环境变量
```
/ql envs                          # 查看所有环境变量
/ql envs 2                        # 查看第2页
/ql envs COOKIE                   # 搜索包含COOKIE的变量
/ql add <名称> <值> [备注]         # 添加
/ql update <名称> <值> [备注]      # 按名称更新
/ql update id:<ID> <值> [备注]     # 按ID精确更新
/ql delete <名称>                  # 删除
/ql enable <名称>                  # 启用
/ql disable <名称>                 # 禁用
```

### 定时任务
```
/ql ls                      # 查看任务列表
/ql ls 2                    # 查看第2页
/ql run <任务ID>             # 执行任务
/ql stop <任务ID>            # 停止任务
/ql log <任务ID>             # 查看日志
/ql cron enable <任务ID>     # 启用任务
/ql cron disable <任务ID>    # 禁用任务
/ql cron pin <任务ID>        # 置顶任务
/ql cron unpin <任务ID>      # 取消置顶
/ql cron delete <任务ID>     # 删除任务
```

### 系统信息
```
/ql info         # 查看系统信息
```

## 开发说明

- 使用 `httpx` 异步 HTTP 客户端（符合 AstrBot 开发规范）
- 遵循 AstrBot 插件开发指南

## 许可

MIT License
