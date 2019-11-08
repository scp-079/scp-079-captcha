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
from .channel import ask_for_help, declare_message, send_debug, update_score
from .etc import code, get_now, lang, mention_text, thread
from .file import save
from .group import delete_message
from .telegram import edit_message_photo, edit_message_text, kick_chat_member, restrict_chat_member, unban_chat_member

# Enable logging
logger = logging.getLogger(__name__)


def ban_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Ban a user
    try:
        thread(kick_chat_member, (client, gid, uid))

        return True
    except Exception as e:
        logger.warning(f"Ban user error: {e}", exc_info=True)

    return False


def change_member_status(client: Client, level: str, gid: int, uid: int, record: bool = False) -> bool:
    # Chat member's status in the group
    try:
        if level == "ban":
            glovar.user_ids[uid]["banned"].add(gid)
            save("user_ids")
            ban_user(client, gid, uid)
        elif level == "restrict":
            glovar.user_ids[uid]["restricted"].add(gid)
            save("user_ids")
            restrict_user(client, gid, uid)
        elif level == "kick":
            ban_user(client, gid, uid)
            record and glovar.user_ids[uid]["banned"].add(gid) and save("user_ids")

        return True
    except Exception as e:
        logger.warning(f"Change member status: {e}", exc_info=True)

    return False


def get_level(gid: int) -> str:
    # Get level
    try:
        if glovar.configs[gid].get("restrict"):
            return "restrict"

        if glovar.configs[gid].get("ban"):
            return "ban"
    except Exception as e:
        logger.warning(f"Get level status: {e}", exc_info=True)

    return "kick"


def kick_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Kick a user
    try:
        thread(kick_user_thread, (client, gid, uid))

        return True
    except Exception as e:
        logger.warning(f"Kick user error: {e}", exc_info=True)

    return False


