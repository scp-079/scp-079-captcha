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
from copy import deepcopy
from typing import List

from pyrogram import Client, Message

from .. import glovar
from .channel import send_debug
from .etc import code, general_link, lang, thread
from .file import save
from .telegram import get_group_info, send_message, send_report_message

# Enable logging
logger = logging.getLogger(__name__)


def conflict_config(config: dict, config_list: List[str], master: str) -> dict:
    # Conflict config
    result = config

    try:
        if master not in config_list:
            return config

        if not config.get(master, False):
            return config

        config_list.remove(master)

        for other in config_list:
            result[other] = False
    except Exception as e:
        logger.warning(f"Conflict config error: {e}", exc_info=True)

    return result


def get_config_text(config: dict) -> str:
    # Get the group's config text
    result = ""

    try:
        # Basic
        default_text = (lambda x: lang("default") if x else lang("custom"))(config.get("default"))
        delete_text = (lambda x: lang("enabled") if x else lang("disabled"))(config.get("delete"))
        restrict_text = (lambda x: lang("enabled") if x else lang("disabled"))(config.get("restrict"))
        result += (f"{lang('config')}{lang('colon')}{code(default_text)}\n"
                   f"{lang('delete')}{lang('colon')}{code(delete_text)}\n"
                   f"{lang('restrict')}{lang('colon')}{code(restrict_text)}\n")

        # Others
        for the_type in ["ban", "forgive", "hint", "pass", "pin", "qns", "manual"]:
            the_text = (lambda x: lang("enabled") if x else lang("disabled"))(config.get(the_type))
            result += f"{lang(the_type)}{lang('colon')}{code(the_text)}\n"
    except Exception as e:
        logger.warning(f"Get config text error: {e}", exc_info=True)

    return result


def start_qns(client: Client, message: Message, key: str) -> bool:
    # Start qns
    result = False

    try:
        # Basic data
        cid = message.chat.id
        uid = message.from_user.id
        mid = message.message_id
        gid = glovar.starts[key]["cid"]
        aid = glovar.starts[key]["uid"]

        # Check the permission
        if uid != aid:
            return False

        # Send the report message
        group_name, group_link = get_group_info(client, gid)
        text = (f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                f"{lang('group_id')}{lang('colon')}{code(gid)}\n"
                f"{lang('action')}{lang('colon')}{code('自定义问题设置')}\n"
                f"{lang('description')}{lang('colon')}{code('请开始设置所指定群组的自定义问题，自发起设置后，您共有 600 秒的时间来调整，逾时无效')}\n")
        thread(send_message, (client, cid, text, mid))

        result = True
    except Exception as e:
        logger.warning(f"Start qns error: {e}", exc_info=True)

    return result


def update_config(client: Client, message: Message, config: dict, more: str = "") -> bool:
    # Update a group's config
    result = False

    try:
        # Basic data
        gid = message.chat.id
        aid = message.from_user.id

        # Update the config
        glovar.configs[gid] = deepcopy(config)
        save("configs")

        # Send the report message
        text = (f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('config_change'))}\n"
                f"{lang('status')}{lang('colon')}{code(lang('status_succeeded'))}\n")

        if more:
            text += f"{lang('more')}{lang('colon')}{code(more)}\n"

        thread(send_report_message, (15, client, gid, text))

        # Send the debug message
        send_debug(
            client=client,
            gids=[gid],
            action=lang("config_change"),
            aid=aid,
            more=more
        )

        result = True
    except Exception as e:
        logger.warning(f"Update config error: {e}", exc_info=True)

    return result
