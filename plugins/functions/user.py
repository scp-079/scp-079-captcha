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
from typing import Dict, Iterable, Union

from pyrogram import ChatPermissions, Client, InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.api.types import User

from .. import glovar
from .channel import ask_for_help, ask_help_welcome, declare_message, send_debug, share_data, update_score
from .command import get_command_type
from .decorators import threaded
from .etc import code, delay, get_int, get_now, get_readable_time, get_text, lang, mention_text, random_str, thread
from .file import data_to_file, file_tsv, save
from .filters import is_class_d_user, is_flooded, is_from_user, is_should_qns
from .group import delete_hint, delete_message
from .ids import init_user_id
from .telegram import answer_callback, edit_message_photo, edit_message_text, get_messages, get_user_full
from .telegram import kick_chat_member, resolve_username, restrict_chat_member, unban_chat_member

# Enable logging
logger = logging.getLogger(__name__)


def add_start(until: int, cid: int, uid: int, action: str) -> str:
    # Add start
    result = ""

    try:
        key = random_str(8)

        while glovar.starts.get(key):
            key = random_str(8)

        glovar.starts[key] = {
            "until": until,
            "cid": cid,
            "uid": uid,
            "action": action
        }
        save("starts")

        result = key
    except Exception as e:
        logger.warning(f"Add start error: {e}", exc_info=True)

    return result


@threaded()
def ban_user(client: Client, gid: int, uid: Union[int, str], lock: bool = False) -> bool:
    # Ban a user
    result = False

    lock and glovar.locks["ban"].acquire()

    try:
        result = kick_chat_member(client, gid, uid)
    except Exception as e:
        logger.warning(f"Ban user error: {e}", exc_info=True)
    finally:
        lock and glovar.locks["ban"].release()

    return result


def change_member_status(client: Client, level: str, gid: int, uid: int,
                         record: bool = False, lock: bool = False) -> bool:
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
            ban_user(client, gid, uid, lock)
            record and glovar.user_ids[uid]["banned"].add(gid) and save("user_ids")

        result = True
    except Exception as e:
        logger.warning(f"Change member status: {e}", exc_info=True)

    return result


