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
from typing import List, Optional

from pyrogram import Chat, ChatMember, Client, Message, User

from .. import glovar
from .decorators import threaded
from .etc import code, get_now, get_text_user, lang, mention_name, thread
from .file import save
from .telegram import delete_messages, get_chat, get_messages, leave_chat

# Enable logging
logger = logging.getLogger(__name__)


@threaded()
def clear_joined_messages(client: Client, gid: int, mid: int) -> bool:
    # Clear joined messages
    result = False

    try:
        if mid - glovar.limit_flood * 4 > 0:
            mids = range(mid - glovar.limit_flood * 4, mid + 1)
        else:
            mids = range(1, mid + 1)

        for mid in mids:
            message = get_messages(client, gid, mid)

            if not message or not message.service:
                continue

            delete_message(client, gid, mid)

        result = True
    except Exception as e:
        logger.warning(f"Clear joined message error: {e}", exc_info=True)

    return result


def delete_hint(client: Client) -> bool:
    # Delete hint messages
    result = False

    try:
        # Basic data
        now = get_now()

        # Get the wait group list
        wait_group_list = {gid for uid in list(glovar.user_ids) for gid in list(glovar.user_ids[uid]["wait"])}

        # Proceed
        for gid in list(glovar.message_ids):
            # Regular hint
            mid = glovar.message_ids[gid]["hint"]

            if mid and gid not in wait_group_list:
                glovar.message_ids[gid]["hint"] = 0
                delete_message(client, gid, mid)

            # Flood static hint
            mids = glovar.message_ids[gid]["flood"]

            if mids and gid not in wait_group_list:
                glovar.message_ids[gid]["flood"] = set()
                thread(delete_messages, (client, gid, mids))

            # Manual hint
            if not glovar.message_ids[gid].get("manual", {}):
                glovar.message_ids[gid]["manual"] = {}

            for mid in list(glovar.message_ids[gid]["manual"]):
                time = glovar.message_ids[gid]["manual"][mid]

                if now - time < glovar.time_captcha:
                    continue

                glovar.message_ids[gid]["nospam"].pop(mid, 0)
                delete_message(client, gid, mid)

            # NOSPAM hint
            if not glovar.message_ids[gid].get("nospam", {}):
                glovar.message_ids[gid]["nospam"] = {}

            for mid in list(glovar.message_ids[gid]["nospam"]):
                time = glovar.message_ids[gid]["nospam"][mid]

                if now - time < glovar.time_captcha:
                    continue

                glovar.message_ids[gid]["nospam"].pop(mid, 0)
                delete_message(client, gid, mid)

        # Save the data
        save("message_ids")

        result = True
    except Exception as e:
        logger.warning(f"Delete hint error: {e}", exc_info=True)

    return result


@threaded()
def delete_message(client: Client, gid: int, mid: int) -> bool:
    # Delete a single message
    result = False

    try:
        if not gid or not mid:
            return True

        mids = [mid]
        result = delete_messages(client, gid, mids)
    except Exception as e:
        logger.warning(f"Delete message error: {e}", exc_info=True)

    return result


def get_group(client: Client, gid: int, cache: bool = True) -> Optional[Chat]:
    # Get the group
    result = None

    try:
        the_cache = glovar.chats.get(gid)

        if cache and the_cache:
            return the_cache

        result = get_chat(client, gid)

        if not result:
            return result

        glovar.chats[gid] = result
    except Exception as e:
        logger.warning(f"Get group error: {e}", exc_info=True)

    return result


def get_hint_text(gid: int, the_type: str, user: User = None) -> str:
    # Get the group's hint text
    result = ""

    try:
        custom_text = glovar.custom_texts[gid].get(the_type, "")

        if custom_text:
            return get_text_user(custom_text, user)

        if the_type == "flood":
            result = (f"{lang('auto_fix')}{lang('colon')}{code(lang('pin'))}\n"
                      f"{lang('reason')}{lang('colon')}{code(lang('action_flood'))}\n")
            description = lang("description_hint").format(glovar.time_captcha)
        elif the_type == "manual":
            result = (f"{lang('user_name')}{lang('colon')}{mention_name(user)}\n"
                      f"{lang('user_id')}{lang('colon')}{code(user.id)}\n")
            description = lang("description_manual").format(glovar.time_captcha)
        elif the_type == "nospam":
            result = (f"{lang('user_name')}{lang('colon')}{mention_name(user)}\n"
                      f"{lang('user_id')}{lang('colon')}{code(user.id)}\n")
            description = lang("description_nospam").format(glovar.time_captcha)
        elif the_type == "single":
            result = (f"{lang('user_name')}{lang('colon')}{mention_name(user)}\n"
                      f"{lang('user_id')}{lang('colon')}{code(user.id)}\n")
            description = lang("description_single").format(glovar.time_captcha)
        elif the_type == "static":
            description = lang("description_hint").format(glovar.time_captcha)
        else:
            description = ""

        result += f"{lang('description')}{lang('colon')}{code(description)}\n"
    except Exception as e:
        logger.warning(f"Get hint text error: {e}", exc_info=True)

    return result


def get_pinned(client: Client, gid: int, cache: bool = True) -> Optional[Message]:
    # Get group's pinned message
    result = None

    try:
        group = get_group(client, gid, cache)

        if not group or not group.pinned_message:
            return None

        result = group.pinned_message
    except Exception as e:
        logger.warning(f"Get pinned error: {e}", exc_info=True)

    return result


def leave_group(client: Client, gid: int) -> bool:
    # Leave a group, clear it's data
    result = False

    try:
        glovar.left_group_ids.add(gid)
        save("left_group_ids")
        thread(leave_chat, (client, gid))

        glovar.lack_group_ids.discard(gid)
        save("lack_group_ids")

        glovar.admin_ids.pop(gid, set())
        save("admin_ids")

        glovar.message_ids.pop(gid, {})
        save("message_ids")

        glovar.pinned_ids.pop(gid, {})
        save("pinned_ids")

        glovar.trust_ids.pop(gid, set())
        save("trust_ids")

        glovar.configs.pop(gid, {})
        save("configs")

        glovar.custom_texts.pop(gid, {})
        save("custom_texts")

        glovar.declared_message_ids.pop(gid, set())

        result = True
    except Exception as e:
        logger.warning(f"Leave group error: {e}", exc_info=True)

    return result


def save_admins(gid: int, admin_members: List[ChatMember]) -> bool:
    # Save the group's admin list
    result = False

    try:
        # Admin list
        glovar.admin_ids[gid] = {admin.user.id for admin in admin_members
                                 if (((not admin.user.is_bot and not admin.user.is_deleted)
                                      and admin.can_delete_messages
                                      and admin.can_restrict_members)
                                     or admin.status == "creator"
                                     or admin.user.id in glovar.bot_ids)}
        save("admin_ids")

        # Trust list
        glovar.trust_ids[gid] = {admin.user.id for admin in admin_members
                                 if ((not admin.user.is_bot and not admin.user.is_deleted)
                                     or admin.user.id in glovar.bot_ids)}
        save("trust_ids")

        result = True
    except Exception as e:
        logger.warning(f"Save admins error: {e}", exc_info=True)

    return result
