# SCP-079-CAPTCHA - Provide challenges for new joined members
# Copyright (C) 2019 SCP-079 <https://scp-079.org>
#
# This file is part of SCP-079-CAPTCHA.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import pickle
from codecs import getdecoder
from configparser import RawConfigParser
from glob import glob
from os import mkdir
from os.path import exists
from shutil import rmtree
from string import ascii_lowercase
from threading import Lock
from typing import Dict, List, Set, Union

from emoji import UNICODE_EMOJI
from pyrogram import Chat

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
    filename="log",
    filemode="w"
)
logger = logging.getLogger(__name__)

# Read data from config.ini

# [basic]
bot_token: str = ""
prefix: List[str] = []
prefix_str: str = "/!"

# [bots]
avatar_id: int = 0
captcha_id: int = 0
clean_id: int = 0
lang_id: int = 0
long_id: int = 0
noflood_id: int = 0
noporn_id: int = 0
nospam_id: int = 0
recheck_id: int = 0
tip_id: int = 0
user_id: int = 0
warn_id: int = 0

# [channels]
captcha_group_id: int = 0
critical_channel_id: int = 0
debug_channel_id: int = 0
exchange_channel_id: int = 0
hide_channel_id: int = 0
test_group_id: int = 0

# [custom]
backup: Union[bool, str] = ""
captcha_link: str = ""
date_reset: str = ""
default_group_link: str = ""
font_chinese: str = ""
font_english: str = ""
font_number: str = ""
limit_mention: int = 0
limit_static: int = 0
limit_track: int = 0
limit_try: int = 0
more: Union[bool, str] = ""
more_link: str = ""
more_text: str = ""
noise: float = 0.0
project_link: str = ""
project_name: str = ""
time_captcha: int = 0
time_invite: int = 0
time_new: int = 0
time_punish: int = 0
time_recheck: int = 0
time_remove: int = 0
time_short: int = 0
time_track: int = 0
zh_cn: Union[bool, str] = ""

# [emoji]
emoji_ad_single: int = 0
emoji_ad_total: int = 0
emoji_many: int = 0
emoji_protect: str = ""
emoji_wb_single: int = 0
emoji_wb_total: int = 0

# [encrypt]
key: Union[bytes, str] = ""
password: str = ""