def check_timeout_user(client: Client, uid: int, now: int) -> bool:
    # Check timeout user
    result = False

    try:
        # Check user waiting status
        if not glovar.user_ids[uid]["wait"]:
            return False

        # Check regular timeout
        for gid in list(glovar.user_ids[uid]["wait"]):
            time = glovar.user_ids[uid]["wait"][gid]
            qns = glovar.user_ids[uid]["qns"].get(gid, "")

            if not time:
                continue

            if qns and is_should_qns(gid):
                continue

            if now - time <= glovar.time_captcha:
                continue

            terminate_user_timeout(
                client=client,
                uid=uid
            )
            break

        # Check qns timeout
        for gid in list(glovar.user_ids[uid]["wait"]):
            time = glovar.user_ids[uid]["wait"][gid]
            qns = glovar.user_ids[uid]["qns"].get(gid, "")

            if not time:
                continue

            if not qns or not is_should_qns(gid):
                continue

            if now - time <= ((glovar.time_captcha // 2) or 30):
                continue

            terminate_user_timeout_qns(
                client=client,
                gid=gid,
                uid=uid
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


@threaded()
def flood_end(client: Client, gid: int, manual: bool = False) -> bool:
    # Flood end, terminate users
    result = False

    glovar.locks["flood"].acquire()

    try:
        if not glovar.flood_logs.get(gid, []) and manual:
            glovar.flood_logs[gid] = []
        elif not glovar.flood_logs.get(gid, []):
            return False

        # Ask help to kick users
        kick_list = set()

        for user in glovar.flood_logs[gid]:
            uid = user["user id"]
            reason = user["reason"]

            if reason != "log":
                continue

            kick_list.add(uid)

        file = data_to_file(kick_list)
        share_data(
            client=client,
            receivers=["USER"],
            action="help",
            action_type="kick",
            data={
                "group_id": gid,
                "manual": manual
            },
            file=file
        )

        # Ask help to clear messages
        delete_list = set()

        for user in glovar.flood_logs[gid]:
            if manual:
                continue

            uid = user["user id"]
            reason = user["reason"]

            if reason not in {"timeout", "wrong"}:
                continue

            delete_list.add(uid)

        file = data_to_file(delete_list)
        not manual and share_data(
            client=client,
            receivers=["USER"],
            action="flood",
            action_type="delete",
            data=gid,
            file=file
        )

        # Share flood users score
        users: Dict[int, float] = {}

        for user in glovar.flood_logs[gid]:
            if manual:
                continue

            uid = user["user id"]
            reason = user["reason"]

            if reason not in {"timeout", "wrong"}:
                continue

            if not init_user_id(uid):
                continue

            pass_count = len(glovar.user_ids[uid]["pass"])
            succeeded_count = len(glovar.user_ids[uid]["succeeded"])
            failed_count = len(glovar.user_ids[uid]["failed"])
            score = pass_count * -0.2 + succeeded_count * -0.3 + failed_count * 0.6
            glovar.user_ids[uid]["score"][glovar.sender.lower()] = score

            users[uid] = score

        save("user_ids")
        file = data_to_file(users)
        not manual and share_data(
            client=client,
            receivers=glovar.receivers["score"],
            action="flood",
            action_type="score",
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

        # Reset flood logs
        glovar.flood_logs.pop(gid, [])
        save("flood_logs")

        # Share flood end status
        share_data(
            client=client,
            receivers=glovar.receivers["flood"],
            action="flood",
            action_type="status",
            data={
                "group_id": gid,
                "status": "end"
            }
        )
    except Exception as e:
        logger.warning(f"Flood end error: {e}", exc_info=True)
    finally:
        glovar.locks["flood"].release()

    return result


def flood_user(gid: int, uid: int, time: int, action: str, reason: str = None,
               mid: int = None, aid: int = None) -> bool:
    # Log the flood user
    result = False

    glovar.locks["flood"].acquire()

    try:
        if glovar.flood_logs.get(gid) is None:
            glovar.flood_logs[gid] = []

        glovar.flood_logs[gid].append(
            {
                "user id": uid,
                "time": get_readable_time(time),
                "action": action,
                "reason": reason,
                "message id": mid,
                "admin id": aid
            }
        )
        save("flood_logs")

        result = True
    except Exception as e:
        logger.warning(f"Flood user error: {e}", exc_info=True)
    finally:
        glovar.locks["flood"].release()

    return result


def forgive_user(client: Client, uid: int, failed: bool = False) -> bool:
    # Forgive the user
    result = False

    try:
        # Pass in all waiting groups
        for gid in list(glovar.user_ids[uid]["wait"]):
            unrestrict_user(client, gid, uid, lock=True)

        # Unban in all punished groups
        failed_set = {gid for gid in list(glovar.user_ids[uid]["failed"]) if glovar.user_ids[uid]["failed"][gid]}

        if failed:
            group_list = failed_set
        else:
            group_list = set(glovar.user_ids[uid]["banned"]) | set(glovar.user_ids[uid]["restricted"]) | failed_set

        for gid in group_list:
            unban_user(client, gid, uid, lock=True)

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
        result = bool([forgive_user(client, uid, True) for uid in list(glovar.user_ids)])
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


def get_uid(client: Client, message: Message) -> int:
    # Get user id from the message
    result = 0

    try:
        # Basic data
        r_msg = message.reply_to_message

        # Get the user id
        if r_msg and is_from_user(None, r_msg):
            result = get_uid_from_reply(client, r_msg)
        else:
            result = get_uid_from_command(client, message)
    except Exception as e:
        logger.warning(f"Get uid error: {e}", exc_info=True)

    return result


def get_uid_from_command(client: Client, message: Message) -> int:
    # Get user id from message command
    result = 0

    try:
        # Basic data
        text = get_command_type(message)

        # ID text
        result = get_int(text)

        if result and result > 0:
            return result

        # Username text
        peer_type, result = resolve_username(client, text)

        if peer_type == "user":
            return result

        # Mention text
        result = get_uid_from_mention(message)
    except Exception as e:
        logger.warning(f"Get uid from command error: {e}", exc_info=True)

    return result


def get_uid_from_mention(message: Message) -> int:
    # Get user id from mention
    result = 0

    try:
        if not message.entities:
            return 0

        valid = [en.user for en in message.entities if en.user]

        if not valid:
            return 0

        result = valid[0].id
    except Exception as e:
        logger.warning(f"Get uid from mention error: {e}", exc_info=True)

    return result


def get_uid_from_reply(client: Client, message: Message) -> int:
    # Get user id from the replied to message
    result = 0

    try:
        # Basic data
        cid = message.chat.id
        mid = message.message_id

        # Get the message
        message = get_messages(client, cid, mid)

        if not message:
            return 0

        # Further
        if message.reply_to_message:
            return get_uid_from_reply(client, message.reply_to_message)

        # Get the uid
        if message.from_user.is_self:
            result = get_uid_from_self(message)
        elif message.new_chat_members:
            result = message.new_chat_members[0].id
        else:
            result = message.from_user.id
    except Exception as e:
        logger.warning(f"Get uid from reply error: {e}", exc_info=True)

    return result


def get_uid_from_self(message: Message) -> int:
    # Get user id from self
    result = 0

    try:
        result = get_uid_from_text(message)

        if result:
            return result

        result = get_uid_from_mention(message)
    except Exception as e:
        logger.warning(f"Get uid from self error: {e}", exc_info=True)

    return result


def get_uid_from_text(message: Message) -> int:
    # Get user id from message text
    result = 0

    try:
        # Basic data
        message_text = get_text(message)

        # Get the uid
        text_list = [text for text in message_text.split("\n")
                     if text.startswith(f"{lang('user_id')}{lang('colon')}")
                     or text.startswith(f"{lang('wait_user')}{lang('colon')}")]

        if not text_list:
            return 0

        result = get_int(text_list[0].split(lang("colon"))[1])
    except Exception as e:
        logger.warning(f"Get uid from text error: {e}", exc_info=True)

    return result


@threaded()
def kick_user(client: Client, gid: int, uid: Union[int, str], until_date: int = 0, lock: bool = False) -> bool:
    # Kick a user
    result = False

    lock and glovar.locks["ban"].acquire()

    try:
        if until_date:
            return kick_chat_member(client, gid, uid, until_date)

        kick_chat_member(client, gid, uid)
        sleep(3)
        unban_chat_member(client, gid, uid)

        result = True
    except Exception as e:
        logger.warning(f"Kick user error: {e}", exc_info=True)
    finally:
        lock and glovar.locks["ban"].release()

    return result


@threaded()
def kick_users(client: Client, gid: int, uids: Iterable[int]) -> bool:
    # Kick users
    result = False

    try:
        if not uids:
            return False

        for uid in uids:
            now = get_now()
            kick_chat_member(client, gid, uid, now + 600)

        result = True
    except Exception as e:
        logger.warning(f"Kick users error: {e}", exc_info=True)

    return result


def lift_ban(client: Client, uid: int, now: int) -> bool:
    # Lift ban from the users
    result = False

    try:
        group_list = list(glovar.user_ids[uid]["failed"])

        for gid in group_list:
            if is_flooded(gid):
                continue

            time = glovar.user_ids[uid]["failed"][gid]

            if not time or now - time <= glovar.time_punish:
                continue

            glovar.user_ids[uid]["failed"][gid] = 0
            unban_user(client, gid, uid, lock=True)

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


@threaded()
def remove_failed_user(uid: int) -> bool:
    # Remove failed user
    result = False

    glovar.locks["failed"].acquire()

    try:
        glovar.failed_ids.pop(uid, {})
        save("failed_ids")
        result = True
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


@threaded()
def remove_wait_user(client: Client, uid: int) -> bool:
    # Remove the user from wait list
    result = False

    glovar.locks["message"].acquire()

    try:
        if not glovar.user_ids.get(uid, {}):
            return False

        # Get the group list
        wait_group_list = list(glovar.user_ids[uid]["wait"])

        if not wait_group_list:
            return False

        # Clear the user's wait status
        for gid in wait_group_list:
            if gid in glovar.ignore_ids["user"]:
                continue

            level = get_level(gid)
            delay(3, change_member_status, [client, level, gid, uid, True])
            glovar.user_ids[uid]["wait"].pop(gid, 0)
            glovar.user_ids[uid]["qns"].pop(gid, "")
            glovar.user_ids[uid]["manual"].discard(gid)
            glovar.user_ids[uid]["failed"][gid] = 0

        # Delete hint
        not all(is_flooded(gid) for gid in wait_group_list) and delete_hint(client)
        save("user_ids")

        # Check the groups
        if glovar.user_ids[uid]["wait"]:
            return True

        # Reset status
        glovar.user_ids[uid]["answer"] = ""
        glovar.user_ids[uid]["limit"] = 0
        glovar.user_ids[uid]["try"] = 0
        save("user_ids")

        # Collect data
        name = glovar.user_ids[uid]["name"]
        mid = glovar.user_ids[uid]["mid"]

        # Reset message id
        glovar.user_ids[uid]["mid"] = 0
        save("user_ids")

        # Remove from CAPTCHA group
        delay(10, remove_captcha_group, [client, uid])

        if not mid:
            return True

        # Get the captcha status text
        text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                f"{lang('description')}{lang('colon')}{code(lang('description_bad'))}\n")

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
        logger.warning(f"Remove wait user error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


@threaded()
def restrict_user(client: Client, gid: int, uid: Union[int, str]) -> bool:
    # Restrict a user
    result = False

    try:
        if uid in glovar.bad_ids["users"] and gid not in glovar.ignore_ids["user"]:
            return True

        result = restrict_chat_member(client, gid, uid, ChatPermissions())
    except Exception as e:
        logger.warning(f"Restrict user error: {e}", exc_info=True)

    return result


def terminate_user_banned(client: Client, uid: int, gid: int) -> bool:
    # Banned in group
    result = False

    try:
        # Check the user's status in that group
        failed = glovar.user_ids[uid]["wait"].pop(gid, 0)
        glovar.user_ids[uid]["qns"].pop(gid, "")
        glovar.user_ids[uid]["manual"].discard(gid)

        # Delete hint
        failed and not is_flooded(gid) and delete_hint(client)

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


def terminate_user_delete(client: Client, gid: int, mid: int) -> bool:
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


def terminate_user_pass(client: Client, uid: int, gid: int, aid: int) -> bool:
    # Pass in group
    result = False

    try:
        # Basic data
        now = get_now()

        # Modify the status
        glovar.user_ids[uid]["pass"][gid] = now
        waiting = glovar.user_ids[uid]["wait"].pop(gid, 0)
        glovar.user_ids[uid]["qns"].pop(gid, "")
        glovar.user_ids[uid]["failed"].pop(gid, 0)
        glovar.user_ids[uid]["banned"].discard(gid)
        glovar.user_ids[uid]["restricted"].discard(gid)

        # Unban the user
        unban_user(client, gid, uid)

        # Delete the hint
        waiting and not is_flooded(gid) and delete_hint(client)

        # Ask help welcome
        if gid not in glovar.user_ids[uid]["manual"]:
            waiting and ask_help_welcome(client, uid, [gid])
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
        wait_group_list = list(g for g in glovar.user_ids[uid]["wait"] if not is_should_qns(g))

        for gid in wait_group_list:
            unrestrict_user(client, gid, uid)

        # Forgive in all failed groups
        failed_group_list = list(glovar.user_ids[uid]["failed"])

        for gid in failed_group_list:
            if is_class_d_user(uid):
                continue

            if not glovar.configs[gid].get("forgive"):
                continue

            unban_user(client, gid, uid)
            glovar.user_ids[uid]["failed"][gid] = 0

        # Unrestrict in all restricted groups
        restricted_group_list = list(glovar.user_ids[uid]["restricted"])

        for gid in restricted_group_list:
            if is_class_d_user(uid):
                continue

            if not glovar.configs[gid].get("forgive"):
                continue

            unrestrict_user(client, gid, uid)
            glovar.user_ids[uid]["restricted"].discard(gid)

        # Unban in all banned groups
        banned_group_list = list(glovar.user_ids[uid]["banned"])

        for gid in banned_group_list:
            if is_class_d_user(uid):
                continue

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
            [glovar.user_ids[uid]["wait"].pop(g, 0) for g in wait_group_list]
            glovar.user_ids[uid]["succeeded"][gid] = now

        # Delete the hint
        not all(is_flooded(gid) for gid in wait_group_list) and delete_hint(client)

        # Remove from CAPTCHA group
        delay(60, remove_captcha_group, [client, uid])

        # Ask help welcome
        welcome_ids = [wid for wid in wait_group_list if wid not in glovar.user_ids[uid]["manual"]]
        glovar.user_ids[uid]["manual"] -= set(wait_group_list)
        save("user_ids")
        ask_help_welcome(client, uid, welcome_ids)

        # Update the score
        not any(is_flooded(gid) for gid in wait_group_list) and update_score(client, uid)

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


def terminate_user_succeed_qns(client: Client, gid: int, uid: int, qid: str) -> bool:
    # Qns verification succeed
    result = False

    try:
        # Basic data
        now = get_now()

        # Pass in the group
        unrestrict_user(client, gid, uid)

        # Modify the status
        glovar.user_ids[uid]["wait"].pop(gid, 0)
        glovar.user_ids[uid]["failed"].pop(gid, 0)
        glovar.user_ids[uid]["restricted"].discard(gid)
        glovar.user_ids[uid]["banned"].discard(gid)
        save("user_ids")

        # Delete the hint
        not is_flooded(gid) and delete_hint(client)

        # Ask help welcome
        gid not in glovar.user_ids[uid]["manual"] and ask_help_welcome(client, uid, [gid])
        glovar.user_ids[uid]["manual"].discard(gid)
        save("user_ids")

        # Send debug message
        send_debug(
            client=client,
            gids=[gid],
            action=lang("action_verified"),
            uid=uid,
            time=now
        )

        # Answer the callback
        thread(answer_callback, (client, qid, lang("action_verified"), True))

        result = True
    except Exception as e:
        logger.warning(f"Terminate user succeed qns error: {e}", exc_info=True)

    return result


def terminate_user_timeout(client: Client, uid: int) -> bool:
    # Verification timeout
    result = False

    try:
        # Basic data
        now = get_now()

        # Get the group list
        wait_group_list = list(g for g in glovar.user_ids[uid]["wait"] if not is_should_qns(g))

        # Modify the status
        glovar.user_ids[uid]["answer"] = ""
        glovar.user_ids[uid]["limit"] = 0
        glovar.user_ids[uid]["try"] = 0

        for gid in wait_group_list:
            # Decide level
            if glovar.user_ids[uid]["failed"].get(gid) is not None:
                level = "ban"
            else:
                level = get_level(gid)

            # Limit the user
            change_member_status(client, level, gid, uid, lock=any(is_flooded(g) for g in wait_group_list))
            not is_flooded(gid) and ask_for_help(client, "delete", gid, uid)

            # Modify the status
            glovar.user_ids[uid]["wait"].pop(gid, 0)
            glovar.user_ids[uid]["manual"].discard(gid)

            if glovar.user_ids[uid]["succeeded"].get(gid, 0):
                glovar.user_ids[uid]["succeeded"][gid] = 0

            # Decide the unban pending
            if level in {"ban", "restrict"}:
                glovar.user_ids[uid]["failed"][gid] = 0
            else:
                glovar.user_ids[uid]["failed"][gid] = now

            # Flood log
            is_flooded(gid) and flood_user(gid, uid, now, level, "timeout")

            # Send debug message
            not is_flooded(gid) and send_debug(
                client=client,
                gids=[gid],
                action=lang(f"auto_{level}"),
                uid=uid,
                time=now,
                more=lang("description_timeout")
            )

        # Collect data
        name = glovar.user_ids[uid]["name"]
        mid = glovar.user_ids[uid]["mid"]

        # Reset message id
        glovar.user_ids[uid]["mid"] = 0
        save("user_ids")

        # Remove from CAPTCHA group
        delay(10, remove_captcha_group, [client, uid])

        # Update the score
        not any(is_flooded(gid) for gid in wait_group_list) and update_score(client, uid)

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


def terminate_user_timeout_qns(client: Client, gid: int, uid: int) -> bool:
    # Qns verification timeout
    result = False

    try:
        # Basic data
        now = get_now()

        # Modify the status
        glovar.user_ids[uid]["wait"].pop(gid, 0)
        glovar.user_ids[uid]["qns"].pop(gid, "")
        glovar.user_ids[uid]["manual"].discard(gid)
        glovar.user_ids[uid]["failed"].pop(gid, 0)
        glovar.user_ids[uid]["restricted"].discard(gid)
        glovar.user_ids[uid]["banned"].discard(gid)
        save("user_ids")

        # Get the level
        level = get_level(gid)

        # Kick the user (ban for 86400 seconds) or ban the user
        if level == "kick":
            kick_user(client, gid, uid, until_date=now + 86400, lock=True)
        elif level == "ban":
            ban_user(client, gid, uid)

        # Delete all messages from the user
        not is_flooded(gid) and ask_for_help(client, "delete", gid, uid)

        # Flood log
        is_flooded(gid) and flood_user(gid, uid, now, level, "timeout")

        # Send debug message
        not is_flooded(gid) and send_debug(
            client=client,
            gids=[gid],
            action=lang(f"auto_{level}"),
            uid=uid,
            time=now,
            more=lang("description_timeout")
        )

        result = True
    except Exception as e:
        logger.warning(f"Terminate user timeout qns error: {e}", exc_info=True)

    return result


def terminate_user_undo_pass(client: Client, uid: int, gid: int, aid: int) -> bool:
    # Undo pass in group
    result = False

    try:
        # Basic data
        now = get_now()

        # Reset status
        glovar.user_ids[uid]["pass"].pop(gid, 0)
        save("user_ids")

        # Update the score
        not is_flooded(gid) and update_score(client, uid)

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
        wait_group_list = list(g for g in glovar.user_ids[uid]["wait"] if not is_should_qns(g))

        # Modify the status
        glovar.user_ids[uid]["answer"] = ""
        glovar.user_ids[uid]["limit"] = 0
        glovar.user_ids[uid]["try"] = 0

        # Kick the user
        for gid in wait_group_list:
            # Ban the user temporarily
            ban_user(client, gid, uid)
            not is_flooded(gid) and ask_for_help(client, "delete", gid, uid)

            # Modify the status
            glovar.user_ids[uid]["wait"].pop(gid, 0)
            glovar.user_ids[uid]["manual"].discard(gid)

            # Give the user one more chance
            glovar.user_ids[uid]["failed"][gid] = now
            glovar.user_ids[uid]["restricted"].discard(gid)
            glovar.user_ids[uid]["banned"].discard(gid)

            # Flood log
            is_flooded(gid) and flood_user(gid, uid, now, "kick", "wrong")

        # Collect data
        name = glovar.user_ids[uid]["name"]
        mid = glovar.user_ids[uid]["mid"]

        # Reset message id
        glovar.user_ids[uid]["mid"] = 0
        save("user_ids")

        # Delete the hint
        not all(is_flooded(gid) for gid in wait_group_list) and delete_hint(client)

        # Remove from CAPTCHA group
        delay(15, remove_captcha_group, [client, uid])

        # Update the score
        not any(is_flooded(gid) for gid in wait_group_list) and update_score(client, uid)

        # Send debug message
        send_debug(
            client=client,
            gids=[gid for gid in wait_group_list if not is_flooded(gid)],
            action=lang(f"auto_kick"),
            uid=uid,
            time=now,
            more=lang("description_wrong")
        )

        # Add failed user
        failed_user(client, uid, "wrong")

        if not mid:
            return True

        # Get the captcha status text
        suggestion = lang("suggestion_wrong").format(glovar.time_punish)
        text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                f"{lang('description')}{lang('colon')}{code(lang('description_wrong'))}\n"
                f"{lang('suggestion')}{lang('colon')}{code(suggestion)}\n")

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


def terminate_user_wrong_qns(client: Client, gid: int, uid: int, qid: str) -> bool:
    # Qns verification wrong
    result = False

    try:
        # Basic data
        now = get_now()

        # Modify the status
        glovar.user_ids[uid]["wait"].pop(gid, 0)
        glovar.user_ids[uid]["qns"].pop(gid, "")
        glovar.user_ids[uid]["manual"].discard(gid)
        glovar.user_ids[uid]["failed"].pop(gid, 0)
        glovar.user_ids[uid]["restricted"].discard(gid)
        glovar.user_ids[uid]["banned"].discard(gid)
        save("user_ids")

        # Get the level
        level = get_level(gid)

        # Kick the user (ban for 3600 seconds) or ban the user
        if level == "kick":
            kick_user(client, gid, uid, until_date=now + 3600, lock=True)
        elif level == "ban":
            ban_user(client, gid, uid)

        # Delete all messages from the user
        not is_flooded(gid) and ask_for_help(client, "delete", gid, uid)

        # Flood log
        is_flooded(gid) and flood_user(gid, uid, now, "kick", "wrong")

        # Delete the hint
        not is_flooded(gid) and delete_hint(client)

        # Send debug message
        not is_flooded(gid) and send_debug(
            client=client,
            gids=[gid],
            action=lang(f"auto_{level}"),
            uid=uid,
            time=now,
            more=lang("description_wrong")
        )

        # Answer the callback
        thread(answer_callback, (client, qid, lang("description_wrong"), True))

        result = True
    except Exception as e:
        logger.warning(f"Terminate user wrong qns error: {e}", exc_info=True)

    return result


@threaded()
def unban_user(client: Client, gid: int, uid: int, lock: bool = False) -> bool:
    # Unban a user
    result = False

    lock and glovar.locks["ban"].acquire()

    try:
        result = unban_chat_member(client, gid, uid)
    except Exception as e:
        logger.warning(f"Unban user error: {e}", exc_info=True)
    finally:
        lock and glovar.locks["ban"].release()

    return result


@threaded()
def unrestrict_user(client: Client, gid: int, uid: Union[int, str], lock: bool = False) -> bool:
    # Unrestrict a user
    result = False

    lock and glovar.locks["ban"].acquire()

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
    finally:
        lock and glovar.locks["ban"].release()

    return result
