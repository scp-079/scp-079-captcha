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
import re
from copy import deepcopy

from pyrogram import Client, Filters, Message

from .. import glovar
from ..functions.captcha import send_static, user_captcha
from ..functions.channel import get_debug_text, share_data
from ..functions.command import delete_normal_command, delete_shared_command, command_error
from ..functions.config import conflict_config, get_config_text, update_config
from ..functions.etc import bold, code, general_link, get_command_context, get_int, get_now, get_text, lang
from ..functions.etc import mention_id, message_link, thread
from ..functions.file import save
from ..functions.filters import authorized_group, captcha_group, class_e, from_user
from ..functions.filters import is_class_c, is_class_e, is_from_user, test_group
from ..functions.group import delete_message
from ..functions.telegram import forward_messages, get_group_info, get_messages, resolve_username, send_message
from ..functions.telegram import send_report_message
from ..functions.user import terminate_user_pass, terminate_user_succeed, terminate_user_undo_pass

# Enable logging
logger = logging.getLogger(__name__)


@Client.on_message(Filters.incoming & Filters.group
                   & Filters.command(["captcha"], glovar.prefix)
                   & ~captcha_group & ~test_group & authorized_group
                   & from_user)
def captcha(client: Client, message: Message) -> bool:
    # Send CAPTCHA request manually
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        gid = message.chat.id

        # Check permission
        if not is_class_c(None, message):
            return False

        # Basic data
        now = message.date or get_now()
        r_message = message.reply_to_message
        aid = message.from_user.id

        if not r_message or not is_from_user(None, r_message):
            return False

        # Check pass
        if is_class_c(None, r_message) or is_class_e(None, r_message):
            return False

        if r_message.new_chat_members:
            user = r_message.new_chat_members[0]
        else:
            user = r_message.from_user

        result = user_captcha(
            client=client,
            message=r_message,
            gid=gid,
            user=user,
            mid=r_message.message_id,
            now=now,
            aid=aid
        )
    except Exception as e:
        logger.warning(f"Captcha error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()
        delete_normal_command(client, message)

    return result


@Client.on_message(Filters.incoming & Filters.group & Filters.command(["config"], glovar.prefix)
                   & ~captcha_group & ~test_group & authorized_group
                   & from_user)
def config(client: Client, message: Message) -> bool:
    # Request CONFIG session
    result = False

    glovar.locks["config"].acquire()

    try:
        # Basic data
        gid = message.chat.id
        aid = message.from_user.id
        mid = message.from_user.id

        # Check permission
        if not is_class_c(None, message):
            return False

        # Check command format
        command_type, command_context = get_command_context(message)

        if not command_type or not re.search(f"^{glovar.sender}$", command_type, re.I):
            return False

        now = get_now()

        # Check the config lock
        if now - glovar.configs[gid]["lock"] < 310:
            return command_error(client, message, lang("config_change"), lang("config_flood"))

        # Private check
        if command_context == "private":
            result = forward_messages(
                client=client,
                cid=glovar.logging_channel_id,
                fid=gid,
                mids=[mid]
            )

            if not result:
                return False

            text = (f"{lang('project')}{lang('colon')}{code(glovar.sender)}\n"
                    f"{lang('user_id')}{lang('colon')}{code(aid)}\n"
                    f"{lang('level')}{lang('colon')}{code(lang('config_create'))}\n"
                    f"{lang('rule')}{lang('colon')}{code(lang('rule_custom'))}\n")
            result = send_message(client, glovar.logging_channel_id, text, result.message_id)
        else:
            result = None

        # Set lock
        glovar.configs[gid]["lock"] = now
        save("configs")

        # Ask CONFIG generate a config session
        group_name, group_link = get_group_info(client, message.chat)
        share_data(
            client=client,
            receivers=["CONFIG"],
            action="config",
            action_type="ask",
            data={
                "project_name": glovar.project_name,
                "project_link": glovar.project_link,
                "group_id": gid,
                "group_name": group_name,
                "group_link": group_link,
                "user_id": aid,
                "private": command_context == "private",
                "config": glovar.configs[gid],
                "default": glovar.default_config
            }
        )

        # Send debug message
        text = get_debug_text(client, message.chat)
        text += (f"{lang('admin_group')}{lang('colon')}{code(message.from_user.id)}\n"
                 f"{lang('action')}{lang('colon')}{code(lang('config_create'))}\n")

        if result:
            text += f"{lang('evidence')}{lang('colon')}{general_link(result.message_id, message_link(result))}\n"

        thread(send_message, (client, glovar.debug_channel_id, text))

        result = True
    except Exception as e:
        logger.warning(f"Config error: {e}", exc_info=True)
    finally:
        glovar.locks["config"].release()
        delete_shared_command(client, message)

    return result


@Client.on_message(Filters.incoming & Filters.group
                   & Filters.command([f"config_{glovar.sender.lower()}"], glovar.prefix)
                   & ~captcha_group & ~test_group & authorized_group
                   & from_user)
def config_directly(client: Client, message: Message) -> bool:
    # Config the bot directly
    result = False

    glovar.locks["config"].acquire()

    try:
        # Basic data
        gid = message.chat.id
        aid = message.from_user.id
        now = get_now()

        # Check permission
        if not is_class_c(None, message):
            return False

        # Get get the command
        command_type, command_context = get_command_context(message)

        # Check the command
        if not command_type:
            return command_error(client, message, lang("config_change"), lang("command_lack"))

        # Get the config
        new_config = deepcopy(glovar.configs[gid])

        # Show the config
        if command_type == "show":
            text = (f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"
                    f"{lang('action')}{lang('colon')}{code(lang('config_show'))}\n"
                    f"{get_config_text(new_config)}\n")
            return send_report_message(30, client, gid, text)

        # Check the config lock
        if now - new_config["lock"] < 310:
            return command_error(client, message, lang("config_change"), lang("config_flood"))

        # Set the config to default status
        if command_type == "default":
            new_config = deepcopy(glovar.default_config)
            new_config["lock"] = now
            return update_config(client, message, new_config, "default")

        # Check the command format
        if not command_context:
            return command_error(client, message, lang("config_change"), lang("command_lack"))

        # Check the command type
        if command_type not in {"delete", "restrict", "ban", "forgive", "hint", "pass", "pin", "manual"}:
            return command_error(client, message, lang("config_change"), lang("command_type"))

        # New settings
        if command_context == "off":
            new_config[command_type] = False
        elif command_context == "on":
            new_config[command_type] = True
        else:
            return command_error(client, message, lang("config_change"), lang("command_para"))

        new_config = conflict_config(new_config, ["restrict", "ban"], command_type)
        new_config["default"] = False
        result = update_config(client, message, new_config, f"{command_type} {command_context}")
    except Exception as e:
        logger.warning(f"Config directly error: {e}", exc_info=True)
    finally:
        glovar.locks["config"].release()
        delete_normal_command(client, message)

    return result


@Client.on_message(Filters.incoming & Filters.group & Filters.command(["pass"], glovar.prefix)
                   & captcha_group & ~test_group
                   & from_user & class_e)
def pass_captcha(client: Client, message: Message) -> bool:
    # Pass in CAPTCHA
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        cid = message.chat.id
        aid = message.from_user.id
        mid = message.message_id

        if not message.reply_to_message or not message.reply_to_message.from_user:
            return False

        # Get the user id
        user = message.reply_to_message.from_user
        uid = user.id

        if user.is_self:
            message_text = get_text(message.reply_to_message)
            uid = get_int(message_text.split("\n")[1].split(lang("colon"))[1])

        # Check the user status
        if not (uid
                and uid != aid
                and glovar.user_ids.get(uid, {})
                and glovar.user_ids[uid]["wait"]
                and glovar.user_ids[uid]["mid"]):
            return delete_message(client, cid, mid)

        # Let user pass
        terminate_user_succeed(
            client=client,
            uid=uid
        )

        # Send the report message
        text = (f"{lang('admin')}{lang('colon')}{mention_id(aid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('action_pass'))}\n"
                f"{lang('user_id')}{lang('colon')}{mention_id(uid)}\n"
                f"{lang('status')}{lang('colon')}{code(lang('status_succeeded'))}\n")
        thread(send_message, (client, cid, text, mid))

        result = True
    except Exception as e:
        logger.warning(f"Pass captcha error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


@Client.on_message(Filters.incoming & Filters.group & Filters.command(["pass"], glovar.prefix)
                   & ~captcha_group & ~test_group & authorized_group
                   & from_user)
def pass_group(client: Client, message: Message) -> bool:
    # Pass in group

    if not message or not message.chat:
        return True

    # Basic data
    gid = message.chat.id
    mid = message.message_id

    glovar.locks["message"].acquire()
    try:
        # Check permission
        if not is_class_c(None, message):
            return True

        r_message = message.reply_to_message

        # Generate the report message's text
        aid = message.from_user.id
        text = f"{lang('admin')}{lang('colon')}{code(aid)}\n"

        # Proceed
        if r_message and is_from_user(None, r_message):
            if r_message.from_user.is_self:
                r_message = get_messages(client, gid, r_message.message_id)

                if r_message and r_message.reply_to_message:
                    uid = r_message.reply_to_message.from_user.id
                else:
                    return True
            elif r_message.new_chat_members:
                uid = r_message.new_chat_members[0].id
            else:
                uid = r_message.from_user.id
        else:
            uid = 0
            id_text, _ = get_command_context(message)

            if id_text:
                uid = get_int(id_text)

            if not uid and id_text:
                peer_id, peer_type = resolve_username(client, id_text)

                if peer_type == "user":
                    uid = peer_id

        if uid:
            if glovar.user_ids.get(uid, {}) and glovar.user_ids[uid]["wait"].get(gid, 0):
                terminate_user_pass(
                    client=client,
                    uid=uid,
                    gid=gid,
                    aid=aid
                )
                text += (f"{lang('action')}{lang('colon')}{code(lang('action_pass'))}\n"
                         f"{lang('user_id')}{lang('colon')}{mention_id(uid)}\n"
                         f"{lang('status')}{lang('colon')}{code(lang('status_succeeded'))}\n")
            elif glovar.user_ids[uid]["pass"].get(gid, 0):
                terminate_user_undo_pass(
                    client=client,
                    uid=uid,
                    gid=gid,
                    aid=aid
                )
                text += (f"{lang('action')}{lang('colon')}{code(lang('action_undo_pass'))}\n"
                         f"{lang('user_id')}{lang('colon')}{mention_id(uid)}\n"
                         f"{lang('status')}{lang('colon')}{code(lang('status_succeeded'))}\n")
            else:
                text += (f"{lang('action')}{lang('colon')}{code(lang('action_pass'))}\n"
                         f"{lang('status')}{lang('colon')}{code(lang('status_failed'))}\n"
                         f"{lang('reason')}{lang('colon')}{code(lang('reason_none'))}\n")
        else:
            text += (f"{lang('action')}{lang('colon')}{code(lang('action_pass'))}\n"
                     f"{lang('status')}{lang('colon')}{code(lang('status_failed'))}\n"
                     f"{lang('reason')}{lang('colon')}{code(lang('command_usage'))}\n")

        # Send the report message
        thread(send_report_message, (30, client, gid, text))

        return True
    except Exception as e:
        logger.warning(f"Pass group error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()
        delete_message(client, gid, mid)

    return False


@Client.on_message(Filters.incoming & Filters.group & Filters.command(["static"], glovar.prefix)
                   & ~captcha_group & ~test_group & authorized_group
                   & from_user)
def static(client: Client, message: Message) -> bool:
    # Send a new static hint message

    if not message or not message.chat:
        return True

    # Basic data
    gid = message.chat.id
    mid = message.message_id

    glovar.locks["message"].acquire()

    try:
        # Check permission
        if not is_class_c(None, message):
            return True

        # Generate the report message's text
        aid = message.from_user.id
        text = (f"{lang('admin')}{lang('colon')}{code(aid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('action_static'))}\n"
                f"{lang('status')}{lang('colon')}{code(lang('status_succeeded'))}\n")

        # Proceed
        hint_text = f"{lang('description')}{lang('colon')}{code(lang('description_hint'))}\n"
        send_static(client, gid, hint_text)

        # Send the report message
        thread(send_report_message, (15, client, gid, text))

        return True
    except Exception as e:
        logger.warning(f"Static error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()
        delete_message(client, gid, mid)

    return False


@Client.on_message(Filters.incoming & Filters.group & Filters.command(["version"], glovar.prefix)
                   & test_group
                   & from_user)
def version(client: Client, message: Message) -> bool:
    # Check the program's version
    result = False

    try:
        # Basic data
        cid = message.chat.id
        aid = message.from_user.id
        mid = message.message_id

        # Generate the text
        text = (f"{lang('admin')}{lang('colon')}{mention_id(aid)}\n\n"
                f"{lang('version')}{lang('colon')}{bold(glovar.version)}\n")

        # Send the report message
        result = send_message(client, cid, text, mid)
    except Exception as e:
        logger.warning(f"Version error: {e}", exc_info=True)

    return result