try:
    config = RawConfigParser()
    config.read("config.ini")
    # [basic]
    bot_token = config["basic"].get("bot_token", bot_token)
    prefix = list(config["basic"].get("prefix", prefix_str))
    # [bots]
    avatar_id = int(config["bots"].get("avatar_id", avatar_id))
    captcha_id = int(config["bots"].get("captcha_id", captcha_id))
    clean_id = int(config["bots"].get("clean_id", clean_id))
    lang_id = int(config["bots"].get("lang_id", lang_id))
    long_id = int(config["bots"].get("long_id", long_id))
    noflood_id = int(config["bots"].get("noflood_id", noflood_id))
    noporn_id = int(config["bots"].get("noporn_id", noporn_id))
    nospam_id = int(config["bots"].get("nospam_id", nospam_id))
    recheck_id = int(config["bots"].get("recheck_id", recheck_id))
    tip_id = int(config["bots"].get("tip_id", tip_id))
    user_id = int(config["bots"].get("user_id", user_id))
    warn_id = int(config["bots"].get("warn_id", warn_id))
    # [channels]
    captcha_group_id = int(config["channels"].get("captcha_group_id", captcha_group_id))
    critical_channel_id = int(config["channels"].get("critical_channel_id", critical_channel_id))
    debug_channel_id = int(config["channels"].get("debug_channel_id", debug_channel_id))
    exchange_channel_id = int(config["channels"].get("exchange_channel_id", exchange_channel_id))
    hide_channel_id = int(config["channels"].get("hide_channel_id", hide_channel_id))
    test_group_id = int(config["channels"].get("test_group_id", test_group_id))
    # [custom]
    backup = config["custom"].get("backup", backup)
    backup = eval(backup)
    captcha_link = config["custom"].get("captcha_link", captcha_link)
    date_reset = config["custom"].get("date_reset", date_reset)
    default_group_link = config["custom"].get("default_group_link", default_group_link)
    font_chinese = config["custom"].get("font_chinese", font_chinese)
    font_english = config["custom"].get("font_english", font_english)
    font_number = config["custom"].get("font_number", font_number)
    limit_mention = int(config["custom"].get("limit_mention", limit_mention))
    limit_static = int(config["custom"].get("limit_static", limit_static))
    limit_track = int(config["custom"].get("limit_track", limit_track))
    limit_try = int(config["custom"].get("limit_try", limit_try))
    more = config["custom"].get("more", more)
    more = eval(more)
    more_link = config["custom"].get("more_link", more_link)
    more_text = config["custom"].get("more_text", more_text)
    noise = float(config["custom"].get("noise", noise))
    project_link = config["custom"].get("project_link", project_link)
    project_name = config["custom"].get("project_name", project_name)
    time_captcha = int(config["custom"].get("time_captcha", time_captcha))
    time_invite = int(config["custom"].get("time_invite", time_invite))
    time_new = int(config["custom"].get("time_new", time_new))
    time_punish = int(config["custom"].get("time_punish", time_punish))
    time_recheck = int(config["custom"].get("time_recheck", time_recheck))
    time_remove = int(config["custom"].get("time_remove", time_remove))
    time_short = int(config["custom"].get("time_short", time_short))
    time_track = int(config["custom"].get("time_track", time_track))
    zh_cn = config["custom"].get("zh_cn", zh_cn)
    zh_cn = eval(zh_cn)
    # [emoji]
    emoji_ad_single = int(config["emoji"].get("emoji_ad_single", emoji_ad_single))
    emoji_ad_total = int(config["emoji"].get("emoji_ad_total", emoji_ad_total))
    emoji_many = int(config["emoji"].get("emoji_many", emoji_many))
    emoji_protect = getdecoder("unicode_escape")(config["emoji"].get("emoji_protect", emoji_protect))[0]
    emoji_wb_single = int(config["emoji"].get("emoji_wb_single", emoji_wb_single))
    emoji_wb_total = int(config["emoji"].get("emoji_wb_total", emoji_wb_total))
    # [encrypt]
    key = config["encrypt"].get("key", key)
    key = key.encode("utf-8")
    password = config["encrypt"].get("password", password)
except Exception as e:
    logger.warning(f"Read data from config.ini error: {e}", exc_info=True)

# Check
if (bot_token in {"", "[DATA EXPUNGED]"}
        or prefix == []
        or avatar_id == 0
        or captcha_id == 0
        or clean_id == 0
        or lang_id == 0
        or long_id == 0
        or noflood_id == 0
        or noporn_id == 0
        or nospam_id == 0
        or recheck_id == 0
        or tip_id == 0
        or user_id == 0
        or warn_id == 0
        or captcha_group_id == 0
        or critical_channel_id == 0
        or debug_channel_id == 0
        or exchange_channel_id == 0
        or hide_channel_id == 0
        or test_group_id == 0
        or backup not in {False, True}
        or captcha_link in {"", "[DATA EXPUNGED]"}
        or date_reset in {"", "[DATA EXPUNGED]"}
        or default_group_link in {"", "[DATA EXPUNGED]"}
        or font_chinese in {"", "[DATA EXPUNGED]"}
        or font_english in {"", "[DATA EXPUNGED]"}
        or font_number in {"", "[DATA EXPUNGED]"}
        or limit_mention == 0
        or limit_static == 0
        or limit_track == 0
        or limit_try == 0
        or more not in {False, True}
        or more_link in {"", "[DATA EXPUNGED]"}
        or more_text in {"", "[DATA EXPUNGED]"}
        or noise == 0.0
        or project_link in {"", "[DATA EXPUNGED]"}
        or project_name in {"", "[DATA EXPUNGED]"}
        or time_captcha == 0
        or time_invite == 0
        or time_new == 0
        or time_punish == 0
        or time_recheck == 0
        or time_remove == 0
        or time_short == 0
        or time_track == 0
        or zh_cn not in {False, True}
        or emoji_ad_single == 0
        or emoji_ad_total == 0
        or emoji_many == 0
        or emoji_protect in {"", "[DATA EXPUNGED]"}
        or emoji_wb_single == 0
        or emoji_wb_total == 0
        or key in {b"", b"[DATA EXPUNGED]", "", "[DATA EXPUNGED]"}
        or password in {"", "[DATA EXPUNGED]"}):
    logger.critical("No proper settings")
    raise SystemExit("No proper settings")

