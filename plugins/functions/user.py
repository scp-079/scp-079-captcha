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
from time import sleep
from typing import Union

from pyrogram import ChatPermissions, Client, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.api.types import User

from .. import glovar
from .channel import ask_for_help, ask_help_welcome, declare_message, send_debug, share_data, update_score
from .decorators import threaded
from .etc import code, delay, get_now, get_readable_time, lang, mention_text, thread
from .file import data_to_file, file_tsv, save
from .group import delete_hint, delete_message
from .telegram import edit_message_photo, edit_message_text, get_user_full, kick_chat_member
from .telegram import restrict_chat_member, unban_chat_member

# Enable logging
logger = logging.getLogger(__name__)


@threaded()
def ban_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Ban a user
    result = False

    try:
        result = kick_chat_member(client, gid, uid)
    except Exception as e:
        logger.warning(f"Ban user error: {e}", exc_info=True)

    return result


def change_member_status(client: Client, level: str, gid: int, uid: int, record: bool = False) -> bool:
    # Chat member's status in the group
    result = False

    try:
        if level not in {"ban", "restrict", "kick"}:
            return False

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

        result = True
    except Exception as e:
        logger.warning(f"Change member status: {e}", exc_info=True)

    return result


def check_timeout_user(client: Client, uid: int, now: int) -> bool:
    # Check timeout user
    result = False

    try:
        if not glovar.user_ids[uid]["wait"]:
            return False

        for gid in list(glovar.user_ids[uid]["wait"]):
            time = glovar.user_ids[uid]["wait"][gid]

            if not time or now - time <= glovar.time_captcha:
                continue

            terminate_user_timeout(
                client=client,
                uid=uid,
                gid=gid
            )

        result = True
    except Exception as e:
        logger.warning(f"Check timeout user error: {e}", exc_info=True)

    return result


@threaded()
def failed_user(client: Client, uid: int, reason: str) -> bool:
    # Log failed user info
    result = False

    glovar.locks["failed"].acquire()

    try:
        if not glovar.failed:
            return False

        if reason == "remove":
            glovar.failed_ids.pop(uid, {})
            save("failed_ids")
            return True

        if glovar.failed_ids.get(uid):
            return False

        user_full = get_user_full(client, uid)
        user: User = user_full.user

        if not user_full:
            return False

        glovar.failed_ids[uid] = {
            "username": bool(user.username),
            "first": user.first_name,
            "last": user.last_name,
            "bio": user_full.about,
            "reason": reason
        }
        save("failed_ids")

        result = True
    except Exception as e:
        logger.warning(f"Failed user error: {e}", exc_info=True)
    finally:
        glovar.locks["failed"].release()

    return result


def flood_end(client: Client, gid: int) -> bool:
    # Flood end, terminate users
    result = False

    try:
        if not glovar.flood_logs.get(gid, []):
            return False

        kick_list = set()

        for user in glovar.flood_logs[gid]:
            uid = user["user id"]
            action = user["action"]

            if action != "log":
                continue

            kick_list.add(uid)

        # Ask help to kick users
        file = data_to_file(kick_list)
        share_data(
            client=client,
            receivers=["USER"],
            action="help",
            action_type="kick",
            data=gid,
            file=file
        )

        # Send report
        first_line = list(glovar.flood_logs[gid][0])
        lines = [[user.get(key) for key in first_line] for user in glovar.flood_logs[gid]]
        file = file_tsv(
            first_line=first_line,
            lines=lines
        )
        result = send_debug(
            client=client,
            gids=[gid],
            action=lang(f"action_report"),
            file=file
        )
    except Exception as e:
        logger.warning(f"Flood end error: {e}", exc_info=True)

    return result


def flood_user(gid: int, uid: int, time: int, action: str, mid: int = 0, aid: int = 0) -> bool:
    # Log the flood user
    result = False

    try:
        if not glovar.pinned_ids[gid]["start"]:
            return False

        if glovar.flood_logs.get(gid) is None:
            glovar.flood_logs[gid] = []

        glovar.flood_logs[gid].append(
            {
                "user id": uid,
                "time": get_readable_time(time),
                "action": action,
                "message id": mid,
                "admin id": aid
            }
        )
        save("flood_logs")

        result = True
    except Exception as e:
        logger.warning(f"Flood user error: {e}", exc_info=True)

    return result


