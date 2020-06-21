# SCP-079-CAPTCHA - Provide challenges for newly joined members
# Copyright (C) 2019-2020 SCP-079 <https://scp-079.org>
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
from yaml import safe_load

from .checker import check_all

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
    filename="log",
    filemode="a"
)
logger = logging.getLogger(__name__)

# Read data from config.ini

# [flag]
broken: bool = True

# [basic]
bot_token: str = ""
prefix: List[str] = []
prefix_str: str = "/!"

# [bots]
avatar_id: int = 0
captcha_id: int = 0
clean_id: int = 0
index_id: int = 0
lang_id: int = 0
long_id: int = 0
noflood_id: int = 0
noporn_id: int = 0
nospam_id: int = 0
tip_id: int = 0
user_id: int = 0
warn_id: int = 0

# [captcha]
captcha_link: str = ""
font_chinese: str = "/usr/share/fonts/truetype/arphic-gkai00mp/gkai00mp.ttf"
font_english: str = "/usr/share/fonts/truetype/freefont/FreeMono.ttf"
font_number: str = "/usr/share/fonts/truetype/freefont/FreeMono.ttf"
noise: float = 0.4

# [channels]
captcha_group_id: int = 0
critical_channel_id: int = 0
debug_channel_id: int = 0
exchange_channel_id: int = 0
hide_channel_id: int = 0
logging_channel_id: int = 0
test_group_id: int = 0

# [custom]
default_group_link: str = "https://t.me/SCP_079_DEBUG"
leave_button: str = "申请使用"
leave_link: str = "https://scp-079.org/ApplyForUse/"
leave_reason: str = "需要授权方可使用"
more: Union[bool, str] = "True"
more_link: str = "https://scp-079.org/readme/"
more_text: str = "点击了解本项目"
project_link: str = "https://scp-079.org/captcha/"
project_name: str = "SCP-079-CAPTCHA"

# [emoji]
emoji_ad_single: int = 15
emoji_ad_total: int = 30
emoji_many: int = 15
emoji_protect: str = "\\U0001F642"
emoji_wb_single: int = 10
emoji_wb_total: int = 15

# [encrypt]
key: Union[bytes, str] = ""
password: str = ""

# [language]
lang: str = "cmn-Hans"
normalize: Union[bool, str] = "True"

# [limit]
limit_flood: int = 10
limit_mention: int = 20
limit_track: int = 8
limit_try: int = 2

# [mode]
aio: Union[bool, str] = "False"
backup: Union[bool, str] = "False"
failed: Union[bool, str] = "False"
simple: Union[bool, str] = "False"
simple_only: Union[bool, str] = "False"

# [time]
date_reset: str = "1st mon"
time_captcha: int = 240
time_invite: int = 1800
time_new: int = 1800
time_punish: int = 600
time_recheck: int = 3600
time_remove: int = 300
time_short: int = 300
time_track: int = 3600