def kick_user_thread(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Kick a user thread
    try:
        kick_chat_member(client, gid, uid)
        sleep(3)
        unban_chat_member(client, gid, uid)

        return True
    except Exception as e:
        logger.warning(f"Kick user thread error: {e}", exc_info=True)

    return False


def restrict_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Restrict a user
    try:
        if uid in glovar.bad_ids["users"]:
            return True

        thread(restrict_chat_member, (client, gid, uid, ChatPermissions()))

        return True
    except Exception as e:
        logger.warning(f"Restrict user error: {e}", exc_info=True)

    return False


def terminate_user(client: Client, the_type: str, uid: int, gid: int = 0, mid: int = 0, aid: int = 0) -> bool:
    # Terminate the user
    try:
        # Basic data
        now = get_now()

        # Delete the message
        if the_type == "delete" and mid:
            delete_message(client, gid, mid)
            declare_message(client, gid, mid)

        # Pass in group
        elif the_type == "pass":
            glovar.user_ids[uid]["wait"].pop(gid, 0)
            unrestrict_user(client, gid, uid)
            glovar.user_ids[uid]["failed"].pop(gid, 0)
            glovar.user_ids[uid]["restricted"].discard(gid)

            if gid in glovar.user_ids[uid]["banned"]:
                glovar.user_ids[uid]["banned"].discard(gid)
                unban_user(client, gid, uid)

            save("user_ids")

            send_debug(
                client=client,
                gids=[gid],
                action=lang("action_pass"),
                uid=uid,
                aid=aid
            )

        # User under punishment
        elif the_type == "punish":
            level = get_level(gid)
            change_member_status(client, level, gid, uid)

        # Verification succeed
        elif the_type == "succeed":
            wait_group_list = list(glovar.user_ids[uid]["wait"])
            for gid in wait_group_list:
                unrestrict_user(client, gid, uid)

            failed_group_list = list(glovar.user_ids[uid]["failed"])
            for gid in failed_group_list:
                if glovar.configs[gid].get("forgive"):
                    unban_user(client, gid, uid)
                    glovar.user_ids[uid]["failed"][gid] = 0

            restricted_group_list = list(glovar.user_ids[uid]["restricted"])
            for gid in restricted_group_list:
                if glovar.configs[gid].get("forgive"):
                    unrestrict_user(client, gid, uid)
                    glovar.user_ids[uid]["restricted"].discard(gid)

            banned_group_list = list(glovar.user_ids[uid]["banned"])
            for gid in banned_group_list:
                if glovar.configs[gid].get("forgive"):
                    unban_user(client, gid, uid)
                    glovar.user_ids[uid]["banned"].discard(gid)

            # Modify the status
            glovar.user_ids[uid]["answer"] = ""
            glovar.user_ids[uid]["limit"] = 0
            glovar.user_ids[uid]["try"] = 0
            if glovar.user_ids[uid]["wait"]:
                gid = min(glovar.user_ids[uid]["wait"], key=glovar.user_ids[uid]["wait"].get)
                glovar.user_ids[uid]["wait"] = {}
                glovar.user_ids[uid]["succeeded"][gid] = now

            # Edit the message
            name = glovar.user_ids[uid]["name"]
            mid = glovar.user_ids[uid]["mid"]
            if mid:
                # Get the captcha status text
                captcha_text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                                f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                                f"{lang('description')}{lang('colon')}{code(lang('description_succeed'))}\n")

                # Edit the message
                question_type = glovar.user_ids[uid]["type"]
                if question_type in glovar.question_types["image"]:
                    thread(
                        target=edit_message_photo,
                        args=(client, glovar.captcha_group_id, mid, "assets/succeed.png", None, captcha_text)
                    )
                elif question_type in glovar.question_types["text"]:
                    thread(
                        target=edit_message_text,
                        args=(client, glovar.captcha_group_id, mid, captcha_text)
                    )

            # Reset message id
            glovar.user_ids[uid]["mid"] = 0
            save("user_ids")

            # Update the score
            update_score(client, uid)

            send_debug(
                client=client,
                gids=wait_group_list,
                action=lang("action_verified"),
                uid=uid
            )

        # Verification timeout
        elif the_type == "timeout":
            # Decide level
            if glovar.user_ids[uid]["failed"].get(gid) is not None:
                level = "ban"
            else:
                level = get_level(gid)

            # Limit the user
            change_member_status(client, level, gid, uid)
            ask_for_help(client, "delete", gid, uid)

            # Modify the status
            glovar.user_ids[uid]["answer"] = ""
            glovar.user_ids[uid]["limit"] = 0
            glovar.user_ids[uid]["try"] = 0
            glovar.user_ids[uid]["wait"].pop(gid, 0)
            if glovar.user_ids[uid]["succeeded"].get(gid, 0):
                glovar.user_ids[uid]["succeeded"][gid] = 0

            # Decide the unban pending
            if level in {"ban", "restrict"}:
                glovar.user_ids[uid]["failed"][gid] = 0
            else:
                glovar.user_ids[uid]["failed"][gid] = now

            # Edit the message
            name = glovar.user_ids[uid]["name"]
            mid = glovar.user_ids[uid]["mid"]
            if mid:
                # Get the captcha status text
                captcha_text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                                f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                                f"{lang('description')}{lang('colon')}{code(lang('description_timeout'))}\n")

                # Edit the message
                question_type = glovar.user_ids[uid]["type"]
                if question_type in glovar.question_types["image"]:
                    thread(
                        target=edit_message_photo,
                        args=(client, glovar.captcha_group_id, mid, "assets/fail.png", None, captcha_text)
                    )
                elif question_type in glovar.question_types["text"]:
                    thread(
                        target=edit_message_text,
                        args=(client, glovar.captcha_group_id, mid, captcha_text)
                    )

            # Reset message id
            glovar.user_ids[uid]["mid"] = 0
            save("user_ids")

            # Update the score
            update_score(client, uid)

            # Send debug message
            send_debug(
                client=client,
                gids=[gid],
                action=lang(f"auto_{level}"),
                uid=uid,
                more=lang("description_timeout")
            )

        # Pass in group
        elif the_type == "undo_pass":
            glovar.user_ids[uid]["pass"].pop(gid, 0)
            save("user_ids")

            send_debug(
                client=client,
                gids=[gid],
                action=lang("action_undo_pass"),
                uid=uid,
                aid=aid
            )

        # Verification Wrong
        elif the_type == "wrong":
            # Get the group list
            wait_group_list = list(glovar.user_ids[uid]["wait"])

            # Kick the user
            for gid in wait_group_list:
                ban_user(client, gid, uid)
                ask_for_help(client, "delete", gid, uid)

            # Modify the status
            glovar.user_ids[uid]["answer"] = ""
            glovar.user_ids[uid]["limit"] = 0
            glovar.user_ids[uid]["try"] = 0
            glovar.user_ids[uid]["wait"] = {}

            # Give the user one more chance
            for gid in wait_group_list:
                glovar.user_ids[uid]["failed"][gid] = now
                glovar.user_ids[uid]["restricted"].discard(gid)
                glovar.user_ids[uid]["banned"].discard(gid)
                if glovar.user_ids[uid]["succeeded"].get(gid, 0):
                    glovar.user_ids[uid]["succeeded"][gid] = 0

            # Edit the message
            name = glovar.user_ids[uid]["name"]
            mid = glovar.user_ids[uid]["mid"]
            if mid:
                # Get the captcha status text
                captcha_text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                                f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                                f"{lang('description')}{lang('colon')}{code(lang('description_wrong'))}\n"
                                f"{lang('suggestion')}{lang('colon')}{code(lang('suggestion_wrong'))}\n")

                # Edit the message
                question_type = glovar.user_ids[uid]["type"]
                if question_type in glovar.question_types["image"]:
                    thread(
                        target=edit_message_photo,
                        args=(client, glovar.captcha_group_id, mid, "assets/fail.png", None, captcha_text)
                    )
                elif question_type in glovar.question_types["text"]:
                    thread(
                        target=edit_message_text,
                        args=(client, glovar.captcha_group_id, mid, captcha_text)
                    )

            # Reset message id
            glovar.user_ids[uid]["mid"] = 0
            save("user_ids")

            # Update the score
            update_score(client, uid)

            # Send debug message
            send_debug(
                client=client,
                gids=wait_group_list,
                action=lang(f"auto_kick"),
                uid=uid,
                more=lang("description_wrong")
            )

        return True
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