def forgive_user(client: Client, uid: int) -> bool:
    # Forgive the user
    result = False

    try:
        # Pass in all waiting groups
        for gid in list(glovar.user_ids[uid]["wait"]):
            unrestrict_user(client, gid, uid)

        # Unban in all punished groups
        for gid in set(glovar.user_ids[uid]["banned"]) | set(glovar.user_ids[uid]["restricted"]):
            unban_user(client, gid, uid)

        # Remove users from CAPTCHA group
        time = glovar.user_ids[uid]["time"]
        time and kick_user(client, glovar.captcha_group_id, uid)
        mid = glovar.user_ids[uid]["mid"]
        mid and delete_message(client, glovar.captcha_group_id, mid)

        result = True
    except Exception as e:
        logger.warning(f"Forgive user error: {e}", exc_info=True)

    return result


def forgive_users(client: Client) -> bool:
    # Forgive all users
    result = False

    try:
        result = bool([forgive_user(client, uid) for uid in list(glovar.user_ids)])
    except Exception as e:
        logger.warning(f"Forgive users error: {e}", exc_info=True)

    return result


def get_level(gid: int) -> str:
    # Get level
    result = "kick"

    try:
        if glovar.configs[gid].get("restrict"):
            return "restrict"

        if glovar.configs[gid].get("ban"):
            return "ban"
    except Exception as e:
        logger.warning(f"Get level status: {e}", exc_info=True)

    return result


@threaded()
def kick_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Kick a user
    result = False

    try:
        kick_chat_member(client, gid, uid)
        sleep(3)
        unban_chat_member(client, gid, uid)
        result = True
    except Exception as e:
        logger.warning(f"Kick user error: {e}", exc_info=True)

    return result


def lift_ban(client: Client, uid: int, now: int) -> bool:
    # Lift ban from the users
    result = False

    try:
        group_list = list(glovar.user_ids[uid]["failed"])

        for gid in group_list:
            time = glovar.user_ids[uid]["failed"][gid]

            if not time or now - time <= glovar.time_punish:
                continue

            glovar.user_ids[uid]["failed"][gid] = 0
            unban_user(client, gid, uid)

        result = True
    except Exception as e:
        logger.warning(f"Lift ban error: {e}", exc_info=True)

    return result


