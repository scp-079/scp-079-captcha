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

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
    filename="log",
    filemode="a"
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
font_chinese: str = ""
font_english: str = ""
font_number: str = ""
noise: float = 0.0

# [channels]
captcha_group_id: int = 0
critical_channel_id: int = 0
debug_channel_id: int = 0
exchange_channel_id: int = 0
hide_channel_id: int = 0
logging_channel_id: int = 0
test_group_id: int = 0

# [custom]
default_group_link: str = ""
more: Union[bool, str] = ""
more_link: str = ""
more_text: str = ""
project_link: str = ""
project_name: str = ""

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

# [language]
lang: str = ""
normalize: Union[bool, str] = ""

# [limit]
limit_flood: int = 0
limit_mention: int = 0
limit_track: int = 0
limit_try: int = 0

# [mode]
aio: Union[bool, str] = ""
backup: Union[bool, str] = ""
failed: Union[bool, str] = ""
simple: Union[bool, str] = ""
simple_only: Union[bool, str] = ""

# [time]
date_reset: str = ""
time_captcha: int = 0
time_invite: int = 0
time_new: int = 0
time_punish: int = 0
time_recheck: int = 0
time_remove: int = 0
time_short: int = 0
time_track: int = 0

try:
    config = RawConfigParser()
    config.read("config.ini")

    # [basic]
    bot_token = config["basic"].get("bot_token", bot_token)
    prefix = list(config["basic"].get("prefix", prefix_str))

    # [bots]
    avatar_id = int(config["bots"].get("avatar_id", str(avatar_id)))
    captcha_id = int(config["bots"].get("captcha_id", str(captcha_id)))
    clean_id = int(config["bots"].get("clean_id", str(clean_id)))
    index_id = int(config["bots"].get("index_id", str(index_id)))
    lang_id = int(config["bots"].get("lang_id", str(lang_id)))
    long_id = int(config["bots"].get("long_id", str(long_id)))
    noflood_id = int(config["bots"].get("noflood_id", str(noflood_id)))
    noporn_id = int(config["bots"].get("noporn_id", str(noporn_id)))
    nospam_id = int(config["bots"].get("nospam_id", str(nospam_id)))
    tip_id = int(config["bots"].get("tip_id", str(tip_id)))
    user_id = int(config["bots"].get("user_id", str(user_id)))
    warn_id = int(config["bots"].get("warn_id", str(warn_id)))

    # [captcha]
    captcha_link = config["captcha"].get("captcha_link", captcha_link)
    font_chinese = config["captcha"].get("font_chinese", font_chinese)
    font_english = config["captcha"].get("font_english", font_english)
    font_number = config["captcha"].get("font_number", font_number)
    noise = float(config["captcha"].get("noise", str(noise)))

    # [channels]
    captcha_group_id = int(config["channels"].get("captcha_group_id", str(captcha_group_id)))
    critical_channel_id = int(config["channels"].get("critical_channel_id", str(critical_channel_id)))
    debug_channel_id = int(config["channels"].get("debug_channel_id", str(debug_channel_id)))
    exchange_channel_id = int(config["channels"].get("exchange_channel_id", str(exchange_channel_id)))
    hide_channel_id = int(config["channels"].get("hide_channel_id", str(hide_channel_id)))
    logging_channel_id = int(config["channels"].get("logging_channel_id", str(logging_channel_id)))
    test_group_id = int(config["channels"].get("test_group_id", str(test_group_id)))

    # [custom]
    default_group_link = config["custom"].get("default_group_link", default_group_link)
    more = config["custom"].get("more", more)
    more = eval(more)
    more_link = config["custom"].get("more_link", more_link)
    more_text = config["custom"].get("more_text", more_text)
    project_link = config["custom"].get("project_link", project_link)
    project_name = config["custom"].get("project_name", project_name)

    # [emoji]
    emoji_ad_single = int(config["emoji"].get("emoji_ad_single", str(emoji_ad_single)))
    emoji_ad_total = int(config["emoji"].get("emoji_ad_total", str(emoji_ad_total)))
    emoji_many = int(config["emoji"].get("emoji_many", str(emoji_many)))
    emoji_protect = getdecoder("unicode_escape")(config["emoji"].get("emoji_protect", emoji_protect))[0]
    emoji_wb_single = int(config["emoji"].get("emoji_wb_single", str(emoji_wb_single)))
    emoji_wb_total = int(config["emoji"].get("emoji_wb_total", str(emoji_wb_total)))

    # [encrypt]
    key = config["encrypt"].get("key", key)
    key = key.encode("utf-8")
    password = config["encrypt"].get("password", password)

    # [language]
    lang = config["language"].get("lang", lang)
    normalize = config["language"].get("normalize", normalize)
    normalize = eval(normalize)

    # [limit]
    limit_flood = int(config["limit"].get("limit_flood", str(limit_flood)))
    limit_mention = int(config["limit"].get("limit_mention", str(limit_mention)))
    limit_track = int(config["limit"].get("limit_track", str(limit_track)))
    limit_try = int(config["limit"].get("limit_try", str(limit_try)))

    # [mode]
    aio = config["mode"].get("aio", aio)
    aio = eval(aio)
    backup = config["mode"].get("backup", backup)
    backup = eval(backup)
    failed = config["mode"].get("failed", failed)
    failed = eval(failed)
    simple = config["mode"].get("simple", simple)
    simple = eval(simple)
    simple_only = config["mode"].get("simple_only", simple_only)
    simple_only = eval(simple_only)

    # [time]
    date_reset = config["time"].get("date_reset", date_reset)
    time_captcha = int(config["time"].get("time_captcha", str(time_captcha)))
    time_invite = int(config["time"].get("time_invite", str(time_invite)))
    time_new = int(config["time"].get("time_new", str(time_new)))
    time_punish = int(config["time"].get("time_punish", str(time_punish)))
    time_recheck = int(config["time"].get("time_recheck", str(time_recheck)))
    time_remove = int(config["time"].get("time_remove", str(time_remove)))
    time_short = int(config["time"].get("time_short", str(time_short)))
    time_track = int(config["time"].get("time_track", str(time_track)))
