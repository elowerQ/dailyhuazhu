# 华住会自动签到 🏨

每日自动签到华住会，支持 **GitHub Actions** 和 **青龙面板** 运行。

## ✨ 功能特性

- ✅ 每日自动签到，获取积分
- ✅ 多账号支持
- ✅ 签到前检测，避免重复签到
- ✅ 随机延迟，模拟人工操作
- ✅ 失败自动重试 (最多3次)
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

   | 名称 | 值 |
   |---|---|
   | `HUAZHU_COOKIE` | 你的华住会Cookie |
   | `PUSH_KEY` | Server酱Key (可选) |

   > 多账号在同一个变量中用 `&` 或换行分隔

3. **创建定时任务**

   进入「定时任务」，新建任务：
   ```
   名称: 华住会签到
   命令: task huazhu_checkin.py
   定时规则: 5 8 * * *
   ```

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
hzh/
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

### v1.0.0 (2026-03-17)
- 🎉 初始版本
- ✅ 支持每日自动签到
- ✅ 支持多账号
- ✅ 支持 GitHub Actions + 青龙面板
- ✅ 支持多种推送通知
