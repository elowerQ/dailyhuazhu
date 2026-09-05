# 华住会自动签到 🏨

每日自动签到华住会，支持 **GitHub Actions** 和 **青龙面板** 运行。

## ✨ 功能特性

- ✅ 每日自动签到，获取积分
- ✅ 多账号支持
- ✅ 签到前检测，避免重复签到
- ✅ 启动随机延迟 (默认随机等 1~30 分钟，防风控)
- ✅ 被限制 (HTTP 429) 时自动延迟重试
- ✅ 多种推送通知 (Server酱 / Telegram / Bark / PushPlus)
- ✅ 支持 GitHub Actions 定时运行
- ✅ 支持 青龙面板 运行

---

## 📱 获取 Cookie

### 方法：微信小程序抓包

1. 安装抓包工具 (推荐 [Charles](https://www.charlesproxy.com/) 或 [Fiddler](https://www.telerik.com/fiddler))
2. 配置手机代理，安装HTTPS证书
3. 打开微信 → 搜索「**华住会**」小程序
4. 进入 **会员** → **签到** 页面，点击签到
5. 在抓包工具中找到 `hweb-minilogin.huazhu.com` 相关请求
6. 复制请求头中的 **Cookie** 字段值

> ⚠️ Cookie 有时效性，失效后需要重新获取

---

## 🚀 部署方式

### 方式一：GitHub Actions (推荐)

1. **Fork 本仓库**

2. **设置 Secrets**
   
   进入仓库 → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

| Secret 名称 | 说明 | 必填 |
|---|---|---|
| `HUAZHU_COOKIE` | 华住会Cookie，多账号用 `&` 分隔 | ✅ |
| `HUAZHU_RANDOM_DELAY` | 启动随机延迟最大分钟数，默认 30；设 0 关闭 | ❌ |
| `HUAZHU_RETRY_COUNT` | 被限制 (429) 时自动重试次数，默认 2；设 0 关闭 | ❌ |
| `HUAZHU_RETRY_DELAY_MIN` | 每次重试间隔分钟数，默认 15 | ❌ |
| `PUSH_KEY` | Server酱推送Key | ❌ |
| `TG_BOT_TOKEN` | Telegram Bot Token | ❌ |
| `TG_CHAT_ID` | Telegram Chat ID | ❌ |
| `BARK_KEY` | Bark推送Key | ❌ |
| `PUSHPLUS_TOKEN` | PushPlus推送Token | ❌ |

3. **启用 Actions**
   
   进入仓库 → `Actions` → 点击 `I understand my workflows, go ahead and enable them`

4. **手动测试**
   
   进入 `Actions` → `华住会自动签到` → `Run workflow` → 点击运行

> 📅 默认每天北京时间 **08:05** 自动执行

---

### 方式二：青龙面板

1. **添加脚本**

   在青龙面板中，选择「脚本管理」，上传 `huazhu_checkin.py` 文件。

   或者通过「订阅管理」拉取仓库：
   ```
   名称: 华住会签到
   类型: 公开仓库
   链接: <你的仓库地址>
   定时类型: crontab
   定时规则: 0 8 * * *
   文件后缀: py
   ```

2. **配置环境变量**

   进入「环境变量」，添加：

   | 名称 | 值 | 必填 |
   |---|---|---|
   | `HUAZHU_COOKIE` | 你的华住会Cookie | ✅ |
   | `HUAZHU_RANDOM_DELAY` | 随机延迟最大分钟数，默认 30 | ❌ |
   | `HUAZHU_RETRY_COUNT` | 被限制时重试次数，默认 2 | ❌ |
   | `HUAZHU_RETRY_DELAY_MIN` | 每次重试间隔分钟数，默认 15 | ❌ |
   | `PUSH_KEY` | Server酱Key | ❌ |

   > 多账号在同一个变量中用 `&` 或换行分隔

3. **创建定时任务**

   进入「定时任务」，新建任务：
   ```
   名称: 华住会签到
   命令: task huazhu_checkin.py
   定时规则: 5 8 * * *
   ```

   > ⏱️ **注意超时设置**：开启随机延迟 + 重试后，最坏情况耗时约 65 分钟（随机延迟 30 分钟 + 重试 2×15 分钟）。请将青龙任务的「超时」设置为 **70 分钟以上**，否则任务会被中途杀掉。也可通过环境变量调小延迟/重试参数。

---

### 方式三：本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
# Windows PowerShell
$env:HUAZHU_COOKIE="你的Cookie"

# Linux/Mac
export HUAZHU_COOKIE="你的Cookie"

# 运行
python huazhu_checkin.py
```

---

## 📋 多账号配置

多个账号的 Cookie 用 `&` 或换行符分隔：

```
cookie1内容&cookie2内容&cookie3内容
```

---

## 🔔 推送通知配置

| 渠道 | 环境变量 | 获取方式 |
|---|---|---|
| Server酱 | `PUSH_KEY` | [sct.ftqq.com](https://sct.ftqq.com/) |
| Telegram | `TG_BOT_TOKEN` + `TG_CHAT_ID` | [@BotFather](https://t.me/BotFather) |
| Bark | `BARK_KEY` | iOS Bark App |
| PushPlus | `PUSHPLUS_TOKEN` | [pushplus.plus](https://www.pushplus.plus/) |

---

## 📁 项目结构

```
dailyhuazhu/
├── huazhu_checkin.py          # 主签到脚本
├── requirements.txt           # Python依赖
├── README.md                  # 说明文档
├── .gitignore                 # Git忽略文件
└── .github/
    └── workflows/
        └── checkin.yml        # GitHub Actions 工作流
```

---

## ⚠️ 免责声明

- 本项目仅供学习交流使用
- 使用本脚本产生的一切后果由使用者自行承担
- 请勿用于商业用途或恶意用途
- 如有侵权，请联系删除

---

## 📝 更新日志

### v1.1.0 (2026-09-05)
- 🛡️ 新增启动随机延迟：定时任务触发后随机等待 1~30 分钟再签到，避免每天固定时刻签到被风控识别（可通过 `HUAZHU_RANDOM_DELAY` 配置，设 0 关闭）
- 🔁 新增被限制自动重试：签到遇到 HTTP 429 / businessCode 99999（账号被限制）时，自动延迟 15 分钟重试，最多 2 次（可通过 `HUAZHU_RETRY_COUNT`、`HUAZHU_RETRY_DELAY_MIN` 配置）

### v1.0.2 (2026-03-20)
- 🐛 修复签到信息返回"?"的BUG：根据API实际返回字段，修正展示信息为准确的“再签X天得奖励”及积分信息。

### v1.0.1 (2026-03-18)
- 🐛 修复API返回 `businessCode: 1003` (未登录/Token过期) 时被错误判断为签到成功的问题
- ✨ 增加对Token过期的明确提示，方便用户重新抓包

### v1.0.0 (2026-03-17)
- 🎉 初始版本
- ✅ 支持每日自动签到
- ✅ 支持多账号
- ✅ 支持 GitHub Actions + 青龙面板
- ✅ 支持多种推送通知
