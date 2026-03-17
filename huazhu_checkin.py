#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华住会自动签到脚本
支持: GitHub Actions / 青龙面板 / 本地运行
Author: Auto Generated
Cron: 0 8 * * *  (每天早上8点执行)

环境变量:
  HUAZHU_COOKIE: 华住会Cookie，多账号用 & 或换行分隔
  PUSH_KEY:      Server酱推送Key (可选)
  TG_BOT_TOKEN:  Telegram Bot Token (可选)
  TG_CHAT_ID:    Telegram Chat ID (可选)

获取Cookie方法:
  1. 微信打开华住会小程序
  2. 进入 "会员" -> "签到" 页面
  3. 使用抓包工具 (Charles/Fiddler) 抓取请求
  4. 找到 hweb-minilogin.huazhu.com 相关请求的 Cookie
  5. 或者抓取完整的签到请求URL中的参数
"""

import os
import sys
import json
import time
import random
import hashlib
import logging
from datetime import datetime
from urllib.parse import urlencode, quote

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
# 全局配置
# ============================================================
BASE_URL = "https://hweb-minilogin.huazhu.com"
SIGN_URL = f"{BASE_URL}/api/sign/signIn"
SIGN_INFO_URL = f"{BASE_URL}/api/sign/getSignInfo"
USER_INFO_URL = f"{BASE_URL}/api/member/getMemberInfo"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 "
                  "MicroMessenger/8.0.44.2540(0x28002C37) Process/appbrand0 "
                  "WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 "
                  "MiniProgramEnv/android",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Origin": "https://hweb-minilogin.huazhu.com",
    "Referer": "https://hweb-minilogin.huazhu.com/",
    "Connection": "keep-alive",
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
            else:
                logger.warning(f"Server酱推送失败: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Server酱推送异常: {e}")

    # Telegram Bot推送
    tg_token = os.environ.get("TG_BOT_TOKEN", "")
    tg_chat_id = os.environ.get("TG_CHAT_ID", "")
    if tg_token and tg_chat_id:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            data = {"chat_id": tg_chat_id, "text": f"{title}\n\n{content}", "parse_mode": "HTML"}
            resp = requests.post(url, json=data, timeout=10)
            if resp.status_code == 200:
                logger.info("Telegram推送成功")
            else:
                logger.warning(f"Telegram推送失败: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Telegram推送异常: {e}")

    # 青龙面板内置通知 (通过环境变量 QLAPI)
    # 青龙面板通常会自动捕获print输出作为日志

    # Bark推送
    bark_key = os.environ.get("BARK_KEY", "")
    if bark_key:
        try:
            url = f"https://api.day.app/{bark_key}/{quote(title)}/{quote(content)}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                logger.info("Bark推送成功")
        except Exception as e:
            logger.warning(f"Bark推送异常: {e}")

    # PushPlus推送
    pushplus_token = os.environ.get("PUSHPLUS_TOKEN", "")
    if pushplus_token:
        try:
            url = "https://www.pushplus.plus/send"
            data = {"token": pushplus_token, "title": title, "content": content}
            resp = requests.post(url, json=data, timeout=10)
            if resp.status_code == 200:
                logger.info("PushPlus推送成功")
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
        self.nickname = "未知用户"
        self.member_level = ""
        self.points = 0

    def _request(self, method, url, **kwargs):
        """封装请求，增加重试和错误处理"""
        kwargs.setdefault("timeout", 30)
        for attempt in range(3):
            try:
                resp = self.session.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/3): {e}")
                if attempt < 2:
                    time.sleep(random.uniform(2, 5))
                else:
                    raise
        return None

    def get_user_info(self):
        """获取用户信息"""
        try:
            data = self._request("GET", USER_INFO_URL)
            if data and data.get("code") == 0:
                info = data.get("data", {})
                self.nickname = info.get("nickname", info.get("memberName", "未知用户"))
                self.member_level = info.get("levelName", "")
                self.points = info.get("totalPoints", info.get("points", 0))
                log_and_notify(f"👤 用户: {self.nickname} | 等级: {self.member_level} | 积分: {self.points}")
                return True
            else:
                msg = data.get("msg", "未知错误") if data else "请求失败"
                log_and_notify(f"❌ 获取用户信息失败: {msg}")
                return False
        except Exception as e:
            log_and_notify(f"❌ 获取用户信息异常: {e}")
            return False

    def get_sign_info(self):
        """获取签到状态"""
        try:
            data = self._request("GET", SIGN_INFO_URL)
            if data and data.get("code") == 0:
                info = data.get("data", {})
                is_signed = info.get("isTodaySigned", info.get("isSign", False))
                sign_days = info.get("continueDays", info.get("signDays", 0))
                if is_signed:
                    log_and_notify(f"📋 今日已签到 | 连续签到: {sign_days}天")
                else:
                    log_and_notify(f"📋 今日未签到 | 连续签到: {sign_days}天")
                return {"is_signed": is_signed, "sign_days": sign_days}
            else:
                msg = data.get("msg", "未知错误") if data else "请求失败"
                log_and_notify(f"⚠️ 获取签到信息失败: {msg}")
                return None
        except Exception as e:
            log_and_notify(f"⚠️ 获取签到信息异常: {e}")
            return None

    def do_checkin(self):
        """执行签到"""
        try:
            # 构造签到请求体
            timestamp = int(time.time() * 1000)
            payload = {
                "timestamp": timestamp,
            }

            data = self._request("POST", SIGN_URL, json=payload)

            if data is None:
                log_and_notify("❌ 签到请求失败，无响应")
                return False

            code = data.get("code", -1)
            msg = data.get("msg", data.get("message", "未知"))

            if code == 0:
                result = data.get("data", {})
                points_earned = result.get("points", result.get("rewardPoints", "未知"))
                sign_days = result.get("continueDays", result.get("signDays", ""))
                log_and_notify(f"✅ 签到成功! 获得 {points_earned} 积分 | 连续签到: {sign_days}天")
                return True
            elif "已签到" in str(msg) or "already" in str(msg).lower():
                log_and_notify(f"📌 今日已签到，无需重复签到")
                return True
            else:
                log_and_notify(f"❌ 签到失败: [{code}] {msg}")
                return False

        except Exception as e:
            log_and_notify(f"❌ 签到异常: {e}")
            return False

    def run(self):
        """运行签到流程"""
        log_and_notify(f"{'='*40}")
        log_and_notify(f"🏨 华住会自动签到")
        log_and_notify(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_and_notify(f"{'='*40}")

        # 1. 获取用户信息
        self.get_user_info()

        # 随机延迟，模拟人工操作
        delay = random.uniform(1, 3)
        logger.info(f"等待 {delay:.1f} 秒...")
        time.sleep(delay)

        # 2. 获取签到状态
        sign_info = self.get_sign_info()

        # 如果已签到则跳过
        if sign_info and sign_info.get("is_signed"):
            log_and_notify("✅ 今日已完成签到，跳过")
            return True

        # 随机延迟
        delay = random.uniform(1, 3)
        time.sleep(delay)

        # 3. 执行签到
        result = self.do_checkin()

        # 4. 签到后再次获取信息确认
        if result:
            time.sleep(random.uniform(1, 2))
            self.get_sign_info()

        log_and_notify(f"{'='*40}\n")
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
    cookie_str = os.environ.get("HUAZHU_COOKIE", "")

    if not cookie_str:
        log_and_notify("❌ 未配置 HUAZHU_COOKIE 环境变量!")
        log_and_notify("请设置环境变量 HUAZHU_COOKIE 为华住会的Cookie")
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

    # 汇总结果
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