try:
    config = RawConfigParser()
    config.read("config.ini")

    # [basic]
    bot_token = config.get("basic", "bot_token", fallback=bot_token)
    prefix_str = config.get("basic", "prefix", fallback=prefix_str)
    prefix = [p for p in list(prefix_str) if p]

    # [bots]
    avatar_id = int(config.get("bots", "avatar_id", fallback=avatar_id))
    captcha_id = int(config.get("bots", "captcha_id", fallback=captcha_id))
    clean_id = int(config.get("bots", "clean_id", fallback=clean_id))
    index_id = int(config.get("bots", "index_id", fallback=index_id))
    lang_id = int(config.get("bots", "lang_id", fallback=lang_id))
    long_id = int(config.get("bots", "long_id", fallback=long_id))
    noflood_id = int(config.get("bots", "noflood_id", fallback=noflood_id))
    noporn_id = int(config.get("bots", "noporn_id", fallback=noporn_id))
    nospam_id = int(config.get("bots", "nospam_id", fallback=nospam_id))
    tip_id = int(config.get("bots", "tip_id", fallback=tip_id))
    user_id = int(config.get("bots", "user_id", fallback=user_id))
    warn_id = int(config.get("bots", "warn_id", fallback=warn_id))

    # [captcha]
    captcha_link = config.get("captcha", "captcha_link", fallback=captcha_link)
    font_chinese = config.get("captcha", "font_chinese", fallback=font_chinese)
    font_english = config.get("captcha", "font_english", fallback=font_english)
    font_number = config.get("captcha", "font_english", fallback=font_number)
    noise = float(config.get("captcha", "noise", fallback=noise))

    # [channels]
    captcha_group_id = int(config.get("channels", "captcha_group_id", fallback=captcha_group_id))
    critical_channel_id = int(config.get("channels", "critical_channel_id", fallback=critical_channel_id))
    debug_channel_id = int(config.get("channels", "debug_channel_id", fallback=debug_channel_id))
    exchange_channel_id = int(config.get("channels", "exchange_channel_id", fallback=exchange_channel_id))
    hide_channel_id = int(config.get("channels", "hide_channel_id", fallback=hide_channel_id))
    logging_channel_id = int(config.get("channels", "logging_channel_id", fallback=logging_channel_id))
    test_group_id = int(config.get("channels", "test_group_id", fallback=test_group_id))

    # [custom]
    default_group_link = config.get("custom", "default_group_link", fallback=default_group_link)
    leave_button = config.get("custom", "leave_button", fallback=leave_button)
    leave_link = config.get("custom", "leave_link", fallback=leave_link)
    leave_reason = config.get("custom", "leave_reason", fallback=leave_reason)
    more = config.get("custom", "more", fallback=more)
    more = eval(more)
    more_link = config.get("custom", "more_link", fallback=more_link)
    more_text = config.get("custom", "more_text", fallback=more_text)
    project_link = config.get("custom", "project_link", fallback=project_link)
    project_name = config.get("custom", "project_name", fallback=project_name)

    # [emoji]
    emoji_ad_single = int(config.get("emoji", "emoji_ad_single", fallback=emoji_ad_single))
    emoji_ad_total = int(config.get("emoji", "emoji_ad_total", fallback=emoji_ad_total))
    emoji_many = int(config.get("emoji", "emoji_many", fallback=emoji_many))
    emoji_protect = config.get("emoji", "emoji_protect", fallback=emoji_protect)
    emoji_protect = getdecoder("unicode_escape")(emoji_protect)[0]
    emoji_wb_single = int(config.get("emoji", "emoji_wb_single", fallback=emoji_wb_single))
    emoji_wb_total = int(config.get("emoji", "emoji_wb_total", fallback=emoji_wb_total))

    # [encrypt]
    key = config.get("encrypt", "key", fallback=key)
    key = key.encode("utf-8")
    password = config.get("encrypt", "password", fallback=password)

    # [language]
    lang = config.get("language", "lang", fallback=lang)
    normalize = config.get("language", "normalize", fallback=normalize)
    normalize = eval(normalize)

    # [limit]
    limit_flood = int(config.get("limit", "limit_flood", fallback=limit_flood))
    limit_mention = int(config.get("limit", "limit_mention", fallback=limit_mention))
    limit_track = int(config.get("limit", "limit_track", fallback=limit_track))
    limit_try = int(config.get("limit", "limit_try", fallback=limit_try))

    # [mode]
    aio = config.get("mode", "aio", fallback=aio)
    aio = eval(aio)
    backup = config.get("mode", "backup", fallback=backup)
    backup = eval(backup)
    failed = config.get("mode", "failed", fallback=failed)
    failed = eval(failed)
    simple = config.get("mode", "simple", fallback=simple)
    simple = eval(simple)
    simple_only = config.get("mode", "simple_only", fallback=simple_only)
    simple_only = eval(simple_only)

    # [time]
    date_reset = config.get("time", "date_reset", fallback=date_reset)
    time_captcha = int(config.get("time", "time_captcha", fallback=time_captcha))
    time_invite = int(config.get("time", "time_invite", fallback=time_invite))
    time_new = int(config.get("time", "time_new", fallback=time_new))
    time_punish = int(config.get("time", "time_punish", fallback=time_punish))
    time_recheck = int(config.get("time", "time_recheck", fallback=time_recheck))
    time_remove = int(config.get("time", "time_remove", fallback=time_remove))
    time_short = int(config.get("time", "time_short", fallback=time_short))
    time_track = int(config.get("time", "time_track", fallback=time_track))

    # [flag]
    broken = False
