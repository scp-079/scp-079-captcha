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
from copy import deepcopy
from json import loads
from typing import Any

from pyrogram import Client, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .. import glovar
from .captcha import user_captcha
from .channel import get_debug_text, send_debug, share_data
from .config import get_config_text
from .decorators import threaded
from .etc import code, crypt_str, general_link, get_int, get_now, get_text, lang, thread, mention_id
from .file import crypt_file, data_to_file, delete_file, get_new_path, get_downloaded_path, save
from .filters import is_class_e_user, is_should_ignore
from .group import leave_group
from .ids import init_group_id, init_user_id
from .telegram import get_chat_member, get_members, kick_chat_member, send_message, send_report_message
from .timers import update_admins
from .user import flood_end, flood_user, forgive_user, forgive_users, kick_user, remove_failed_user, remove_new_users
from .user import remove_wait_user, terminate_user_banned

# Enable logging
logger = logging.getLogger(__name__)


def receive_add_bad(client: Client, data: dict) -> bool:
    # Receive bad objects that other bots shared
    result = False

    try:
        # Basic data
        the_id = data["id"]
        the_type = data["type"]

        # Receive bad user
        if the_type != "user":
            return False

        glovar.bad_ids["users"].add(the_id)
        save("bad_ids")

        remove_wait_user(client, the_id)
        remove_failed_user(the_id)

        result = True
    except Exception as e:
        logger.warning(f"Receive add bad error: {e}", exc_info=True)

    return result


@threaded()
def receive_check_log(client: Client, message: Message, data: dict) -> bool:
    # Receive check log
    result = False

    try:
        # Basic data
        gid = data["group_id"]
        begin = data["begin"]
        end = data["end"]
        manual = data["manual"]
        now = get_now()
        count = 0

        # Get users
        users = receive_file_data(client, message)

        if users is None:
            users = set()

        # Log the users
        log_users = deepcopy(users)
        manual and logger.warning(f"Log users {len(log_users)}")
        members = get_members(client, gid)
        member_count = 0

        for member in members:
            member_count += 1
            uid = member.user.id

            if uid not in log_users and not begin < member.joined_date < end:
                continue

            if is_should_ignore(gid, uid):
                continue

            if is_class_e_user(uid):
                continue

            with glovar.locks["message"]:
                user_status = glovar.user_ids.get(member.user.id)

            if (user_status
                    and any(gid in user_status[the_type] for the_type in ["failed", "pass", "wait", "succeeded"])):
                continue

            if manual:
                kick_chat_member(client, gid, member.user.id, True)
                flood_user(gid, member.user.id, now, "ban", "check")
                logger.warning(f"Banned {member.user.id} in {gid}")
            else:
                kick_user(client, gid, member.user.id)
                flood_user(gid, member.user.id, now, "kick", "check")

            log_users.discard(member.user.id)
            count += 1

        manual and logger.warning(f"Checked {member_count} members of {gid}")
        manual and logger.warning(f"Count {count}")
        manual and logger.warning(f"Log users {len(log_users)}")

        for uid in log_users:
            if is_should_ignore(gid, uid):
                continue

            if is_class_e_user(uid):
                continue

            with glovar.locks["message"]:
                user_status = glovar.user_ids.get(uid)

            if (user_status
                    and any(gid in user_status[the_type] for the_type in ["failed", "pass", "wait", "succeeded"])):
                continue

            manual and logger.warning(f"Need USER to kick {uid} in {gid}")
            manual and kick_chat_member(client, gid, uid, True, True)
            flood_user(gid, uid, now, (manual and "ban") or "kick", "log")
            count += 1

        manual and logger.warning(f"Count {count}")

        # Send debug message
        send_debug(
            client=client,
            gids=[gid],
            action=lang("action_count"),
            total=len(users),
            count=count
        )

        # Flood end
        result = flood_end(client, gid, manual)
    except Exception as e:
        logger.warning(f"Receive check log error: {e}", exc_info=True)

    return result


