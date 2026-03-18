#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华住会自动签到脚本
支持: GitHub Actions / 青龙面板 / 本地运行
Cron: 0 8 * * *  (每天早上8点执行)

环境变量:
  HUAZHU_COOKIE: 华住会Cookie，多账号用 & 或换行分隔
  PUSH_KEY:      Server酱推送Key (可选)
  TG_BOT_TOKEN:  Telegram Bot Token (可选)
  TG_CHAT_ID:    Telegram Chat ID (可选)
  BARK_KEY:      Bark推送Key (可选)
  PUSHPLUS_TOKEN: PushPlus推送Token (可选)

获取Cookie方法:
  1. 使用抓包工具(Charles/Fiddler/Stream)
  2. 打开微信 -> 华住会小程序 -> 会员 -> 签到
  3. 抓取 appgw.huazhu.com 域名请求中的 Cookie
  4. 关键字段: userToken=xxx (必须包含)
"""

import os
import sys
import json
import time
import random
import logging
from datetime import datetime
from urllib.parse import quote

__version__ = "1.0.1"

try:
    import requests
except ImportError:
    print("正在安装 requests 库...")
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("huazhu")

# ============================================================
# 真实API地址 (从抓包分析得到)
# ============================================================
BASE_URL = "https://appgw.huazhu.com"
SIGN_IN_URL = f"{BASE_URL}/game/sign_in"           # GET, 签到
SIGN_HEADER_URL = f"{BASE_URL}/game/sign_header"    # GET, 签到状态/头部信息
SIGN_NOTICE_CLOSE_URL = f"{BASE_URL}/game/sign_notice_close"  # GET, 关闭签到提醒
PLAY_ENTRY_URL = f"{BASE_URL}/game/play_entry"      # GET, 活动入口

# 认证跳转 (用于刷新 userToken)
BRIDGE_URL = "https://hweb-minilogin.huazhu.com/bridge/jump"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
                  "MicroMessenger/8.0.69(0x18004532) NetType/WIFI Language/zh_CN "
                  "miniProgram/wx286efc12868f2559",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://cdn.huazhu.com",
    "Referer": "https://cdn.huazhu.com/",
    "Client-Platform": "WX-MP",
    "Connection": "keep-alive",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}

# 消息收集
notify_messages = []


def log_and_notify(msg):
    """记录日志并收集通知消息"""
    logger.info(msg)
    notify_messages.append(msg)


# ============================================================
# 推送通知
# ============================================================
def send_notify(title, content):
    """发送推送通知"""
    # Server酱推送
    push_key = os.environ.get("PUSH_KEY", "")
    if push_key:
        try:
            url = f"https://sctapi.ftqq.com/{push_key}.send"
            data = {"title": title, "desp": content.replace("\n", "\n\n")}
            resp = requests.post(url, data=data, timeout=10)
            if resp.status_code == 200:
                logger.info("Server酱推送成功")
        except Exception as e:
            logger.warning(f"Server酱推送异常: {e}")

    # Telegram Bot推送
    tg_token = os.environ.get("TG_BOT_TOKEN", "")
    tg_chat_id = os.environ.get("TG_CHAT_ID", "")
    if tg_token and tg_chat_id:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            data = {"chat_id": tg_chat_id, "text": f"{title}\n\n{content}"}
            resp = requests.post(url, json=data, timeout=10)
            if resp.status_code == 200:
                logger.info("Telegram推送成功")
        except Exception as e:
            logger.warning(f"Telegram推送异常: {e}")

    # Bark推送
    bark_key = os.environ.get("BARK_KEY", "")
    if bark_key:
        try:
            url = f"https://api.day.app/{bark_key}/{quote(title)}/{quote(content)}"
            requests.get(url, timeout=10)
        except Exception as e:
            logger.warning(f"Bark推送异常: {e}")

    # PushPlus推送
    pushplus_token = os.environ.get("PUSHPLUS_TOKEN", "")
    if pushplus_token:
        try:
            url = "https://www.pushplus.plus/send"
            data = {"token": pushplus_token, "title": title, "content": content}
            requests.post(url, json=data, timeout=10)
        except Exception as e:
            logger.warning(f"PushPlus推送异常: {e}")


# ============================================================
# 华住会签到类
# ============================================================
class HuazhuCheckin:
    """华住会自动签到"""

    def __init__(self, cookie):
        self.cookie = cookie.strip()
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.session.headers["Cookie"] = self.cookie

    def _request(self, method, url, **kwargs):
        """封装请求，增加重试"""
        kwargs.setdefault("timeout", 30)
        for attempt in range(3):
            try:
                resp = self.session.request(method, url, **kwargs)
                # 不直接 raise_for_status, 让调用者处理
                return resp
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/3): {e}")
                if attempt < 2:
                    time.sleep(random.uniform(2, 5))
                else:
                    raise
        return None

    def get_sign_header(self):
        """获取签到头部信息 (签到状态)"""
        try:
            resp = self._request("GET", SIGN_HEADER_URL)
            data = resp.json()
            biz_code = str(data.get("businessCode", ""))
            response_des = data.get("responseDes", "")

            # businessCode 1003 = 未登录 (token过期)
            if biz_code == "1003" or "未登录" in str(response_des):
                log_and_notify(f"❌ Token已过期! (businessCode={biz_code}, responseDes={response_des})")
                log_and_notify(f"   请重新抓包获取新的Cookie/userToken")
                return {"is_signed": False, "token_expired": True}

            if biz_code == "1000":
                content = data.get("content", {})
                if isinstance(content, dict):
                    sign_days = content.get("signDays", content.get("continueDays", "?"))
                    is_signed = content.get("isTodaySigned", content.get("isSign", False))
                    points = content.get("points", content.get("totalPoints", "?"))
                    log_and_notify(f"📋 签到状态: {'已签到' if is_signed else '未签到'} | 连签: {sign_days}天 | 积分: {points}")
                    return {"is_signed": is_signed, "sign_days": sign_days}
                else:
                    log_and_notify(f"📋 签到头信息: {data}")
                    return {"is_signed": False}
            else:
                log_and_notify(f"⚠️ 获取签到状态失败: businessCode={biz_code}, msg={data.get('message', '')}, des={response_des}")
                log_and_notify(f"   完整响应: {json.dumps(data, ensure_ascii=False)[:300]}")
                return None
        except Exception as e:
            log_and_notify(f"⚠️ 获取签到状态异常: {e}")
            return None

    def do_checkin(self):
        """执行签到 - GET /game/sign_in?date={timestamp}"""
        try:
            timestamp = int(time.time())
            params = {"date": str(timestamp)}

            resp = self._request("GET", SIGN_IN_URL, params=params)
            data = resp.json()

            biz_code = str(data.get("businessCode", ""))
            response_des = data.get("responseDes", "")
            msg = data.get("message", "")
            content = data.get("content", {})

            # businessCode 1003 = 未登录 (token过期)
            if biz_code == "1003" or "未登录" in str(response_des):
                log_and_notify(f"❌ 签到失败: Token已过期! (businessCode={biz_code})")
                log_and_notify(f"   请重新抓包获取新的Cookie/userToken")
                return False

            if biz_code == "1000":
                if isinstance(content, dict) and content:
                    points_earned = content.get("points", content.get("rewardPoints", "?"))
                    sign_days = content.get("continueDays", content.get("signDays", "?"))
                    log_and_notify(f"✅ 签到成功! 获得 {points_earned} 积分 | 连签: {sign_days}天")
                else:
                    log_and_notify(f"✅ 签到成功! 返回: {content}")
                return True
            elif "已签" in str(msg) or "already" in str(msg).lower() or "signed" in str(msg).lower():
                log_and_notify(f"📌 今日已签到，无需重复签到")
                return True
            else:
                log_and_notify(f"❌ 签到失败: businessCode={biz_code}, msg={msg}, des={response_des}")
                log_and_notify(f"   完整响应: {json.dumps(data, ensure_ascii=False)[:300]}")
                return False

        except Exception as e:
            log_and_notify(f"❌ 签到异常: {e}")
            return False

    def run(self):
        """运行签到流程"""
        log_and_notify(f"{'='*40}")
        log_and_notify(f"🏨 华住会自动签到")
        log_and_notify(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 提取 userToken 用于日志展示
        token_part = ""
        if "userToken=" in self.cookie:
            token_val = self.cookie.split("userToken=")[1].split(";")[0]
            token_part = token_val[:8] + "***" + token_val[-4:]
        log_and_notify(f"🔑 Token: {token_part}")
        log_and_notify(f"{'='*40}")

        # 1. 获取签到状态
        sign_info = self.get_sign_header()

        # Token过期则直接返回失败
        if sign_info and sign_info.get("token_expired"):
            return False

        # 如果已签到则跳过
        if sign_info and sign_info.get("is_signed"):
            log_and_notify("✅ 今日已完成签到，跳过")
            return True

        # 随机延迟
        delay = random.uniform(1, 3)
        time.sleep(delay)

        # 2. 执行签到
        result = self.do_checkin()

        # 3. 签到后再查一次状态确认
        if result:
            time.sleep(random.uniform(1, 2))
            self.get_sign_header()

        log_and_notify("")
        return result


# ============================================================
# 主入口
# ============================================================
def main():
    """主函数"""
    global notify_messages
    notify_messages = []

    log_and_notify("🏨 华住会自动签到程序启动")
    log_and_notify(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 从环境变量获取Cookie
    cookie_str = os.environ.get("HUAZHU_COOKIE", "填写__tea_cache_tokens_10000004={xxxx}")

    if not cookie_str:
        log_and_notify("❌ 未配置 HUAZHU_COOKIE 环境变量!")
        log_and_notify("请设置环境变量 HUAZHU_COOKIE 为华住会的Cookie")
        log_and_notify("Cookie 必须包含 userToken 字段")
        log_and_notify("多账号请用 & 或换行符分隔")
        send_notify("华住会签到失败", "\n".join(notify_messages))
        sys.exit(1)

    # 支持多账号，用 & 或换行分隔
    cookies = [c.strip() for c in cookie_str.replace("&", "\n").split("\n") if c.strip()]

    log_and_notify(f"📊 共检测到 {len(cookies)} 个账号\n")

    success_count = 0
    fail_count = 0

    for idx, cookie in enumerate(cookies, 1):
        log_and_notify(f"🔄 开始处理第 {idx}/{len(cookies)} 个账号")

        # 检查 cookie 中是否包含 userToken
        if "userToken=" not in cookie:
            log_and_notify(f"⚠️ 第 {idx} 个账号的Cookie中未找到 userToken，请检查")
            fail_count += 1
            continue

        try:
            checkin = HuazhuCheckin(cookie)
            result = checkin.run()
            if result:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            log_and_notify(f"❌ 第 {idx} 个账号处理异常: {e}")
            fail_count += 1

        # 多账号间随机延迟
        if idx < len(cookies):
            delay = random.uniform(3, 8)
            logger.info(f"账号间等待 {delay:.1f} 秒...")
            time.sleep(delay)

    # 汇总
    log_and_notify(f"\n{'='*40}")
    log_and_notify(f"📊 签到汇总: 成功 {success_count} | 失败 {fail_count} | 总计 {len(cookies)}")
    log_and_notify(f"{'='*40}")

    # 发送通知
    title = f"华住会签到 - 成功{success_count}/{len(cookies)}"
    send_notify(title, "\n".join(notify_messages))

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