except Exception as e:
    print("[ERROR] Read data from config.ini error, please check the log file")
    logger.warning(f"Read data from config.ini error: {e}", exc_info=True)

# Check
check_all(
    {
        "bots": {
            "avatar_id": avatar_id,
            "captcha_id": captcha_id,
            "clean_id": clean_id,
            "index_id": index_id,
            "lang_id": lang_id,
            "long_id": long_id,
            "noflood_id": noflood_id,
            "noporn_id": noporn_id,
            "nospam_id": nospam_id,
            "tip_id": tip_id,
            "user_id": user_id,
            "warn_id": warn_id
        },
        "captcha": {
            "captcha_link": captcha_link,
            "font_chinese": font_chinese,
            "font_english": font_english,
            "font_number": font_number,
            "noise": noise
        },
        "channels": {
            "captcha_group_id": captcha_group_id,
            "critical_channel_id": critical_channel_id,
            "debug_channel_id": debug_channel_id,
            "exchange_channel_id": exchange_channel_id,
            "hide_channel_id": hide_channel_id,
            "logging_channel_id": logging_channel_id,
            "test_group_id": test_group_id
        },
        "custom": {
            "default_group_link": default_group_link,
            "leave_button": leave_button,
            "leave_link": leave_link,
            "leave_reason": leave_reason,
            "more": more,
            "more_link": more_link,
            "more_text": more_text,
            "project_link": project_link,
            "project_name": project_name
        },
        "emoji": {
            "emoji_ad_single": emoji_ad_single,
            "emoji_ad_total": emoji_ad_total,
            "emoji_many": emoji_many,
            "emoji_protect": emoji_protect,
            "emoji_wb_single": emoji_wb_single,
            "emoji_wb_total": emoji_wb_total
        },
        "encrypt": {
            "key": key,
            "password": password
        },
        "language": {
            "lang": lang,
            "normalize": normalize
        },
        "limit": {
            "limit_flood": limit_flood,
            "limit_mention": limit_mention,
            "limit_track": limit_track,
            "limit_try": limit_try
        },
        "mode": {
            "aio": aio,
            "backup": backup,
            "failed": failed,
            "simple": simple,
            "simple_only": simple_only
        },
        "time": {
            "date_reset": date_reset,
            "time_captcha": time_captcha,
            "time_invite": time_invite,
            "time_new": time_new,
            "time_punish": time_punish,
            "time_recheck": time_recheck,
            "time_remove": time_remove,
            "time_short": time_short,
            "time_track": time_track
        }
    },
    broken
)

# Language Dictionary
lang_dict: dict = {}

try:
    with open(f"languages/{lang}.yml", "r", encoding="utf-8") as f:
        lang_dict = safe_load(f)
except Exception as e:
    logger.critical(f"Reading language YAML file failed: {e}", exc_info=True)
    raise SystemExit("Reading language YAML file failed")

# Init

all_commands: List[str] = [
    "add",
    "captcha",
    "config",
    "config_captcha",
    "custom",
    "edit",
    "help",
    "pass",
    "qns",
    "remove",
    "rm",
    "show",
    "start",
    "static",
    "version"
]

bot_ids: Set[int] = {avatar_id, captcha_id, clean_id, index_id, lang_id, long_id,
                     noflood_id, noporn_id, nospam_id, tip_id, user_id, warn_id}

chats: Dict[int, Chat] = {}
# chats = {
#     -10012345678: Chat
# }

changed_ids: Set[int] = set()
# changed_ids = {12345678}

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
    "pin": True,
    "qns": False,
    "manual": False,
}

default_custom_text: Dict[str, str] = {
    "flood": "",
    "manual": "",
    "multi": "",
    "nospam": "",
    "single": "",
    "static": ""
}

default_message_data: Dict[str, Union[int, Dict[int, int], Set[int]]] = {
    "flood": set(),
    "hint": 0,
    "static": 0,
    "manual": {},
    "nospam": {}
}

default_pinned_data: Dict[str, int] = {
    "new_id": 0,
    "old_id": 0,
    "start": 0,
    "last": 0
}