# Languages
lang: Dict[str, str] = {
    # Admin
    "admin": (zh_cn and "管理员") or "Admin",
    "admin_group": (zh_cn and "群管理") or "Group Admin",
    "admin_project": (zh_cn and "项目管理员") or "Project Admin",
    # Basic
    "action": (zh_cn and "执行操作") or "Action",
    "clear": (zh_cn and "清空数据") or "Clear Data",
    "colon": (zh_cn and "：") or ": ",
    "description": (zh_cn and "说明") or "Description",
    "disabled": (zh_cn and "禁用") or "Disabled",
    "enabled": (zh_cn and "启用") or "Enabled",
    "name": (zh_cn and "名称") or "Name",
    "reason": (zh_cn and "原因") or "Reason",
    "reset": (zh_cn and "重置数据") or "Reset Data",
    "rollback": (zh_cn and "数据回滚") or "Rollback",
    "score": (zh_cn and "评分") or "Score",
    "status_failed": (zh_cn and "未执行") or "Failed",
    "status_succeeded": (zh_cn and "成功执行") or "Succeeded",
    "version": (zh_cn and "版本") or "Version",
    # Config
    "config": (zh_cn and "设置") or "Settings",
    "config_button": (zh_cn and "请点击下方按钮进行设置") or "Press the Button to Config",
    "config_change": (zh_cn and "更改设置") or "Change Config",
    "config_create": (zh_cn and "创建设置会话") or "Create Config Session",
    "config_go": (zh_cn and "前往设置") or "Go to Config",
    "config_locked": (zh_cn and "设置当前被锁定") or "Config is Locked",
    "config_show": (zh_cn and "查看设置") or "Show Config",
    "config_updated": (zh_cn and "已更新") or "Updated",
    "custom": (zh_cn and "自定义") or "Custom",
    "default": (zh_cn and "默认") or "Default",
    "delete": (zh_cn and "协助删除") or "Help Delete",
    "restrict": (zh_cn and "禁言模式") or "Restriction Mode",
    "ban": (zh_cn and "封禁模式") or "Ban Mode",
    "forgive": (zh_cn and "自动解禁") or "Auto Forgive",
    "hint": (zh_cn and "入群提示") or "Hint for New Joined User",
    "pass": (zh_cn and "自动免验证") or "Auto Pass",
    "manual": (zh_cn and "仅手动") or "Manual Only",
    # Command
    "command_lack": (zh_cn and "命令参数缺失") or "Lack of Parameter",
    "command_para": (zh_cn and "命令参数有误") or "Incorrect Command Parameter",
    "command_type": (zh_cn and "命令类别有误") or "Incorrect Command Type",
    "command_usage": (zh_cn and "用法有误") or "Incorrect Usage",
    # Debug
    "evidence": (zh_cn and "证据留存") or "Evidence",
    "triggered_by": (zh_cn and "触发消息") or "Triggered By",
    # Emergency
    "issue": (zh_cn and "发现状况") or "Issue",
    "exchange_invalid": (zh_cn and "数据交换频道失效") or "Exchange Channel Invalid",
    "auto_fix": (zh_cn and "自动处理") or "Auto Fix",
    "protocol_1": (zh_cn and "启动 1 号协议") or "Initiate Protocol 1",
    "transfer_channel": (zh_cn and "频道转移") or "Transfer Channel",
    "emergency_channel": (zh_cn and "应急频道") or "Emergency Channel",
    # Group
    "group_id": (zh_cn and "群组 ID") or "Group ID",
    "group_name": (zh_cn and "群组名称") or "Group Name",
    "inviter": (zh_cn and "邀请人") or "Inviter",
    "leave_auto": (zh_cn and "自动退出并清空数据") or "Leave automatically",
    "leave_approve": (zh_cn and "已批准退出群组") or "Approve to Leave the Group",
    "reason_admin": (zh_cn and "获取管理员列表失败") or "Failed to Fetch Admin List",
    "reason_leave": (zh_cn and "非管理员或已不在群组中") or "Not Admin in Group",
    "reason_none": (zh_cn and "无数据") or "No Data",
    "reason_permissions": (zh_cn and "权限缺失") or "Missing Permissions",
    "reason_unauthorized": (zh_cn and "未授权使用") or "Unauthorized",
    "reason_user": (zh_cn and "缺失 USER") or "Missing USER",
    "refresh": (zh_cn and "刷新群管列表") or "Refresh Admin Lists",
    "status_joined": (zh_cn and "已加入群组") or "Joined the Group",
    "status_left": (zh_cn and "已退出群组") or "Left the Group",
    # More
    "privacy": (zh_cn and "可能涉及隐私而未转发") or "Not Forwarded Due to Privacy Reason",
    "cannot_forward": (zh_cn and "此类消息无法转发至频道") or "The Message Cannot be Forwarded to Channel",
    # Message Types
    "gam": (zh_cn and "游戏") or "Game",
    "ser": (zh_cn and "服务消息") or "Service",
    # Record
    "project": (zh_cn and "项目编号") or "Project",
    "project_origin": (zh_cn and "原始项目") or "Original Project",
    "status": (zh_cn and "状态") or "Status",
    "user_id": (zh_cn and "用户 ID") or "User ID",
    "level": (zh_cn and "操作等级") or "Level",
    "rule": (zh_cn and "规则") or "Rule",
    "message_type": (zh_cn and "消息类别") or "Message Type",
    "message_game": (zh_cn and "游戏标识") or "Game Short Name",
    "message_lang": (zh_cn and "消息语言") or "Message Language",
    "message_len": (zh_cn and "消息长度") or "Message Length",
    "message_freq": (zh_cn and "消息频率") or "Message Frequency",
    "user_score": (zh_cn and "用户得分") or "User Score",
    "user_bio": (zh_cn and "用户简介") or "User Bio",
    "user_name": (zh_cn and "用户昵称") or "User Name",
    "from_name": (zh_cn and "来源名称") or "Forward Name",
    "contact": (zh_cn and "联系方式") or "Contact Info",
    "more": (zh_cn and "附加信息") or "Extra Info",
    # Special
    "action_invite": (zh_cn and "重新生成邀请链接") or "Generate New Invite Link",
    "action_pass": (zh_cn and "手动通过") or "Pass Manually",
    "action_static": (zh_cn and "发送固定提示消息") or "Send Static Hint",
    "action_undo_pass": (zh_cn and "撤销放行") or "Undo Pass",
    "action_verified": (zh_cn and "通过验证") or "Verified",
    "action_wait": (zh_cn and "等待验证") or "Wait for Verification",
    "attention": (zh_cn and "注意") or "Attention",
    "attention_invite": ((zh_cn and "如果提示链接无效，可能是因为链接正在更新，请多试几次")
                         or ("If it prompts that the link is invalid, "
                             "it may be because the link is being updated, please try a few more times")),
    "check_admin": ((zh_cn and "您为管理员，您可自由加入验证群组中查看机器人运行情况")
                    or "You are an admin, you are free to join the verification group to see how the bot works"),
    "check_no": (zh_cn and "您在本群中不需要验证即可发言") or "You can send messages without verification in this group",
    "check_pass": (zh_cn and "您在本群中已通过验证") or "You have passed the verification in this group",
    "check_yes": (zh_cn and "您需要验证才能在本群发言") or "You need to verify to send messages in this group",
    "captcha_check": (zh_cn and "我需要验证吗") or "Should I Verify",
    "captcha_go": (zh_cn and "前往验证") or "Go to Verify",
    "description_ask": (zh_cn and (f"请您尽快回答下方的问题以完成验证，"
                                   f"您可以点击相应按钮或直接发送正确答案。"
                                   f"注意，您共有 {{}} 次机会回答问题，答错将导致验证失败。"
                                   f"您在本群的任何发言均将视为对问题的回答，请谨慎发言")
                        or (f"Please answer the question below to complete the verification as soon as possible. "
                            f"You can click the button or send the right answer directly. "
                            f"Note that you have {{}} chances to answer the question, "
                            f"and incorrect answers will cause the verification to fail. "
                            f"Any message you send in this group will be considered as an answer to the question, "
                            f"please send carefully")),
    "description_again": ((zh_cn and "回答错误，请调整答案，再试一次")
                          or "Wrong answer, please adjust the answer and try again"),
    "description_captcha": (zh_cn and (f"待验证用户，请您点击下方右侧按钮进行验证，"
                                       f"请在 {time_captcha} 秒内完成验证，否则您将被移出本群。"
                                       f"如果您不是新入群用户，则本次验证为群组管理员的手动要求")
                            or (f"For users need to be verified, please click the button below to verify. "
                                f"Please complete verification within {time_captcha} seconds, "
                                f"or you will be removed from the group. "
                                f"If you are not a new user, "
                                f"this verification is a manual request by the group admin")),
    "description_hint": (zh_cn and (f"新入群用户，请您点击下方右侧按钮进行验证，"
                                    f"请在 {time_captcha} 秒内完成验证，否则您将被移出本群")
                         or (f"For new joined users, please click the button below to verify. "
                             f"Please complete verification within {time_captcha} seconds, "
                             f"or you will be removed from the group")),
    "description_banned": (zh_cn and "群管理封禁") or "Group admin passed your verification",
    "description_nospam": (zh_cn and (f"待验证用户，请您点击下方右侧按钮进行验证，"
                                      f"请在 {time_captcha} 秒内完成验证，否则您将被移出本群。"
                                      f"如果您不是新入群用户，则本次验证的发起可能为以下原因之一：群组管理员的手动要求；"
                                      f"您触发了防广告机器人的封禁规则，但由于您入群时间较长，故未封禁您，但要求您完成一次验证")
                           or (f"For users need to be verified, please click the button below to verify. "
                               f"Please complete verification within {time_captcha} seconds, "
                               f"or you will be removed from the group. "
                               f"If you are not a new user, "
                               f"this verification may be initiated for one of the following reasons: "
                               f"Manual request by the group admin; "
                               f"You triggered the rules of the anti-ad bot, "
                               f"but because you have been in the group for a long time, "
                               f"the bot does not ban You, but requires you to complete a verification")),
    "description_pass": (zh_cn and "群管理放行") or "Group admin banned you",
    "description_succeed": ((zh_cn and "验证成功，您可在相应群组中正常发言")
                            or "The verification is successful and you can speak in corresponding groups"),
    "description_timeout": (zh_cn and "验证超时") or "Verification Timeout",
    "description_wrong": (zh_cn and "验证失败，回答错误") or "Verification failed. Wrong answer",
    "flood_static": (zh_cn and "自动静态提示") or "Auto Static Hint",
    "invite_button": (zh_cn and "加入验证群组") or "Join CAPTCHA Group",
    "invite_text": (zh_cn and "请在专用群组中进行验证") or "Please verify in a private group",
    "question": (zh_cn and "问题") or "Question",
    "question_change": (zh_cn and "更换问题") or "Change the Question",
    "question_chengyu": (zh_cn and "请发送上图所显示的成语") or "Please send the idiom shown in the above picture",
    "question_food": ((zh_cn and "正确答案在下方按钮中，请选择或发送上图所显示的名称")
                      or ("The correct answer is in the buttons below, "
                          "please select or send the name shown in the above image")),
    "question_letter": ((zh_cn and "请发送上图所显示的一串英文字母（无数字，全部为英文字母），不区分大小写")
                        or "Please send a string of English letters (no numbers) as shown above, not case sensitive"),
    "question_math_pic": ((zh_cn and "正确答案在下方按钮中，请选择或发送上图中所显示的加减法算术题的正确答案")
                          or ("The correct answer is in the buttons below, please select or send the correct answer to "
                              "the addition or subtraction arithmetic question shown in the figure above")),
    "question_pic": ((zh_cn and "正确答案在下方按钮中，请选择或发送上图中所显示物体的正确名称")
                     or ("The correct answer is in the buttons below, "
                         "please select or send the correct name of the object shown in the picture above")),
    "question_number": ((zh_cn and "请发送上图所显示的一串数字（无英文字母，全部为数字）")
                        or "Please send a string of numbers as shown above"),
    "suggestion": (zh_cn and "建议") or "Suggestion",
    "suggestion_wrong": ((zh_cn and f"请您等待 {time_punish} 秒后，再重新加入原始群组（非本群）触发新的验证请求")
                         or f"Please wait {time_punish} seconds before re-joining the original group for verification"),
    "wait_user": (zh_cn and "待验证用户") or "Users Need to Be Verified",
    # Terminate
    "auto_ban": (zh_cn and "自动封禁") or "Auto Ban",
    "auto_delete": (zh_cn and "自动删除") or "Auto Delete",
    "auto_kick": (zh_cn and "自动移除") or "Auto Kick",
    "auto_restrict": (zh_cn and "自动禁言") or "Auto Restrict",
    "global_delete": (zh_cn and "全局删除") or "Global Delete",
    "name_ban": (zh_cn and "名称封禁") or "Ban by Name",
    "name_examine": (zh_cn and "名称检查") or "Name Examination",
    "name_recheck": (zh_cn and "名称复查") or "Name Recheck",
    "op_downgrade": (zh_cn and "操作降级") or "Operation Downgrade",
    "op_upgrade": (zh_cn and "操作升级") or "Operation Upgrade",
    "rule_custom": (zh_cn and "群组自定义") or "Custom Rule",
    "rule_global": (zh_cn and "全局规则") or "Global Rule",
    "score_ban": (zh_cn and "评分封禁") or "Ban by Score",
    "score_user": (zh_cn and "用户评分") or "High Score",
    "watch_ban": (zh_cn and "追踪封禁") or "Watch Ban",
    "watch_delete": (zh_cn and "追踪删除") or "Watch Delete",
    "watch_user": (zh_cn and "敏感追踪") or "Watched User",
    # Unit
    "members": (zh_cn and "名") or "member(s)",
    "seconds": (zh_cn and "秒") or "second(s)"
}