def receive_clear_data(client: Client, data_type: str, data: dict) -> bool:
    # Receive clear data command
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        aid = data["admin_id"]
        the_type = data["type"]

        # Clear bad data
        if (data_type == "bad"
                and the_type == "users"):
            glovar.bad_ids["users"] = set()
            save("bad_ids")

        # Clear user data
        elif data_type == "user":
            if the_type == "all":
                forgive_users(client)
                glovar.user_ids = {}
            elif the_type == "new":
                remove_new_users()

            save("user_ids")

        # Clear watch data
        elif data_type == "watch":
            if the_type == "all":
                glovar.watch_ids = {
                    "ban": {},
                    "delete": {}
                }
            elif the_type == "ban":
                glovar.watch_ids["ban"] = {}
            elif the_type == "delete":
                glovar.watch_ids["delete"] = {}

            save("watch_ids")

        # Clear white data
        elif (data_type == "white"
              and the_type == "all"):
            glovar.white_ids = set()
            save("white_ids")

        # Send debug message
        text = (f"{lang('project')}{lang('colon')}{general_link(glovar.project_name, glovar.project_link)}\n"
                f"{lang('admin_project')}{lang('colon')}{mention_id(aid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('clear'))}\n"
                f"{lang('more')}{lang('colon')}{code(f'{data_type} {the_type}')}\n")
        result = thread(send_message, (client, glovar.debug_channel_id, text))
    except Exception as e:
        logger.warning(f"Receive clear data: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


def receive_config_commit(data: dict) -> bool:
    # Receive config commit
    result = False

    try:
        # Basic data
        gid = data["group_id"]
        config = data["config"]

        glovar.configs[gid] = config
        save("configs")

        result = True
    except Exception as e:
        logger.warning(f"Receive config commit error: {e}", exc_info=True)

    return result


def receive_config_reply(client: Client, data: dict) -> bool:
    # Receive config reply
    result = False

    try:
        # Basic data
        gid = data["group_id"]
        uid = data["user_id"]
        link = data["config_link"]

        # Send the report message
        text = (f"{lang('admin')}{lang('colon')}{code(uid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('config_change'))}\n"
                f"{lang('description')}{lang('colon')}{code(lang('config_button'))}\n")
        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=lang("config_go"),
                        url=link
                    )
                ]
            ]
        )
        thread(send_report_message, (60, client, gid, text, None, markup))

        result = True
    except Exception as e:
        logger.warning(f"Receive config reply error: {e}", exc_info=True)

    return result


def receive_config_show(client: Client, data: dict) -> bool:
    # Receive config show request
    result = False

    try:
        # Basic Data
        aid = data["admin_id"]
        mid = data["message_id"]
        gid = data["group_id"]

        # Generate report message's text
        result = (f"{lang('admin')}{lang('colon')}{mention_id(aid)}\n"
                  f"{lang('action')}{lang('colon')}{code(lang('config_show'))}\n"
                  f"{lang('group_id')}{lang('colon')}{code(gid)}\n")

        if glovar.configs.get(gid, {}):
            result += get_config_text(glovar.configs[gid])
        else:
            result += (f"{lang('status')}{lang('colon')}{code(lang('status_failed'))}\n"
                       f"{lang('reason')}{lang('colon')}{code(lang('reason_none'))}\n")

        # Send the text data
        file = data_to_file(result)
        result = share_data(
            client=client,
            receivers=["MANAGE"],
            action="config",
            action_type="show",
            data={
                "admin_id": aid,
                "message_id": mid,
                "group_id": gid
            },
            file=file
        )
    except Exception as e:
        logger.warning(f"Receive config show error: {e}", exc_info=True)

    return result


def receive_declared_message(data: dict) -> bool:
    # Update declared message's id
    result = False

    try:
        # Basic data
        gid = data["group_id"]
        mid = data["message_id"]

        if not glovar.admin_ids.get(gid):
            return True

        if init_group_id(gid):
            glovar.declared_message_ids[gid].add(mid)

        result = True
    except Exception as e:
        logger.warning(f"Receive declared message error: {e}", exc_info=True)

    return result


def receive_file_data(client: Client, message: Message, decrypt: bool = True) -> Any:
    # Receive file's data from exchange channel
    result = None

    try:
        if not message.document:
            return None

        file_id = message.document.file_id
        file_ref = message.document.file_ref
        path = get_downloaded_path(client, file_id, file_ref)

        if not path:
            return None

        if decrypt:
            # Decrypt the file, save to the tmp directory
            path_decrypted = get_new_path()
            crypt_file("decrypt", path, path_decrypted)
            path_final = path_decrypted
        else:
            # Read the file directly
            path_decrypted = ""
            path_final = path

        with open(path_final, "rb") as f:
            result = pickle.load(f)

        for f in {path, path_decrypted}:
            delete_file(f)
    except Exception as e:
        logger.warning(f"Receive file error: {e}", exc_info=True)

    return result