def remove_captcha_group(client: Client, uid: int) -> bool:
    # Remove user from captcha group
    result = False

    glovar.locks["message"].acquire()

    try:
        if not glovar.user_ids.get(uid, {}):
            return False

        if glovar.user_ids[uid]["mid"]:
            return False

        time = glovar.user_ids[uid]["time"]

        if not time:
            return False

        glovar.user_ids[uid]["time"] = 0
        save("user_ids")
        kick_user(client, glovar.captcha_group_id, uid)

        result = True
    except Exception as e:
        logger.warning(f"Remove captcha group error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


def remove_failed_user(uid: int) -> bool:
    # Remove failed user
    result = False

    glovar.locks["failed"].acquire()

    try:
        glovar.failed_ids.pop(uid, {})
        save("failed_ids")
    except Exception as e:
        logger.warning(f"Remove failed user error: {e}", exc_info=True)
    finally:
        glovar.locks["failed"].release()

    return result


def remove_group_user(client: Client, uid: int, now: int) -> bool:
    # Remove a user from the CAPTCHA group
    result = False

    try:
        time = glovar.user_ids[uid]["time"]

        if not time or now - time <= glovar.time_remove:
            return False

        glovar.user_ids[uid]["time"] = 0
        result = kick_user(client, glovar.captcha_group_id, uid)
    except Exception as e:
        logger.warning(f"Remove group user error: {e}", exc_info=True)

    return result


def remove_new_users() -> bool:
    # Remove new users
    result = False

    try:
        for uid in list(glovar.user_ids):
            glovar.user_ids[uid]["join"] = {}

        result = True
    except Exception as e:
        logger.warning(f"Remove new users error: {e}", exc_info=True)

    return result


def remove_wait_user(client: Client, uid: int) -> bool:
    # Remove the user from wait list
    result = False

    glovar.locks["message"].acquire()

    try:
        if not glovar.user_ids.get(uid, {}):
            return False

        # Clear the user's wait status
        for gid in list(glovar.user_ids[uid]["wait"]):
            level = get_level(gid)
            change_member_status(client, level, gid, uid, True)
            glovar.user_ids[uid]["failed"][gid] = 0

        glovar.user_ids[uid]["wait"] and delete_hint(client)
        glovar.user_ids[uid]["wait"] = {}
        save("user_ids")

        result = True
    except Exception as e:
        logger.warning(f"Remove wait user error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


@threaded()
def restrict_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Restrict a user
    result = False

    try:
        if uid in glovar.bad_ids["users"]:
            return True

        result = restrict_chat_member(client, gid, uid, ChatPermissions())
    except Exception as e:
        logger.warning(f"Restrict user error: {e}", exc_info=True)

    return result


def terminate_user_banned(client: Client, uid: int, gid: int = 0) -> bool:
    # Banned in group
    result = False

    try:
        # Check the user's status in that group
        failed = glovar.user_ids[uid]["wait"].pop(gid, 0)
        failed and delete_hint(client)
        glovar.user_ids[uid]["manual"].discard(gid)

        # Reset all groups' success records
        for gid in glovar.user_ids[uid]["succeeded"]:
            glovar.user_ids[uid]["succeeded"][gid] = 0

        # Save the data
        save("user_ids")

        # Collect data
        name = glovar.user_ids[uid]["name"]
        mid = glovar.user_ids[uid]["mid"]

        # Check if the group is the only waiting group
        if glovar.user_ids[uid]["wait"] or not glovar.user_ids[uid]["mid"]:
            return save("user_ids")

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
        save("user_ids")

        # Remove from CAPTCHA group
        delay(10, remove_captcha_group, [client, uid])

        result = failed_user(client, uid, "banned")
    except Exception as e:
        logger.warning(f"Terminate user banned error: {e}", exc_info=True)

    return result


def terminate_user_delete(client: Client, gid: int = 0, mid: int = 0) -> bool:
    # Delete the message
    result = False

    try:
        if not mid:
            return False

        delete_message(client, gid, mid)
        declare_message(client, gid, mid)

        result = True
    except Exception as e:
        logger.warning(f"Terminate user delete error: {e}", exc_info=True)

    return result


def terminate_user_pass(client: Client, uid: int, gid: int = 0, aid: int = 0) -> bool:
    # Pass in group
    result = False

    try:
        # Basic data
        now = get_now()

        # Modify the status
        glovar.user_ids[uid]["pass"][gid] = now
        glovar.user_ids[uid]["wait"].pop(gid, 0)
        unrestrict_user(client, gid, uid)
        glovar.user_ids[uid]["failed"].pop(gid, 0)
        glovar.user_ids[uid]["restricted"].discard(gid)

        # Lift ban
        banned_group = gid in glovar.user_ids[uid]["banned"]
        banned_group and glovar.user_ids[uid]["banned"].discard(gid)
        banned_group and unban_user(client, gid, uid)

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
        failed_user(client, uid, "remove")

        # Save the data
        save("user_ids")

        # Collect data
        name = glovar.user_ids[uid]["name"]
        mid = glovar.user_ids[uid]["mid"]

        # Check if the group is the only waiting group
        if glovar.user_ids[uid]["wait"] or not glovar.user_ids[uid]["mid"]:
            return True

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
        save("user_ids")

        # Remove from CAPTCHA group
        delay(10, remove_captcha_group, [client, uid])

        result = True
    except Exception as e:
        logger.warning(f"Terminate user pass error: {e}", exc_info=True)

    return result


def terminate_user_punish(client: Client, uid: int, gid: int = 0) -> bool:
    # User under punishment
    result = False

    try:
        level = get_level(gid)
        result = change_member_status(client, level, gid, uid)
    except Exception as e:
        logger.warning(f"Terminate user punish error: {e}", exc_info=True)

    return result


def terminate_user_succeed(client: Client, uid: int) -> bool:
    # Verification succeed
    result = False

    try:
        # Basic data
        now = get_now()

        # Pass in all waiting groups
        wait_group_list = list(glovar.user_ids[uid]["wait"])

        for gid in wait_group_list:
            unrestrict_user(client, gid, uid)

        # Forgive in all failed groups
        failed_group_list = list(glovar.user_ids[uid]["failed"])

        for gid in failed_group_list:
            if not glovar.configs[gid].get("forgive"):
                continue

            unban_user(client, gid, uid)
            glovar.user_ids[uid]["failed"][gid] = 0

        # Unrestrict in all restricted groups
        restricted_group_list = list(glovar.user_ids[uid]["restricted"])

        for gid in restricted_group_list:
            if not glovar.configs[gid].get("forgive"):
                continue

            unrestrict_user(client, gid, uid)
            glovar.user_ids[uid]["restricted"].discard(gid)

        # Unban in all banned groups
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

        # Delete the hint
        delete_hint(client)

        # Remove from CAPTCHA group
        delay(60, remove_captcha_group, [client, uid])

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
        failed_user(client, uid, "remove")

        # Collect data
        name = glovar.user_ids[uid]["name"]
        mid = glovar.user_ids[uid]["mid"]

        # Reset message id
        glovar.user_ids[uid]["mid"] = 0
        save("user_ids")

        if not mid:
            return True

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

        result = True
    except Exception as e:
        logger.warning(f"Terminate user succeed error: {e}", exc_info=True)

    return result


def terminate_user_timeout(client: Client, uid: int, gid: int = 0) -> bool:
    # Verification timeout
    result = False

    try:
        # Basic data
        now = get_now()

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

        # Collect data
        name = glovar.user_ids[uid]["name"]
        mid = glovar.user_ids[uid]["mid"]

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

        # Add failed user
        failed_user(client, uid, "timeout")

        if not mid:
            return True

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

        result = True
    except Exception as e:
        logger.warning(f"Terminate user timeout error: {e}", exc_info=True)

    return result


def terminate_user_undo_pass(client: Client, uid: int, gid: int = 0, aid: int = 0) -> bool:
    # Undo pass in group
    result = False

    try:
        # Basic data
        now = get_now()

        # Reset status
        glovar.user_ids[uid]["pass"].pop(gid, 0)
        save("user_ids")

        # Update the score
        update_score(client, uid)

        # Send debug message
        result = send_debug(
            client=client,
            gids=[gid],
            action=lang("action_undo_pass"),
            uid=uid,
            aid=aid,
            time=now
        )
    except Exception as e:
        logger.warning(f"Terminate undo pass error: {e}", exc_info=True)

    return result


def terminate_user_wrong(client: Client, uid: int) -> bool:
    # Verification Wrong
    result = False

    try:
        # Basic data
        now = get_now()

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

        # Collect data
        name = glovar.user_ids[uid]["name"]
        mid = glovar.user_ids[uid]["mid"]

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

        # Add failed user
        failed_user(client, uid, "timeout")

        if not mid:
            return True

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

        result = True
    except Exception as e:
        logger.warning(f"Terminate user wrong error: {e}", exc_info=True)

    return result


@threaded()
def unban_user(client: Client, gid: int, uid: int) -> bool:
    # Unban a user
    result = False

    try:
        result = unban_chat_member(client, gid, uid)
    except Exception as e:
        logger.warning(f"Unban user error: {e}", exc_info=True)

    return result


@threaded()
def unrestrict_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Unrestrict a user
    result = False

    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_stickers=True,
            can_send_animations=True,
            can_send_games=True,
            can_use_inline_bots=True,
            can_add_web_page_previews=True,
            can_send_polls=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        result = restrict_chat_member(client, gid, uid, permissions)
    except Exception as e:
        logger.warning(f"Unrestrict user error: {e}", exc_info=True)

    return result