# Init

all_commands: List[str] = ["captcha", "config", "config_captcha", "invite", "pass", "static", "version"]

bot_ids: Set[int] = {avatar_id, captcha_id, clean_id, lang_id, long_id, noflood_id,
                     noporn_id, nospam_id, recheck_id, tip_id, user_id, warn_id}

chats: Dict[int, Chat] = {}
# chats = {
#     -10012345678: Chat
# }

declared_message_ids: Dict[int, Set[int]] = {}
# declared_message_ids = {
#     -10012345678: {123}
# }

default_config: Dict[str, Union[bool, int]] = {
    "default": True,
    "lock": 0,
    "delete": True,
    "restrict": False,
    "ban": False,
    "forgive": True,
    "hint": True,
    "pass": True,
    "manual": False
}

default_message_data: Dict[str, Union[int, Set[int]]] = {
    "flood": set(),
    "hint": 0,
    "static": 0
}

default_user_status: Dict[str, Union[int, str, Dict[Union[int, str], Union[float, int]], Set[int]]] = {
    "name": "",
    "mid": 0,
    "time": 0,
    "answer": "",
    "limit": 0,
    "try": 0,
    "join": {},
    "pass": {},
    "wait": {},
    "succeeded": {},
    "failed": {},
    "restricted": set(),
    "banned": set(),
    "score": {
        "captcha": 0.0,
        "clean": 0.0,
        "lang": 0.0,
        "long": 0.0,
        "noflood": 0.0,
        "noporn": 0.0,
        "nospam": 0.0,
        "recheck": 0.0,
        "warn": 0.0
    }
}

