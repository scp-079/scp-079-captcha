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
import re
from copy import deepcopy

from pyrogram import Client, Filters, Message

from .. import glovar
from ..functions.captcha import send_static
from ..functions.channel import get_debug_text, share_data
from ..functions.etc import bold, code, delay, get_command_context, get_command_type, get_int, get_now, get_text, lang
from ..functions.etc import mention_id, thread
from ..functions.file import save
from ..functions.filters import authorized_group, captcha_group, class_e, from_user, is_class_c, test_group
from ..functions.group import delete_message, get_config_text
from ..functions.telegram import get_group_info, resolve_username, send_message, send_report_message
from ..functions.timers import new_invite_link
from ..functions.user import terminate_user

# Enable logging
logger = logging.getLogger(__name__)


@Client.on_message(Filters.incoming & Filters.group & Filters.command(["config"], glovar.prefix)
                   & ~captcha_group & ~test_group & authorized_group
                   & from_user)
def config(client: Client, message: Message) -> bool:
    # Request CONFIG session

    if not message or not message.chat:
        return True

    # Basic data
    gid = message.chat.id
    mid = message.message_id

    try:
        # Check permission
        if not is_class_c(None, message):
            return True

        # Check command format
        command_type = get_command_type(message)
        if not command_type or not re.search(f"^{glovar.sender}$", command_type, re.I):
            return True

        now = get_now()

        # Check the config lock
        if now - glovar.configs[gid]["lock"] < 310:
            return True

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
                "user_id": message.from_user.id,
                "config": glovar.configs[gid],
                "default": glovar.default_config
            }
        )

        # Send debug message
        text = get_debug_text(client, message.chat)
        text += (f"{lang('admin_group')}{lang('colon')}{code(message.from_user.id)}\n"
                 f"{lang('action')}{lang('colon')}{code(lang('config_create'))}\n")
        thread(send_message, (client, glovar.debug_channel_id, text))

        return True
    except Exception as e:
        logger.warning(f"Config error: {e}", exc_info=True)
    finally:
        if is_class_c(None, message):
            delay(3, delete_message, [client, gid, mid])
        else:
            delete_message(client, gid, mid)

    return False


@Client.on_message(Filters.incoming & Filters.group
                   & Filters.command([f"config_{glovar.sender.lower()}"], glovar.prefix)
                   & ~captcha_group & ~test_group & authorized_group
                   & from_user)
def config_directly(client: Client, message: Message) -> bool:
    # Config the bot directly

    if not message or not message.chat:
        return True

    # Basic data
    gid = message.chat.id
    mid = message.message_id

    try:
        # Check permission
        if not is_class_c(None, message):
            return True

        aid = message.from_user.id
        success = True
        reason = lang("config_updated")
        new_config = deepcopy(glovar.configs[gid])
        text = f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"

        # Check command format
        command_type, command_context = get_command_context(message)
        if command_type:
            if command_type == "show":
                text += f"{lang('action')}{lang('colon')}{code(lang('config_show'))}\n"
                text += get_config_text(new_config)
                thread(send_report_message, (30, client, gid, text))
                return True

            now = get_now()

            # Check the config lock
            if now - new_config["lock"] > 310:
                if command_type == "default":
                    new_config = deepcopy(glovar.default_config)
                else:
                    if command_context:
                        if command_type in {"delete", "restrict", "ban", "forgive", "hint", "pass"}:
                            if command_context == "off":
                                new_config[command_type] = False
                            elif command_context == "on":
                                new_config[command_type] = True
                            else:
                                success = False
                                reason = lang("command_para")

                            config_list = ["restrict", "ban"]
                            if command_type in config_list and new_config[command_type]:
                                config_list.remove(command_type)
                                for other in config_list:
                                    new_config[other] = False
                        else:
                            success = False
                            reason = lang("command_type")
                    else:
                        success = False
                        reason = lang("command_lack")

                    if success:
                        new_config["default"] = False
            else:
                success = False
                reason = lang("config_locked")
        else:
            success = False
            reason = lang("command_usage")

        if success and new_config != glovar.configs[gid]:
            # Save new config
            glovar.configs[gid] = new_config
            save("configs")

            # Send debug message
            debug_text = get_debug_text(client, message.chat)
            debug_text += (f"{lang('admin_group')}{lang('colon')}{code(message.from_user.id)}\n"
                           f"{lang('action')}{lang('colon')}{code(lang('config_change'))}\n"
                           f"{lang('more')}{lang('colon')}{code(f'{command_type} {command_context}')}\n")
            thread(send_message, (client, glovar.debug_channel_id, debug_text))

        text += (f"{lang('action')}{lang('colon')}{code(lang('config_change'))}\n"
                 f"{lang('status')}{lang('colon')}{code(reason)}\n")
        thread(send_report_message, ((lambda x: 10 if x else 5)(success), client, gid, text))

        return True
    except Exception as e:
        logger.warning(f"Config directly error: {e}", exc_info=True)
    finally:
        delete_message(client, gid, mid)

    return False


