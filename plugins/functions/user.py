# SCP-079-CAPTCHA - Provide challenges for new joined members
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
from time import sleep
from typing import Union

from pyrogram import ChatPermissions, Client, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.api.types import User

from .. import glovar
from .channel import ask_for_help, ask_help_welcome, declare_message, send_debug, share_data, update_score
from .etc import code, delay, get_now, lang, mention_text, thread
from .file import save
from .group import delete_hint, delete_message
from .telegram import edit_message_photo, edit_message_text, get_user_full, kick_chat_member
from .telegram import restrict_chat_member, unban_chat_member

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


def failed_user(client: Client, uid: int, reason: str) -> bool:
    # Log failed user info
    glovar.locks["failed"].acquire()
    try:
        if not glovar.failed:
            return True

        if glovar.failed_ids.get(uid):
            return True

        user_full = get_user_full(client, uid)
        user: User = user_full.user

        if not user_full:
            return True

        glovar.failed_ids[uid] = {
            "username": bool(user.username),
            "first": user.first_name,
            "last": user.last_name,
            "bio": user_full.about,
            "reason": reason
        }
        save("failed_ids")

        return True
    except Exception as e:
        logger.warning(f"Failed user error: {e}", exc_info=True)
    finally:
        glovar.locks["failed"].release()

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


def log_user(client: Client, gid: int, uid: int) -> bool:
    # Log kick a user
    try:
        # Ask user to kick the user
        share_data(
            client=client,
            receivers=["USER"],
            action="help",
            action_type="kick",
            data={
                "group_id": gid,
                "user_id": uid
            }
        )

        # Send debug message
        send_debug(
            client=client,
            gids=[gid],
            action=lang(f"auto_kick"),
            uid=uid,
            more=lang("description_log")
        )
    except Exception as e:
        logger.warning(f"Log user error: {e}", exc_info=True)

    return False