except Exception as e:
    logger.warning(f"Read data from config.ini error: {e}", exc_info=True)

# Check
if (False
        # [basic]
        or bot_token in {"", "[DATA EXPUNGED]"}
        or prefix == []

        # [bots]
        or avatar_id == 0
        or captcha_id == 0
        or clean_id == 0
        or index_id == 0
        or lang_id == 0
        or long_id == 0
        or noflood_id == 0
        or noporn_id == 0
        or nospam_id == 0
        or tip_id == 0
        or user_id == 0
        or warn_id == 0

        # [captcha]
        or captcha_link in {"", "[DATA EXPUNGED]"}
        or font_chinese in {"", "[DATA EXPUNGED]"}
        or font_english in {"", "[DATA EXPUNGED]"}
        or font_number in {"", "[DATA EXPUNGED]"}
        or noise == 0.0

        # [channels]
        or captcha_group_id == 0
        or critical_channel_id == 0
        or debug_channel_id == 0
        or exchange_channel_id == 0
        or hide_channel_id == 0
        or logging_channel_id == 0
        or test_group_id == 0

        # [custom]
        or default_group_link in {"", "[DATA EXPUNGED]"}
        or more not in {False, True}
        or more_link in {"", "[DATA EXPUNGED]"}
        or more_text in {"", "[DATA EXPUNGED]"}
        or project_link in {"", "[DATA EXPUNGED]"}
        or project_name in {"", "[DATA EXPUNGED]"}

        # [emoji]
        or emoji_ad_single == 0
        or emoji_ad_total == 0
        or emoji_many == 0
        or emoji_protect in {"", "[DATA EXPUNGED]"}
        or emoji_wb_single == 0
        or emoji_wb_total == 0

        # [encrypt]
        or key in {b"", b"[DATA EXPUNGED]", "", "[DATA EXPUNGED]"}
        or password in {"", "[DATA EXPUNGED]"}

        # [language]
        or lang in {"", "[DATA EXPUNGED]"}
        or normalize not in {False, True}

        # [limit]
        or limit_mention == 0
        or limit_flood == 0
        or limit_track == 0
        or limit_try == 0

        # [mode]
        or aio not in {False, True}
        or backup not in {False, True}
        or failed not in {False, True}
        or simple not in {False, True}
        or simple_only not in {False, True}

        # [time]
        or date_reset in {"", "[DATA EXPUNGED]"}
        or time_captcha == 0
        or time_invite == 0
        or time_new == 0
        or time_punish == 0
        or time_recheck == 0
        or time_remove == 0
        or time_short == 0
        or time_track == 0):
    logger.critical("No proper settings")
    raise SystemExit("No proper settings")

# Language Dictionary
lang_dict: dict = {}

try:
    with open(f"languages/{lang}.yml", "r") as f:
        lang_dict = safe_load(f)
except Exception as e:
    logger.critical(f"Reading language YAML file failed: {e}", exc_info=True)
    raise SystemExit("Reading language YAML file failed")

# Init

all_commands: List[str] = [
    "captcha",
    "config",
    "config_captcha",
    "pass",
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
    "manual": False
}

default_custom_text: Dict[str, str] = {
    "flood": "",
    "manual": "",
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
    "failed": Lock(),
    "invite": Lock(),
    "message": Lock(),
    "pin": Lock(),
    "receive": Lock(),
    "regex": Lock()
}

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

version: str = "0.5.0"

# Load data from pics database

pics: Dict[str, List[str]] = {}

if exists("assets/pics"):
    dir_list = glob("assets/pics/*")
else:
    dir_list = []

for dir_path in dir_list:
    dir_name = dir_path.split("/")[-1]

    if not 0 < len(dir_name.encode()) <= 15:
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
#         }
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

trust_ids: Dict[int, Set[int]] = {}
# trust_ids = {
#     -10012345678: {12345678}
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
#             "action": "timeout",
#             "message id": 0,
#             "admin id": 0
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

# Init word variables

for word_type in regex:
    locals()[f"{word_type}_words"]: Dict[str, Dict[str, Union[float, int]]] = {}

# type_words = {
#     "regex": 0
# }

# Load data
file_list: List[str] = ["admin_ids", "bad_ids", "failed_ids", "ignore_ids", "lack_group_ids", "left_group_ids",
                        "message_ids", "pinned_ids", "trust_ids", "user_ids", "watch_ids", "white_ids",
                        "configs", "custom_texts", "flood_logs", "invite"]
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