def receive_help_captcha(client: Client, data: dict) -> bool:
    # Receive help captcha
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        gid = data["group_id"]
        uid = data["user_id"]
        mid = data["message_id"]
        now = get_now()

        # Check the group
        if gid not in glovar.admin_ids:
            return True

        # Get the chat member
        member = get_chat_member(client, gid, uid)

        # Check the member
        if not member or not member.user:
            return True

        # CAPTCHA request
        result = user_captcha(
            client=client,
            message=None,
            gid=gid,
            user=member.user,
            mid=mid,
            now=now,
            aid=glovar.nospam_id
        )
    except Exception as e:
        logger.warning(f"Receive help captcha error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


def receive_ignore_ids(client: Client, message: Message, sender: str) -> bool:
    # Receive ignore ids
    result = False

    try:
        data = receive_file_data(client, message)

        if data is None:
            return False

        glovar.ignore_ids[sender.lower()] = data
        save("ignore_ids")

        result = True
    except Exception as e:
        logger.warning(f"Receive ignore ids error: {e}", exc_info=True)

    return result


def receive_leave_approve(client: Client, data: dict) -> bool:
    # Receive leave approve
    result = False

    try:
        # Basic data
        admin_id = data["admin_id"]
        the_id = data["group_id"]
        force = data["force"]
        reason = data["reason"]

        if reason in {"permissions", "user"}:
            reason = lang(f"reason_{reason}")

        if not glovar.admin_ids.get(the_id) and not force:
            return True

        text = get_debug_text(client, the_id)
        text += (f"{lang('admin_project')}{lang('colon')}{mention_id(admin_id)}\n"
                 f"{lang('status')}{lang('colon')}{code(lang('leave_approve'))}\n")

        if reason:
            text += f"{lang('reason')}{lang('colon')}{code(reason)}\n"

        leave_group(client, the_id)
        thread(send_message, (client, glovar.debug_channel_id, text))

        result = True
    except Exception as e:
        logger.warning(f"Receive leave approve error: {e}", exc_info=True)

    return result


def receive_refresh(client: Client, data: int) -> bool:
    # Receive refresh
    result = False

    try:
        # Basic data
        aid = data

        # Update admins
        update_admins(client)

        # Send debug message
        text = (f"{lang('project')}{lang('colon')}{general_link(glovar.project_name, glovar.project_link)}\n"
                f"{lang('admin_project')}{lang('colon')}{mention_id(aid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('refresh'))}\n")
        thread(send_message, (client, glovar.debug_channel_id, text))

        result = True
    except Exception as e:
        logger.warning(f"Receive refresh error: {e}", exc_info=True)

    return result


def receive_regex(client: Client, message: Message, data: str) -> bool:
    # Receive regex
    result = False

    glovar.locks["regex"].acquire()

    try:
        file_name = data
        word_type = file_name.split("_")[0]

        if word_type not in glovar.regex:
            return False

        words_data = receive_file_data(client, message)

        if words_data is None:
            return False

        pop_set = set(eval(f"glovar.{file_name}")) - set(words_data)
        new_set = set(words_data) - set(eval(f"glovar.{file_name}"))

        for word in pop_set:
            eval(f"glovar.{file_name}").pop(word, 0)

        for word in new_set:
            eval(f"glovar.{file_name}")[word] = 0

        save(file_name)

        # Regenerate special characters dictionary if possible
        if file_name not in {"spc_words", "spe_words"}:
            return False

        special = file_name.split("_")[0]
        exec(f"glovar.{special}_dict = {{}}")

        for rule in words_data:
            # Check keys
            if "[" not in rule:
                continue

            # Check value
            if "?#" not in rule:
                continue

            keys = rule.split("]")[0][1:]
            value = rule.split("?#")[1][1]

            for k in keys:
                eval(f"glovar.{special}_dict")[k] = value

        result = True
    except Exception as e:
        logger.warning(f"Receive regex error: {e}", exc_info=True)
    finally:
        glovar.locks["regex"].release()

    return result


def receive_remove_bad(client: Client, data: dict) -> bool:
    # Receive removed bad objects
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        the_id = data["id"]
        the_type = data["type"]

        # Remove bad user
        if the_type != "user":
            return False

        glovar.bad_ids["users"].discard(the_id)
        save("bad_ids")
        glovar.watch_ids["ban"].pop(the_id, {})
        glovar.watch_ids["delete"].pop(the_id, {})
        save("watch_ids")

        if not glovar.user_ids.get(the_id, {}):
            return True

        forgive_user(client, the_id)

        glovar.user_ids[the_id] = deepcopy(glovar.default_user_status)
        save("user_ids")

        result = True
    except Exception as e:
        logger.warning(f"Receive remove bad error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


def receive_remove_score(client: Client, data: int) -> bool:
    # Receive remove user's score
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        uid = data

        if not glovar.user_ids.get(uid, {}):
            return True

        forgive_user(client, uid)

        glovar.user_ids[uid] = deepcopy(glovar.default_user_status)
        save("user_ids")

        result = True
    except Exception as e:
        logger.warning(f"Receive remove score error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


def receive_remove_watch(data: int) -> bool:
    # Receive removed watching users
    result = False

    try:
        # Basic data
        uid = data

        # Reset watch status
        glovar.watch_ids["ban"].pop(uid, 0)
        glovar.watch_ids["delete"].pop(uid, 0)
        save("watch_ids")

        result = True
    except Exception as e:
        logger.warning(f"Receive remove watch error: {e}", exc_info=True)

    return result


def receive_remove_white(data: int) -> bool:
    # Receive removed withe users
    result = False

    try:
        # Basic data
        uid = data

        if not init_user_id(uid):
            return True

        # White ids
        glovar.white_ids.discard(uid)
        save("white_ids")

        result = True
    except Exception as e:
        logger.warning(f"Receive remove white error: {e}", exc_info=True)

    return result


def receive_rollback(client: Client, message: Message, data: dict) -> bool:
    # Receive rollback data
    result = False

    try:
        # Basic data
        aid = data["admin_id"]
        the_type = data["type"]
        the_data = receive_file_data(client, message)

        if the_data is None:
            return False

        exec(f"glovar.{the_type} = the_data")
        save(the_type)

        # Send debug message
        text = (f"{lang('project')}{lang('colon')}{general_link(glovar.project_name, glovar.project_link)}\n"
                f"{lang('admin_project')}{lang('colon')}{mention_id(aid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('rollback'))}\n"
                f"{lang('more')}{lang('colon')}{code(the_type)}\n")
        thread(send_message, (client, glovar.debug_channel_id, text))

        result = True
    except Exception as e:
        logger.warning(f"Receive rollback error: {e}", exc_info=True)

    return result


def receive_text_data(message: Message) -> dict:
    # Receive text's data from exchange channel
    result = {}

    try:
        text = get_text(message)

        if not text:
            return {}

        result = loads(text)
    except Exception as e:
        logger.warning(f"Receive text data error: {e}")

    return result


def receive_user_score(project: str, data: dict) -> bool:
    # Receive and update user's score
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        project = project.lower()
        uid = data["id"]

        if not init_user_id(uid):
            return False

        score = data["score"]
        glovar.user_ids[uid]["score"][project] = score
        save("user_ids")

        result = True
    except Exception as e:
        logger.warning(f"Receive user score error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


def receive_warn_kicked_user(client: Client, data: dict) -> bool:
    # Receive WARN banned user
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        gid = data["group_id"]
        uid = data["user_id"]

        # Clear wait status
        if not glovar.user_ids.get(uid, {}):
            return True

        # Terminate the user
        result = terminate_user_banned(
            client=client,
            uid=uid,
            gid=gid
        )
    except Exception as e:
        logger.warning(f"Receive warn banned user error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


def receive_watch_user(data: dict) -> bool:
    # Receive watch users that other bots shared
    result = False

    try:
        # Basic data
        the_type = data["type"]
        uid = data["id"]
        until = data["until"]

        # Decrypt the data
        until = crypt_str("decrypt", until, glovar.key)
        until = get_int(until)

        # Add to list
        if the_type == "ban":
            glovar.watch_ids["ban"][uid] = until
        elif the_type == "delete":
            glovar.watch_ids["delete"][uid] = until
        else:
            return False

        save("watch_ids")

        result = True
    except Exception as e:
        logger.warning(f"Receive watch user error: {e}", exc_info=True)

    return result


def receive_white_users(client: Client, message: Message) -> bool:
    # Receive white users
    result = False

    try:
        the_data = receive_file_data(client, message)

        if not the_data:
            return False

        glovar.white_ids = the_data
        save("white_ids")

        result = False
    except Exception as e:
        logger.warning(f"Receive white users error: {e}", exc_info=True)

    return result