emoji_set: Set[str] = set(UNICODE_EMOJI)

locks: Dict[str, Lock] = {
    "admin": Lock(),
    "invite": Lock(),
    "message": Lock(),
    "receive": Lock(),
    "regex": Lock()
}

media_group_ids: Set[int] = set()
# media_group_ids = {12556677123456789}

question_types: Dict[str, List[str]] = {
    "changeable": ["chengyu", "letter", "number"],
    "chinese": ["chengyu", "food", "letter", "math", "math_pic", "number"],
    "english": ["letter", "math", "math_pic", "number"],
    "image": ["chengyu", "food", "letter", "math_pic", "number"],
    "text": ["math"]
}

receivers: Dict[str, List[str]] = {
    "declare": ["ANALYZE", "AVATAR", "CAPTCHA", "CLEAN", "LANG", "LONG",
                "NOFLOOD", "NOPORN", "NOSPAM", "RECHECK", "TIP", "USER", "WARN", "WATCH"],
    "score": ["ANALYZE", "CAPTCHA", "CLEAN", "LANG", "LONG", "MANAGE",
              "NOFLOOD", "NOPORN", "NOSPAM", "RECHECK", "TIP", "USER", "WARN", "WATCH"]
}

regex: Dict[str, bool] = {
    "ad": False,
    "ban": False,
    "bio": False,
    "con": False,
    "iml": False,
    "pho": False,
    "nm": False,
    "sho": True,
    "spc": True,
    "spe": False,
    "wb": True
}