default_question_data: Dict[str, Union[int, str, Dict[str, Dict[str, Union[int, str, Set[str]]]]]] = {
    "lock": 0,
    "aid": 0,
    "last": "",
    "qns": {}
}

default_user_status: Dict[str, Union[int, str, Dict[Union[int, str], Union[float, int, str]], Set[int]]] = {
    "name": "",
    "mid": 0,
    "time": 0,
    "answer": "",
    "limit": 0,
    "try": 0,
    "join": {},
    "pass": {},
    "wait": {},
    "qns": {},
    "succeeded": {},
    "failed": {},
    "restricted": set(),
    "banned": set(),
    "manual": set(),
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
    "ban": Lock(),
    "config": Lock(),
    "failed": Lock(),
    "flood": Lock(),
    "invite": Lock(),
    "message": Lock(),
    "pin": Lock(),
    "receive": Lock(),
    "regex": Lock()
}

pass_counts: Dict[int, int] = {}
# pass_counts = {
#     -10012345678: 0
# }

question_types: Dict[str, List[str]] = {
    "changeable": ["chengyu", "letter", "math_pic", "number"],
    "chinese": ["chengyu", "food", "letter", "math_pic", "number"],
    "english": ["letter", "math_pic", "number"],
    "image": ["chengyu", "food", "letter", "math_pic", "pic", "number"],
    "text": ["math"]
}

if simple:
    append_types = ["chinese", "english"]
else:
    append_types = []

for question_type in append_types:
    question_types[question_type].append("math")

if simple_only:
    replace_types = ["chinese", "english"]
else:
    replace_types = []

for question_type in replace_types:
    question_types[question_type] = ["math"]

