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

from pyrogram import Client, Filters, Message

from .. import glovar
from ..functions.captcha import question_answer, question_ask, user_captcha
from ..functions.channel import ask_help_welcome, get_debug_text
from ..functions.etc import code, general_link, get_now, lang, thread, mention_id
from ..functions.file import save
from ..functions.filters import authorized_group, captcha_group, class_c, class_d, class_e, declared_message
from ..functions.filters import exchange_channel, from_user, hide_channel, is_class_d_user, is_class_e_user
from ..functions.filters import new_group, test_group
from ..functions.group import delete_message, leave_group
from ..functions.ids import init_group_id
from ..functions.receive import receive_add_bad, receive_config_commit, receive_clear_data
from ..functions.receive import receive_config_reply, receive_config_show, receive_declared_message
from ..functions.receive import receive_help_captcha, receive_leave_approve, receive_regex, receive_refresh
from ..functions.receive import receive_remove_bad, receive_remove_score, receive_remove_watch, receive_rollback
from ..functions.receive import receive_text_data, receive_user_score, receive_warn_banned_user, receive_watch_user
from ..functions.telegram import get_admins, send_message
from ..functions.timers import backup_files, send_count
from ..functions.user import kick_user, terminate_user

# Enable logging
logger = logging.getLogger(__name__)


@Client.on_message(Filters.incoming & Filters.group & Filters.new_chat_members
                   & ~captcha_group & ~test_group & ~new_group & authorized_group
                   & from_user & ~class_c
                   & ~declared_message)