@Client.on_message(Filters.incoming & Filters.group & Filters.command(["invite"], glovar.prefix)
                   & captcha_group & ~test_group
                   & from_user & class_e)
def invite(client: Client, message: Message) -> bool:
    # Send a new invite link to CAPTCHA channel
    try:
        # Basic data
        cid = message.chat.id
        aid = message.from_user.id
        mid = message.message_id

        # Generate
        new_invite_link(client, "new")

        # Generate the report message's text
        text = (f"{lang('admin')}{lang('colon')}{mention_id(aid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('action_invite'))}\n"
                f"{lang('status')}{lang('colon')}{code(lang('status_succeeded'))}\n")

        # Send the report message
        thread(send_message, (client, cid, text, mid))

        return True
    except Exception as e:
        logger.warning(f"Invite error: {e}", exc_info=True)

    return False


@Client.on_message(Filters.incoming & Filters.group & Filters.command(["pass"], glovar.prefix)
                   & captcha_group & ~test_group
                   & from_user & class_e)
def pass_captcha(client: Client, message: Message) -> bool:
    # Pass in CAPTCHA
    glovar.locks["message"].acquire()
    try:
        # Basic data
        cid = message.chat.id
        aid = message.from_user.id
        mid = message.message_id

        # Proceed
        if not message.reply_to_message:
            return True

        if not message.reply_to_message.from_user:
            return True

        user = message.reply_to_message.from_user
        uid = user.id

        if user.is_self:
            message_text = get_text(message.reply_to_message)
            uid = get_int(message_text.split("\n")[1].split(lang("colon"))[1])

        if (uid and uid != aid
                and glovar.user_ids.get(uid, {})
                and (glovar.user_ids[uid]["wait"]
                     or glovar.user_ids[uid]["failed"]
                     or glovar.user_ids[uid]["restricted"]
                     or glovar.user_ids[uid]["banned"])):
            terminate_user(
                client=client,
                the_type="succeed",
                uid=uid
            )
            text = (f"{lang('admin')}{lang('colon')}{mention_id(aid)}\n"
                    f"{lang('action')}{lang('colon')}{code(lang('action_pass'))}\n"
                    f"{lang('user_id')}{lang('colon')}{mention_id(uid)}\n"
                    f"{lang('status')}{lang('colon')}{code(lang('status_succeeded'))}\n")
            thread(send_message, (client, cid, text, mid))
        else:
            delete_message(client, cid, mid)

        return True
    except Exception as e:
        logger.warning(f"Pass captcha error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return False


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

        # Generate the report message's text
        aid = message.from_user.id
        text = f"{lang('admin')}{lang('colon')}{code(aid)}\n"

        # Proceed
        if message.reply_to_message and message.reply_to_message.from_user:
            if message.new_chat_members:
                uid = message.new_chat_members[0].id
            else:
                uid = message.reply_to_message.from_user.id
        else:
            uid = 0
            id_text, reason = get_command_context(message)
            if id_text:
                uid = get_int(id_text)

            if not uid and id_text:
                peer_id, peer_type = resolve_username(client, id_text)
                if peer_type == "user":
                    uid = peer_id

        if uid:
            if glovar.user_ids.get(uid, {}) and glovar.user_ids[uid]["wait"].get(gid, 0):
                terminate_user(
                    client=client,
                    the_type="pass",
                    uid=uid,
                    gid=gid,
                    aid=aid
                )
                text += (f"{lang('action')}{lang('colon')}{code(lang('action_pass'))}\n"
                         f"{lang('user_id')}{lang('colon')}{mention_id(uid)}\n"
                         f"{lang('status')}{lang('colon')}{code(lang('status_succeeded'))}\n")
            elif glovar.user_ids[uid]["pass"].get(gid, 0):
                terminate_user(
                    client=client,
                    the_type="undo_pass",
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
        thread(send_static, (client, gid, hint_text))

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
    try:
        cid = message.chat.id
        aid = message.from_user.id
        mid = message.message_id
        text = (f"{lang('admin')}{lang('colon')}{mention_id(aid)}\n\n"
                f"{lang('version')}{lang('colon')}{bold(glovar.version)}\n")
        thread(send_message, (client, cid, text, mid))

        return True
    except Exception as e:
        logger.warning(f"Version error: {e}", exc_info=True)

    return False