for c in ascii_lowercase:
    regex[f"ad{c}"] = False

sender: str = "CAPTCHA"

should_hide: bool = False

usernames: Dict[str, Dict[str, Union[int, str]]] = {}
# usernames = {
#     "SCP_079": {
#         "peer_type": "channel",
#         "peer_id": -1001196128009
#     }
# }

version: str = "0.3.1"

# Load data from pics database

pics: Dict[str, Union[Dict[str, str], List[str]]] = {
    "names": [],
    "paths": {}
}

if exists("assets/pics"):
    dir_list = glob("assets/pics/*")
else:
    dir_list = []

for dir_path in dir_list:
    dir_name = dir_path.split("/")[-1]

    if not 0 < len(dir_name) < 6:
        continue

    pics["names"].append(dir_name)
    file_list = glob(f"{dir_path}/*")
    for file in file_list:
        pics["path"][file] = dir_name

if pics["names"] and pics["path"]:
    append_types = ["chinese", "english", "image"]
else:
    append_types = []

for question_type in append_types:
    question_types[question_type].append("pic")

# Load data from text

chinese_words: Dict[str, List[str]] = {
    "chengyu": [],
    "food": []
}

for word_type in ["chengyu", "food"]:
    with open(f"assets/{word_type}.txt", "r") as f:
        text = f.read()
        lines = text.split("\n")
        candidates = {line.split("\t")[0].strip() for line in lines}
        words = [word for word in candidates if 0 < len(word) < 6]
        chinese_words[word_type] = words