receivers: Dict[str, List[str]] = {
    "flood": ["AVATAR", "CAPTCHA", "CLEAN", "LANG", "LONG", "NOFLOOD", "NOPORN",
              "NOSPAM", "TIP", "USER", "WATCH"],
    "declare": ["ANALYZE", "AVATAR", "CAPTCHA", "CLEAN", "LANG", "LONG",
                "NOFLOOD", "NOPORN", "NOSPAM", "TIP", "USER", "WARN", "WATCH"],
    "score": ["ANALYZE", "AVATAR", "CAPTCHA", "CLEAN", "INDEX", "LANG", "LONG",
              "MANAGE", "NOFLOOD", "NOPORN", "NOSPAM", "TIP", "USER", "WARN", "WATCH"]
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

version: str = "0.6.6"

# Load data from pics database

pics: Dict[str, List[str]] = {}

if exists("assets/pics"):
    dir_list = glob("assets/pics/*")
else:
    dir_list = []

for dir_path in dir_list:
    dir_name = dir_path.split("/")[-1]

    if not 0 < len(dir_name.encode()) <= 64:
        continue

    pics[dir_name] = []
    file_list = glob(f"{dir_path}/*")

    for file in file_list:
        pics[dir_name].append(file)

if pics and not simple_only:
    append_types = ["chinese", "english"]
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
    with open(f"assets/{word_type}.txt", "r", encoding="utf-8") as f:
        text = f.read()
        lines = text.split("\n")
        candidates = {line.split("\t")[0].strip() for line in lines}
        words = [word for word in candidates if 0 < len(word.encode()) <= 64]
        chinese_words[word_type] = words

# Load data from pickle

# Init dir
try:
    rmtree("tmp")
except Exception as e:
    logger.info(f"Remove tmp error: {e}")

for path in ["data", "tmp"]:
    not exists(path) and mkdir(path)

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

failed_ids: Dict[int, Dict[str, Union[bool, str]]] = {}
# failed_ids = {
#     12345678: {
#         "username": False,
#         "first": "",
#         "last": "",
#         "bio": "",
#         "reason": ""
#     }
# }

flooded_ids: Set[int] = set()
# flooded_ids = {-10012345678}

ignore_ids: Dict[str, Set[int]] = {
    "nospam": set(),
    "user": set()
}
# ignore_ids = {
#     "nospam": {-10012345678},
#     "user": {-10012345678}
# }

lack_group_ids: Set[int] = set()
# lack_group_ids = {-10012345678}

left_group_ids: Set[int] = set()
# left_group_ids = {-10012345678}

message_ids: Dict[int, Dict[str, Union[int, Dict[int, int], Set[int]]]] = {}
# message_ids = {
#     -10012345678: {
#         "flood": {120, 121, 122},
#         "hint": 123,
#         "static": 124,
#         "manual": {
#             125: 1512345678
#         },
#         "nospam": {
#             126: 1512345678
#         }
#     }
# }

pinned_ids: Dict[int, Dict[str, int]] = {}
# pinned_ids = {
#     -10012345678: {
#         "new_id": 123,
#         "old_id": 122,
#         "start": 1512345678,
#         "last": 1512345678
#     }
# }

token: str = ""

trust_ids: Dict[int, Set[int]] = {}
# trust_ids = {
#     -10012345678: {12345678}
# }

user_ids: Dict[int, Dict[str, Union[int, str, Dict[Union[int, str], Union[float, int, str]], Set[int]]]] = {}
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
#             -10012345678: 1512345678
#         },
#         "pass": {
#             -10012345678: 1512345678
#         },
#         "wait": {
#             -10012345678: 1512345678
#         },
#         "qns": {
#             -10012345678: "tag"
#         },
#         "succeeded": {
#             -10012345678: 1512345678
#         },
#         "failed": {
#             -10012345678: 1512345678
#         },
#         "restricted": {-10012345678},
#         "banned": {-10012345678},
#         "manual": {-10012345678},
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

white_ids: Set[int] = set()
# white_ids = {12345678}

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

custom_texts: Dict[int, Dict[str, str]] = {}
# custom_texts = {
#     -10012345678: {
#         "flood": "",
#         "manual": "",
#         "multi": "",
#         "nospam": "",
#         "single": "",
#         "static": ""
#     }
# }

flood_logs: Dict[int, List[Dict[str, Union[int, str]]]] = {}
# flood_logs = {
#     -10012345678: [
#         {
#             "user id": 12345678,
#             "time": 205001011200,
#             "action": "kick",
#             "reason": "timeout",
#             "message id": None,
#             "admin id": None
#         }
#     ]
# }

invite: Dict[str, Union[int, str]] = {
    "link": "",
    "time": 0
}
# invite = {
#     "link": "https://t.me/SCP_079_CAPTCHA",
#     "time": 1512345678
# }

questions: Dict[int, Dict[str, Union[int, str, Dict[str, Dict[str, Union[int, str, Set[str]]]]]]] = {}
# questions = {
#     -10012345678: {
#         "lock": 1512345678,
#         "aid": 12345678,
#         "last": "tag",
#         "qns": {
#             "tag": {
#                 "time": 1511234578,
#                 "aid": 12345678,
#                 "question": "a question",
#                 "correct": {"answer1"},
#                 "wrong": {"answer2"},
#                 "issued": 0,
#                 "engaged": 0,
#                 "solved": 0
#             }
#         }
#     }
# }

reset_time: List[Union[int, bool]] = [0, True]

starts: Dict[str, Dict[str, Union[int, str]]] = {}
# starts = {
#     "random": {
#         "until": 1512345678,
#         "cid": -10012345678,
#         "uid": 12345678,
#         "action": "act"
#     }
# }

# Init word variables

for word_type in regex:
    locals()[f"{word_type}_words"]: Dict[str, Dict[str, Union[float, int]]] = {}

# type_words = {
#     "regex": 0
# }

# Load data
file_list: List[str] = ["admin_ids", "bad_ids", "failed_ids", "flooded_ids", "ignore_ids", "lack_group_ids",
                        "left_group_ids", "message_ids", "pinned_ids", "trust_ids", "user_ids", "watch_ids",
                        "white_ids",
                        "configs", "custom_texts", "flood_logs", "invite", "questions", "reset_time", "starts",
                        "token"]
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
copyright_text = (f"SCP-079-{sender} v{version}, Copyright (C) 2019-2020 SCP-079 <https://scp-079.org>\n"
                  "Licensed under the terms of the GNU General Public License v3 or later (GPLv3+)\n")
print(copyright_text)