def remove_captcha_group(client: Client, uid: int) -> bool:
    # Remove user from captcha group
    glovar.locks["message"].acquire()
    try:
        if not glovar.user_ids.get(uid, {}):
            return True

        if glovar.user_ids[uid]["mid"]:
            return True

        time = glovar.user_ids[uid]["time"]

        if not time:
            return True

        glovar.user_ids[uid]["time"] = 0
        save("user_ids")
        kick_user(client, glovar.captcha_group_id, uid)

        return True
    except Exception as e:
        logger.warning(f"Remove captcha group error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

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

        # Banned in group
        if the_type == "banned":
            failed = glovar.user_ids[uid]["wait"].pop(gid, 0)
            glovar.user_ids[uid]["manual"].discard(gid)

            for gid in glovar.user_ids[uid]["succeeded"]:
                glovar.user_ids[uid]["succeeded"][gid] = 0

            # Edit the message
            if not glovar.user_ids[uid]["wait"] and glovar.user_ids[uid]["mid"]:
                name = glovar.user_ids[uid]["name"]
                mid = glovar.user_ids[uid]["mid"]

                # Get the captcha status text
                text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                        f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                        f"{lang('description')}{lang('colon')}{code(lang('description_banned'))}\n")

                # Edit the message
                question_type = glovar.user_ids[uid]["type"]

                if question_type in glovar.question_types["image"]:
                    thread(
                        target=edit_message_photo,
                        args=(client, glovar.captcha_group_id, mid, "assets/fail.png", None, text)
                    )
                elif question_type in glovar.question_types["text"]:
                    thread(
                        target=edit_message_text,
                        args=(client, glovar.captcha_group_id, mid, text)
                    )

                # Reset message id
                glovar.user_ids[uid]["mid"] = 0

                # Remove from CAPTCHA group
                delay(10, remove_captcha_group, [client, uid])

            save("user_ids")

            # Delete the hint
            delete_hint(client)

            # Check failed status
            if not failed:
                return True

        # Delete the message
        elif the_type == "delete" and mid:
            delete_message(client, gid, mid)
            declare_message(client, gid, mid)

        # Pass in group
        elif the_type == "pass":
            # Modify the status
            glovar.user_ids[uid]["pass"][gid] = now
            glovar.user_ids[uid]["wait"].pop(gid, 0)
            unrestrict_user(client, gid, uid)
            glovar.user_ids[uid]["failed"].pop(gid, 0)
            glovar.user_ids[uid]["restricted"].discard(gid)

            if gid in glovar.user_ids[uid]["banned"]:
                glovar.user_ids[uid]["banned"].discard(gid)
                unban_user(client, gid, uid)

            # Edit the message
            if not glovar.user_ids[uid]["wait"] and glovar.user_ids[uid]["mid"]:
                name = glovar.user_ids[uid]["name"]
                mid = glovar.user_ids[uid]["mid"]

                # Get the captcha status text
                text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                        f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                        f"{lang('description')}{lang('colon')}{code(lang('description_pass'))}\n")

                # Edit the message
                question_type = glovar.user_ids[uid]["type"]

                if question_type in glovar.question_types["image"]:
                    thread(
                        target=edit_message_photo,
                        args=(client, glovar.captcha_group_id, mid, "assets/succeed.png", None, text)
                    )
                elif question_type in glovar.question_types["text"]:
                    thread(
                        target=edit_message_text,
                        args=(client, glovar.captcha_group_id, mid, text)
                    )

                # Reset message id
                glovar.user_ids[uid]["mid"] = 0

                # Remove from CAPTCHA group
                delay(10, remove_captcha_group, [client, uid])

            save("user_ids")

            # Delete the hint
            delete_hint(client)

            # Ask help welcome
            if gid not in glovar.user_ids[uid]["manual"]:
                ask_help_welcome(client, uid, [gid])
            else:
                glovar.user_ids[uid]["manual"].discard(gid)
                save("user_ids")

            # Update the score
            update_score(client, uid)

            # Send debug message
            send_debug(
                client=client,
                gids=[gid],
                action=lang("action_pass"),
                uid=uid,
                aid=aid,
                time=now
            )

            # Remove failed status
            with glovar.locks["failed"]:
                glovar.failed_ids.pop(uid, {})
                save("failed_ids")

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
                if not glovar.configs[gid].get("forgive"):
                    continue

                unban_user(client, gid, uid)
                glovar.user_ids[uid]["failed"][gid] = 0

            restricted_group_list = list(glovar.user_ids[uid]["restricted"])

            for gid in restricted_group_list:
                if not glovar.configs[gid].get("forgive"):
                    continue

                unrestrict_user(client, gid, uid)
                glovar.user_ids[uid]["restricted"].discard(gid)

            banned_group_list = list(glovar.user_ids[uid]["banned"])

            for gid in banned_group_list:
                if not glovar.configs[gid].get("forgive"):
                    continue

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
                text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                        f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                        f"{lang('description')}{lang('colon')}{code(lang('description_succeed'))}\n")

                # Get the captcha status markup
                if glovar.more:
                    markup = InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    text=glovar.more_text,
                                    url=glovar.more_link
                                )
                            ]
                        ]
                    )
                else:
                    markup = None

                # Edit the message
                question_type = glovar.user_ids[uid]["type"]

                if question_type in glovar.question_types["image"]:
                    thread(
                        target=edit_message_photo,
                        args=(client, glovar.captcha_group_id, mid, "assets/succeed.png", None, text, markup)
                    )
                elif question_type in glovar.question_types["text"]:
                    thread(
                        target=edit_message_text,
                        args=(client, glovar.captcha_group_id, mid, text, markup)
                    )

            # Reset message id
            glovar.user_ids[uid]["mid"] = 0
            save("user_ids")

            # Delete the hint
            delete_hint(client)

            # Remove from CAPTCHA group
            delay(30, remove_captcha_group, [client, uid])

            # Ask help welcome
            welcome_ids = [wid for wid in wait_group_list if wid not in glovar.user_ids[uid]["manual"]]
            glovar.user_ids[uid]["manual"] = set()
            save("user_ids")
            ask_help_welcome(client, uid, welcome_ids)

            # Update the score
            update_score(client, uid)

            # Send debug message
            send_debug(
                client=client,
                gids=wait_group_list,
                action=lang("action_verified"),
                uid=uid,
                time=now
            )

            # Remove failed status
            with glovar.locks["failed"]:
                glovar.failed_ids.pop(uid, {})
                save("failed_ids")

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
            glovar.user_ids[uid]["manual"].discard(gid)

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
                text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                        f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                        f"{lang('description')}{lang('colon')}{code(lang('description_timeout'))}\n")

                # Edit the message
                question_type = glovar.user_ids[uid]["type"]

                if question_type in glovar.question_types["image"]:
                    thread(
                        target=edit_message_photo,
                        args=(client, glovar.captcha_group_id, mid, "assets/fail.png", None, text)
                    )
                elif question_type in glovar.question_types["text"]:
                    thread(
                        target=edit_message_text,
                        args=(client, glovar.captcha_group_id, mid, text)
                    )

            # Reset message id
            glovar.user_ids[uid]["mid"] = 0
            save("user_ids")

            # Remove from CAPTCHA group
            delay(10, remove_captcha_group, [client, uid])

            # Update the score
            update_score(client, uid)

            # Send debug message
            send_debug(
                client=client,
                gids=[gid],
                action=lang(f"auto_{level}"),
                uid=uid,
                time=now,
                more=lang("description_timeout")
            )

        # Pass in group
        elif the_type == "undo_pass":
            glovar.user_ids[uid]["pass"].pop(gid, 0)
            save("user_ids")

            # Update the score
            update_score(client, uid)

            # Send debug message
            send_debug(
                client=client,
                gids=[gid],
                action=lang("action_undo_pass"),
                uid=uid,
                aid=aid,
                time=now
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
            glovar.user_ids[uid]["manual"] = set()

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
                text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                        f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                        f"{lang('description')}{lang('colon')}{code(lang('description_wrong'))}\n"
                        f"{lang('suggestion')}{lang('colon')}{code(lang('suggestion_wrong'))}\n")

                # Edit the message
                question_type = glovar.user_ids[uid]["type"]

                if question_type in glovar.question_types["image"]:
                    thread(
                        target=edit_message_photo,
                        args=(client, glovar.captcha_group_id, mid, "assets/fail.png", None, text)
                    )
                elif question_type in glovar.question_types["text"]:
                    thread(
                        target=edit_message_text,
                        args=(client, glovar.captcha_group_id, mid, text)
                    )

            # Reset message id
            glovar.user_ids[uid]["mid"] = 0
            save("user_ids")

            # Delete the hint
            delete_hint(client)

            # Remove from CAPTCHA group
            delay(15, remove_captcha_group, [client, uid])

            # Update the score
            update_score(client, uid)

            # Send debug message
            send_debug(
                client=client,
                gids=wait_group_list,
                action=lang(f"auto_kick"),
                uid=uid,
                time=now,
                more=lang("description_wrong")
            )

        # Failed reason
        if the_type in {"banned", "timeout", "wrong"}:
            thread(failed_user, (client, uid, the_type))

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