# Load data from pickle

# Init dir
try:
    rmtree("tmp")
except Exception as e:
    logger.info(f"Remove tmp error: {e}")

for path in ["data", "tmp"]:
    if not exists(path):
        mkdir(path)

# Init ids variables

admin_ids: Dict[int, Set[int]] = {}
# admin_ids = {
#     -10012345678: {12345678}
# }

bad_ids: Dict[str, Set[Union[int, str]]] = {
    "users": set()
}
# bad_ids = {
#     "users": {12345678}
# }

left_group_ids: Set[int] = set()
# left_group_ids = {-10012345678}

message_ids: Dict[int, Dict[str, Union[int, Set[int]]]] = {}
# message_ids = {
#     -10012345678: {
#         "flood": {120, 121, 122},
#         "hint": 123,
#         "static": 124
#     }
# }

user_ids: Dict[int, Dict[str, Union[int, str, Dict[Union[int, str], Union[float, int]], Set[int]]]] = {}
# user_ids = {
#     12345678: {
#         "name": "name",
#         "type": "text",
#         "mid": 123,
#         "time": 1512345678,
#         "answer": "",
#         "limit": 5,
#         "try": 0,
#         "join": {
#               -10012345678: 1512345678
#         },
#         "pass": {
#               -10012345678: 1512345678
#         },
#         "wait": {
#               -10012345678: 1512345678
#         },
#         "succeeded": {
#               -10012345678: 1512345678
#         },
#         "failed": {
#               -10012345678: 1512345678
#         },
#         "restricted": {-10012345678},
#         "banned": {-10012345678},
#         "score": {
#             "captcha": 0.0,
#             "clean": 0.0,
#             "lang": 0.0,
#             "long": 0.0,
#             "noflood": 0.0,
#             "noporn": 0.0,
#             "nospam": 0.0,
#             "recheck": 0.0,
#             "warn": 0.0
#         }
#     }
# }

