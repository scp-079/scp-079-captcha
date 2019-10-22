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
from time import sleep
from typing import Union

from pyrogram import ChatPermissions, Client

from .. import glovar
from .channel import declare_message
from .etc import thread
from .group import delete_message
from .ids import init_user_id
from .telegram import kick_chat_member, restrict_chat_member, unban_chat_member

# Enable logging
logger = logging.getLogger(__name__)


def add_detected_user(gid: int, uid: int, now: int) -> bool:
    # Add or update a detected user's status
    try:
        if not init_user_id(uid):
            return False

        previous = glovar.user_ids[uid]["failed"].get(gid)
        glovar.user_ids[uid]["failed"][gid] = now

        return bool(previous)
    except Exception as e:
        logger.warning(f"Add detected user error: {e}", exc_info=True)

    return False


def ban_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Ban a user
    try:
        thread(kick_chat_member, (client, gid, uid))

        return True
    except Exception as e:
        logger.warning(f"Ban user error: {e}", exc_info=True)

    return False


def change_member_status(client: Client, gid: int, uid: int) -> str:
    # Chat member's status in the group
    try:
        if glovar.configs[gid].get("restrict"):
            restrict_user(client, gid, uid)
            glovar.user_ids[uid]["restrict"].add(gid)
            return "restrict"

        if glovar.configs[gid].get("ban"):
            ban_user(client, gid, uid)
            glovar.user_ids[uid]["ban"].add(gid)
            return "ban"

        kick_user(client, gid, uid)
    except Exception as e:
        logger.warning(f"Change member status: {e}", exc_info=True)

    return "kick"


def kick_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Kick a user
    try:
        kick_chat_member(client, gid, uid)
        sleep(3)
        unban_chat_member(client, gid, uid)

        return True
    except Exception as e:
        logger.warning(f"Kick user error: {e}", exc_info=True)

    return False


def restrict_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Restrict a user
    try:
        thread(restrict_chat_member, (client, gid, uid, ChatPermissions()))

        return True
    except Exception as e:
        logger.warning(f"Restrict user error: {e}", exc_info=True)

    return False


def terminate_user(client: Client, the_type: str, uid: int, gid: int = 0, mid: int = 0) -> bool:
    # Terminate the user
    try:
        if the_type == "delete" and mid:
            delete_message(client, gid, mid)
            declare_message(client, gid, mid)

        elif the_type == "punish":
            change_member_status(client, gid, uid)

        elif the_type == "succeed":
            pass
    except Exception as e:
        logger.warning(f"Terminate user error: {e}", exc_info=True)

    return False


def unban_user(client: Client, gid: int, uid: int) -> bool:
    # Unban a user
    try:
        thread(unban_chat_member, (client, gid, uid))

        return True
    except Exception as e:
        logger.warning(f"Unban user error: {e}", exc_info=True)

    return False


def unrestrict_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Unrestrict a user
    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_send_polls=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        thread(restrict_chat_member, (client, gid, uid, permissions))

        return True
    except Exception as e:
        logger.warning(f"Unrestrict user error: {e}", exc_info=True)

    return False