def hint(client: Client, message: Message) -> bool:
    # Check new joined user
    glovar.locks["message"].acquire()
    try:
        # Basic data
        gid = message.chat.id
        mid = message.message_id
        now = message.date or get_now()

        # Check config
        if glovar.configs[gid].get("manual") or is_class_e_user(message.from_user):
            uid = message.new_chat_members[0].id
            ask_help_welcome(client, uid, [gid], mid)
            return True

        for new in message.new_chat_members:
            # Basic data
            uid = new.id

            # Process
            result = user_captcha(
                client=client,
                message=message,
                gid=gid,
                user=new,
                mid=mid,
                now=now
            )

            if not result:
                return True

            # Update user's join status
            glovar.user_ids[uid]["join"][gid] = now
            save("user_ids")

        return True
    except Exception as e:
        logger.warning(f"Hint error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return False


@Client.on_message(Filters.incoming & Filters.group & ~Filters.new_chat_members
                   & ~captcha_group & ~test_group & authorized_group
                   & from_user & ~class_c & ~class_d & ~class_e
                   & ~declared_message)
def check(client: Client, message: Message) -> bool:
    # Check the messages sent from groups
    glovar.locks["message"].acquire()
    try:
        # Basic data
        gid = message.chat.id
        uid = message.from_user.id
        mid = message.message_id

        # Check wait list
        if (glovar.user_ids.get(uid, {})
                and (glovar.user_ids[uid]["wait"].get(gid, 0)
                     or glovar.user_ids[uid]["failed"].get(gid, 0))):
            terminate_user(
                client=client,
                the_type="delete",
                uid=uid,
                gid=gid,
                mid=mid
            )

        return True
    except Exception as e:
        logger.warning(f"Check error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return False


@Client.on_message(Filters.incoming & Filters.group & Filters.new_chat_members
                   & captcha_group & ~new_group
                   & from_user
                   & ~declared_message)
def verify_ask(client: Client, message: Message) -> bool:
    # Check the messages sent from groups
    glovar.locks["message"].acquire()
    try:
        # Basic data
        gid = message.chat.id
        mid = message.message_id

        for new in message.new_chat_members:
            # Basic data
            uid = new.id

            # Check if the user is Class D personnel
            if is_class_d_user(new):
                kick_user(client, gid, uid)
                delete_message(client, gid, mid)
                continue

            # Check if the user is Class E personnel
            if is_class_e_user(new):
                delete_message(client, gid, mid)
                continue

            # Check data
            if not glovar.user_ids.get(uid, {}):
                kick_user(client, gid, uid)
                delete_message(client, gid, mid)
                continue

            # Check wait list
            if not glovar.user_ids[uid]["wait"]:
                kick_user(client, gid, uid)
                delete_message(client, gid, mid)
                continue

            # Check the question status
            if glovar.user_ids[uid]["mid"]:
                delete_message(client, gid, mid)
                continue

            # Ask a new question
            question_ask(client, new, mid)

        return True
    except Exception as e:
        logger.warning(f"Verify ask error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return False


@Client.on_message(Filters.incoming & Filters.group & ~Filters.new_chat_members
                   & captcha_group
                   & from_user)
def verify_check(client: Client, message: Message) -> bool:
    # Check the messages sent from the CAPTCHA group

    if not message or not message.chat:
        return True

    # Basic data
    gid = message.chat.id
    mid = message.message_id

    glovar.locks["message"].acquire()
    try:
        # Basic data
        uid = message.from_user.id

        # Check message
        if message.service:
            return True

        # Check if the user is Class D personnel
        if is_class_d_user(message.from_user):
            return True

        # Check if the user is Class E personnel
        if is_class_e_user(message.from_user):
            return True

        # Check data
        if not glovar.user_ids.get(uid, {}):
            return True

        # Check wait list
        if not glovar.user_ids[uid]["wait"]:
            return True

        # Check the question status
        if not glovar.user_ids[uid]["mid"]:
            return True

        # Check the message
        if not message.text and not message.caption:
            return True

        # Answer the question
        question_answer(client, uid, message.text or message.caption)

        return True
    except Exception as e:
        logger.warning(f"Verify check error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()
        delete_message(client, gid, mid)

    return False


@Client.on_message(Filters.incoming & Filters.channel & ~Filters.command(glovar.all_commands, glovar.prefix)
                   & hide_channel, group=-1)
def exchange_emergency(client: Client, message: Message) -> bool:
    # Sent emergency channel transfer request
    try:
        # Read basic information
        data = receive_text_data(message)

        if not data:
            return True

        sender = data["from"]
        receivers = data["to"]
        action = data["action"]
        action_type = data["type"]
        data = data["data"]

        if "EMERGENCY" not in receivers:
            return True

        if action != "backup":
            return True

        if action_type != "hide":
            return True

        if data is True:
            glovar.should_hide = data
        elif data is False and sender == "MANAGE":
            glovar.should_hide = data

        project_text = general_link(glovar.project_name, glovar.project_link)
        hide_text = (lambda x: lang("enabled") if x else "disabled")(glovar.should_hide)
        text = (f"{lang('project')}{lang('colon')}{project_text}\n"
                f"{lang('action')}{lang('colon')}{code(lang('transfer_channel'))}\n"
                f"{lang('emergency_channel')}{lang('colon')}{code(hide_text)}\n")
        thread(send_message, (client, glovar.debug_channel_id, text))

        return True
    except Exception as e:
        logger.warning(f"Exchange emergency error: {e}", exc_info=True)

    return False


@Client.on_message(Filters.incoming & Filters.group
                   & (Filters.new_chat_members | Filters.group_chat_created | Filters.supergroup_chat_created)
                   & ~captcha_group & ~test_group & new_group
                   & from_user)
def init_group(client: Client, message: Message) -> bool:
    # Initiate new groups
    try:
        # Basic data
        gid = message.chat.id
        inviter = message.from_user

        # Text prefix
        text = get_debug_text(client, message.chat)

        # Check permission
        if inviter.id == glovar.user_id:
            # Remove the left status
            if gid in glovar.left_group_ids:
                glovar.left_group_ids.discard(gid)
                save("left_group_ids")

            # Update group's admin list
            if not init_group_id(gid):
                return True

            admin_members = get_admins(client, gid)

            if admin_members:
                glovar.admin_ids[gid] = {admin.user.id for admin in admin_members
                                         if ((not admin.user.is_bot and not admin.user.is_deleted)
                                             or admin.user.id in glovar.bot_ids)}
                save("admin_ids")
                text += f"{lang('status')}{lang('colon')}{code(lang('status_joined'))}\n"
            else:
                thread(leave_group, (client, gid))
                text += (f"{lang('status')}{lang('colon')}{code(lang('status_left'))}\n"
                         f"{lang('reason')}{lang('colon')}{code(lang('reason_admin'))}\n")
        else:
            if gid in glovar.left_group_ids:
                return leave_group(client, gid)

            leave_group(client, gid)

            text += (f"{lang('status')}{lang('colon')}{code(lang('status_left'))}\n"
                     f"{lang('reason')}{lang('colon')}{code(lang('reason_unauthorized'))}\n")

        # Add inviter info
        if message.from_user.username:
            text += f"{lang('inviter')}{lang('colon')}{mention_id(inviter.id)}\n"
        else:
            text += f"{lang('inviter')}{lang('colon')}{code(inviter.id)}\n"

        # Send debug message
        thread(send_message, (client, glovar.debug_channel_id, text))

        return True
    except Exception as e:
        logger.warning(f"Init group error: {e}", exc_info=True)

    return False


@Client.on_message((Filters.incoming or glovar.aio) & Filters.channel
                   & ~Filters.command(glovar.all_commands, glovar.prefix)
                   & exchange_channel)
def process_data(client: Client, message: Message) -> bool:
    # Process the data in exchange channel
    glovar.locks["receive"].acquire()
    try:
        data = receive_text_data(message)

        if not data:
            return True

        sender = data["from"]
        receivers = data["to"]
        action = data["action"]
        action_type = data["type"]
        data = data["data"]

        # This will look awkward,
        # seems like it can be simplified,
        # but this is to ensure that the permissions are clear,
        # so it is intentionally written like this
        if glovar.sender in receivers:

            if sender == "CLEAN":

                if action == "add":
                    if action_type == "bad":
                        receive_add_bad(client, data)
                    elif action_type == "watch":
                        receive_watch_user(data)

            elif sender == "CONFIG":

                if action == "config":
                    if action_type == "commit":
                        receive_config_commit(data)
                    elif action_type == "reply":
                        receive_config_reply(client, data)

            elif sender == "LANG":

                if action == "add":
                    if action_type == "bad":
                        receive_add_bad(client, data)
                    elif action_type == "watch":
                        receive_watch_user(data)

                elif action == "update":
                    if action_type == "declare":
                        receive_declared_message(data)
                    elif action_type == "score":
                        receive_user_score(sender, data)

            elif sender == "LONG":

                if action == "add":
                    if action_type == "bad":
                        receive_add_bad(client, data)
                    elif action_type == "watch":
                        receive_watch_user(data)

                elif action == "update":
                    if action_type == "declare":
                        receive_declared_message(data)
                    elif action_type == "score":
                        receive_user_score(sender, data)

            elif sender == "MANAGE":

                if action == "add":
                    if action_type == "bad":
                        receive_add_bad(client, data)

                elif action == "backup":
                    if action_type == "now":
                        thread(backup_files, (client,))
                    elif action_type == "rollback":
                        receive_rollback(client, message, data)

                elif action == "clear":
                    receive_clear_data(client, action_type, data)

                elif action == "config":
                    if action_type == "show":
                        receive_config_show(client, data)

                elif action == "leave":
                    if action_type == "approve":
                        receive_leave_approve(client, data)

                elif action == "remove":
                    if action_type == "bad":
                        receive_remove_bad(client, data)
                    elif action_type == "score":
                        receive_remove_score(client, data)
                    elif action_type == "watch":
                        receive_remove_watch(data)

                elif action == "update":
                    if action_type == "refresh":
                        receive_refresh(client, data)

            elif sender == "NOFLOOD":

                if action == "add":
                    if action_type == "bad":
                        receive_add_bad(client, data)
                    elif action_type == "watch":
                        receive_watch_user(data)

                elif action == "update":
                    if action_type == "declare":
                        receive_declared_message(data)
                    elif action_type == "score":
                        receive_user_score(sender, data)

            elif sender == "NOPORN":

                if action == "add":
                    if action_type == "bad":
                        receive_add_bad(client, data)
                    elif action_type == "watch":
                        receive_watch_user(data)

                elif action == "update":
                    if action_type == "declare":
                        receive_declared_message(data)
                    elif action_type == "score":
                        receive_user_score(sender, data)

            elif sender == "NOSPAM":

                if action == "add":
                    if action_type == "bad":
                        receive_add_bad(client, data)
                    elif action_type == "watch":
                        receive_watch_user(data)

                elif action == "help":
                    if action_type == "captcha":
                        receive_help_captcha(client, data)

                elif action == "update":
                    if action_type == "declare":
                        receive_declared_message(data)
                    elif action_type == "score":
                        receive_user_score(sender, data)

            elif sender == "RECHECK":

                if action == "add":
                    if action_type == "bad":
                        receive_add_bad(client, data)
                    elif action_type == "watch":
                        receive_watch_user(data)

                elif action == "update":
                    if action_type == "declare":
                        receive_declared_message(data)
                    elif action_type == "score":
                        receive_user_score(sender, data)

            elif sender == "REGEX":

                if action == "regex":
                    if action_type == "update":
                        receive_regex(client, message, data)
                    elif action_type == "count":
                        if data == "ask":
                            send_count(client)

            elif sender == "WARN":

                if action == "update":
                    if action_type == "score":
                        receive_user_score(sender, data)

            elif sender == "WATCH":

                if action == "add":
                    if action_type == "watch":
                        receive_watch_user(data)

        elif "USER" in receivers:

            if sender == "WARN":

                if action == "help":
                    if action_type == "delete":
                        receive_warn_banned_user(client, data)

        return True
    except Exception as e:
        logger.warning(f"Process data error: {e}", exc_info=True)
    finally:
        glovar.locks["receive"].release()

    return False