watch_ids: Dict[str, Dict[int, int]] = {
    "ban": {},
    "delete": {}
}
# watch_ids = {
#     "ban": {
#         12345678: 1512345678
#     },
#     "delete": {
#         12345678: 1512345678
#     }
# }

# Init data variables

configs: Dict[int, Dict[str, Union[bool, int]]] = {}
# configs = {
#     -10012345678: {
#         "default": False,
#         "lock": 1512345678,
#         "delete": True,
#         "restrict": False,
#         "ban": False,
#         "forgive": True,
#         "hint": False,
#         "pass": True,
#         "manual": False
#     }
# }

invite: Dict[str, Union[int, str]] = {
    "link": "",
    "time": 0
}
# invite = {
#     "link": "https://t.me/SCP_079_CAPTCHA",
#     "time": 1512345678
# }

# Init word variables

for word_type in regex:
    locals()[f"{word_type}_words"]: Dict[str, Dict[str, Union[float, int]]] = {}

# type_words = {
#     "regex": 0
# }

# Load data
file_list: List[str] = ["admin_ids", "bad_ids", "left_group_ids", "message_ids", "user_ids", "watch_ids",
                        "configs", "invite"]
file_list += [f"{f}_words" for f in regex]
for file in file_list:
    try:
        try:
            if exists(f"data/{file}") or exists(f"data/.{file}"):
                with open(f"data/{file}", "rb") as f:
                    locals()[f"{file}"] = pickle.load(f)
            else:
                with open(f"data/{file}", "wb") as f:
                    pickle.dump(eval(f"{file}"), f)
        except Exception as e:
            logger.error(f"Load data {file} error: {e}", exc_info=True)
            with open(f"data/.{file}", "rb") as f:
                locals()[f"{file}"] = pickle.load(f)
    except Exception as e:
        logger.critical(f"Load data {file} backup error: {e}", exc_info=True)
        raise SystemExit("[DATA CORRUPTION]")

# Generate special characters dictionary
for special in ["spc", "spe"]:
    locals()[f"{special}_dict"]: Dict[str, str] = {}
    for rule in locals()[f"{special}_words"]:
        # Check keys
        if "[" not in rule:
            continue

        # Check value
        if "?#" not in rule:
            continue

        keys = rule.split("]")[0][1:]
        value = rule.split("?#")[1][1]
        for k in keys:
            locals()[f"{special}_dict"][k] = value

# Start program
copyright_text = (f"SCP-079-{sender} v{version}, Copyright (C) 2019 SCP-079 <https://scp-079.org>\n"
                  "Licensed under the terms of the GNU General Public License v3 or later (GPLv3+)\n")
print(copyright_text)
