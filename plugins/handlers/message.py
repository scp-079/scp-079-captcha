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

from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, Message

from .. import glovar
from ..functions.challenge import question_answer, question_ask, user_captcha, user_captcha_qns
from ..functions.channel import ask_help_welcome, get_debug_text
from ..functions.command import delete_normal_command
from ..functions.etc import code, general_link, get_now, lang, thread, mention_id
from ..functions.file import save
from ..functions.filters import aio, authorized_group, captcha_group, class_c, class_d, class_e, declared_message
from ..functions.filters import exchange_channel, from_user, hide_channel, is_class_d_user, is_class_e_user
from ..functions.filters import is_flooded, is_should_qns, new_group, test_group, is_class_c_user
from ..functions.group import delete_message, save_admins, leave_group
from ..functions.ids import init_group_id
from ..functions.receive import receive_add_bad, receive_check_log, receive_clear_data, receive_config_commit
from ..functions.receive import receive_config_reply, receive_config_show, receive_declared_message
from ..functions.receive import receive_flood_check, receive_help_captcha, receive_help_confirm
from ..functions.receive import receive_warn_kicked_user, receive_ignore_ids, receive_leave_approve, receive_regex
from ..functions.receive import receive_refresh, receive_remove_bad, receive_remove_score, receive_remove_watch
from ..functions.receive import receive_remove_white, receive_rollback, receive_text_data, receive_user_score
from ..functions.receive import receive_watch_user, receive_white_users
from ..functions.telegram import get_admins, send_message
from ..functions.timers import backup_files, send_count, share_failed_users
from ..functions.user import get_level, kick_user, terminate_user_delete

# Enable logging
logger = logging.getLogger(__name__)


@Client.on_message(filters.incoming & filters.group & filters.new_chat_members
                   & ~captcha_group & ~test_group & ~new_group & authorized_group
                   & from_user & ~class_c
                   & ~declared_message)
def hint(client: Client, message: Message) -> bool:
    # Check new joined user
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        gid = message.chat.id
        mid = message.message_id
        now = message.date or get_now()

        # Check the group status
        if is_flooded(gid):
            delete_message(client, gid, mid)

        # Check config
        if glovar.configs[gid].get("manual", False) or (is_class_e_user(message.from_user) and not is_should_qns(gid)):
            return bool([ask_help_welcome(client, new.id, [gid], mid)
                         for new in message.new_chat_members if not new.is_bot])

        for new in message.new_chat_members:
            # Basic data
            uid = new.id

            # Check user status
            if (glovar.user_ids.get(uid, {})
                    and (glovar.user_ids[uid]["wait"].get(gid, 0)
                         or (glovar.user_ids[uid]["failed"].get(gid, 0) > 0 and get_level(gid) != "kick"))):
                terminate_user_delete(
                    client=client,
                    gid=gid,
                    mid=mid
                )
                continue

            # Process
            if is_should_qns(gid):
                result = user_captcha_qns(
                    client=client,
                    message=message,
                    gid=gid,
                    user=new,
                    mid=mid
                )
            else:
                result = user_captcha(
                    client=client,
                    message=message,
                    gid=gid,
                    user=new,
                    mid=mid,
                    now=now
                )

            if not result:
                continue

            # Update user's join status
            glovar.user_ids[uid]["join"][gid] = now
            save("user_ids")

        result = True
    except Exception as e:
        logger.warning(f"Hint error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


@Client.on_chat_member_updated(authorized_group)
def hint_further(client: Client, chat_member_updated: ChatMemberUpdated) -> bool:
    # Check new joined user
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        gid = chat_member_updated.chat.id
        mid = 0
        now = chat_member_updated.date or get_now()

        # Check new chat member
        if not chat_member_updated.new_chat_member:
            return False

        if chat_member_updated.from_user.is_self or chat_member_updated.from_user.is_bot:
            return False

        if not chat_member_updated.new_chat_member.status == "member":
            return False

        # Get user
        user = chat_member_updated.new_chat_member.user
        uid = user.id

        # Check class C status
        if is_class_c_user(gid, user) or is_class_c_user(gid, chat_member_updated.from_user):
            return False

        # Check config
        if glovar.configs[gid].get("manual", False) or (is_class_e_user(user) and not is_should_qns(gid)):
            return ask_help_welcome(client, uid, [gid])

        # Check user status
        if (glovar.user_ids.get(uid, {})
                and (glovar.user_ids[uid]["wait"].get(gid, 0)
                     or (glovar.user_ids[uid]["failed"].get(gid, 0) > 0 and get_level(gid) != "kick"))):
            return False

        # Process
        if is_should_qns(gid):
            result = user_captcha_qns(
                client=client,
                message=None,
                gid=gid,
                user=user,
                mid=mid
            )
        else:
            result = user_captcha(
                client=client,
                message=None,
                gid=gid,
                user=user,
                mid=mid,
                now=now
            )

        if not result:
            return False

        # Update user's join status
        glovar.user_ids[uid]["join"][gid] = now
        save("user_ids")

        result = True
    except Exception as e:
        logger.warning(f"Hint further error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


@Client.on_message(filters.incoming & filters.group & ~filters.new_chat_members
                   & ~captcha_group & ~test_group & authorized_group
                   & from_user & ~class_c & ~class_d & ~class_e
                   & ~declared_message)
def check(client: Client, message: Message) -> bool:
    # Check the messages sent from groups
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        gid = message.chat.id
        uid = message.from_user.id
        mid = message.message_id

        # Check wait list
        if not (glovar.user_ids.get(uid, {})
                and (glovar.user_ids[uid]["wait"].get(gid, 0) or glovar.user_ids[uid]["failed"].get(gid, 0))):
            return False

        # Delete the message
        result = terminate_user_delete(
            client=client,
            gid=gid,
            mid=mid
        )
    except Exception as e:
        logger.warning(f"Check error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


@Client.on_message(filters.incoming & filters.group & filters.new_chat_members
                   & captcha_group & ~new_group
                   & from_user
                   & ~declared_message)
def verify_ask(client: Client, message: Message) -> bool:
    # Check the messages sent from groups
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        gid = message.chat.id
        mid = message.message_id

        for new in message.new_chat_members:
            # Basic data
            uid = new.id

            # Check if the user is Class E personnel
            if is_class_e_user(new):
                delete_message(client, gid, mid)
                continue

            # Check data
            if not glovar.user_ids.get(uid, {}):
                kick_user(client, gid, uid)
                delete_message(client, gid, mid)
                continue

            # User wait list
            wait_group_list = list(glovar.user_ids[uid]["wait"])

            # Check wait list
            if not wait_group_list or all(is_should_qns(g) and glovar.user_ids[uid]["qns"].get(g)
                                          for g in wait_group_list):
                kick_user(client, gid, uid)
                delete_message(client, gid, mid)
                continue

            # Check if the user is Class D personnel
            if is_class_d_user(new) and all(g not in glovar.ignore_ids["user"] for g in wait_group_list):
                kick_user(client, gid, uid)
                delete_message(client, gid, mid)
                continue

            # Check the question status
            if glovar.user_ids[uid]["mid"]:
                delete_message(client, gid, mid)
                continue

            # Ask a new question
            question_ask(client, new, mid)

        result = True
    except Exception as e:
        logger.warning(f"Verify ask error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


@Client.on_message(filters.incoming & filters.group & ~filters.new_chat_members
                   & captcha_group
                   & from_user)
def verify_check(client: Client, message: Message) -> bool:
    # Check the messages sent from the CAPTCHA group
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        uid = message.from_user.id

        # Check message
        if message.service:
            return False

        # Check if the user is Class E personnel
        if is_class_e_user(message.from_user):
            return False

        # Check data
        if not glovar.user_ids.get(uid, {}):
            return False

        # User wait list
        wait_group_list = list(glovar.user_ids[uid]["wait"])

        # Check wait list
        if not wait_group_list or all(is_should_qns(g) and glovar.user_ids[uid]["qns"].get(g)
                                      for g in wait_group_list):
            return False

        # Check if the user is Class D personnel
        if is_class_d_user(message.from_user) and all(gid not in glovar.ignore_ids["user"] for gid in wait_group_list):
            return False

        # Check the question status
        if not glovar.user_ids[uid]["mid"]:
            return False

        # Check the message
        if not message.text and not message.caption:
            return False

        # Answer the question
        result = question_answer(client, uid, message.text or message.caption)
    except Exception as e:
        logger.warning(f"Verify check error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()
        delete_normal_command(client, message)

    return result


@Client.on_message((filters.incoming | aio) & filters.channel
                   & ~filters.command(glovar.all_commands, glovar.prefix)
                   & hide_channel, group=-1)
def exchange_emergency(client: Client, message: Message) -> bool:
    # Sent emergency channel transfer request
    result = False

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

        result = True
    except Exception as e:
        logger.warning(f"Exchange emergency error: {e}", exc_info=True)

    return result


@Client.on_message(filters.incoming & filters.group
                   & (filters.new_chat_members | filters.group_chat_created | filters.supergroup_chat_created)
                   & ~captcha_group & ~test_group & new_group
                   & from_user)
def init_group(client: Client, message: Message) -> bool:
    # Initiate new groups
    result = False

    glovar.locks["admin"].acquire()

    try:
        # Basic data
        gid = message.chat.id
        inviter = message.from_user

        # Text prefix
        text = get_debug_text(client, message.chat)

        # Check permission
        if inviter.id != glovar.user_id:
            if gid in glovar.left_group_ids:
                return leave_group(client, gid)

            leave_group(client, gid, glovar.leave_reason)

            text += (f"{lang('status')}{lang('colon')}{code(lang('status_left'))}\n"
                     f"{lang('reason')}{lang('colon')}{code(lang('reason_unauthorized'))}\n")

            if message.from_user.username:
                text += f"{lang('inviter')}{lang('colon')}{mention_id(inviter.id)}\n"
            else:
                text += f"{lang('inviter')}{lang('colon')}{code(inviter.id)}\n"

            return thread(send_message, (client, glovar.debug_channel_id, text))

        # Remove the left status
        if gid in glovar.left_group_ids:
            glovar.left_group_ids.discard(gid)
            save("left_group_ids")

        # Update group's admin list
        if not init_group_id(gid):
            return True

        # Get admins
        admin_members = get_admins(client, gid)

        if admin_members:
            save_admins(gid, admin_members)
            text += f"{lang('status')}{lang('colon')}{code(lang('status_joined'))}\n"
        else:
            leave_group(client, gid)
            text += (f"{lang('status')}{lang('colon')}{code(lang('status_left'))}\n"
                     f"{lang('reason')}{lang('colon')}{code(lang('reason_admin'))}\n")

        # Add inviter info
        if inviter.username:
            text += f"{lang('inviter')}{lang('colon')}{mention_id(inviter.id)}\n"
        else:
            text += f"{lang('inviter')}{lang('colon')}{code(inviter.id)}\n"

        # Send debug message
        thread(send_message, (client, glovar.debug_channel_id, text))

        result = True
    except Exception as e:
        logger.warning(f"Init group error: {e}", exc_info=True)
    finally:
        glovar.locks["admin"].release()

    return result


@Client.on_message((filters.incoming | aio) & filters.channel
                   & ~filters.command(glovar.all_commands, glovar.prefix)
                   & exchange_channel)
def process_data(client: Client, message: Message) -> bool:
    # Process the data in exchange channel
    result = False

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

            if sender == "AVATAR":

                if action == "add":
                    if action_type == "white":
                        receive_white_users(client, message)

                elif action == "remove":
                    if action_type == "white":
                        receive_remove_white(data)

            elif sender == "CLEAN":

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
                        backup_files(client)
                    elif action_type == "rollback":
                        receive_rollback(client, message, data)

                elif action == "clear":
                    receive_clear_data(client, action_type, data)

                elif action == "config":
                    if action_type == "show":
                        receive_config_show(client, data)

                elif action == "flood":
                    if action_type == "check":
                        receive_flood_check(client, data)

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
                    elif action_type == "ignore":
                        receive_ignore_ids(client, message, sender)
                    elif action_type == "score":
                        receive_user_score(sender, data)

            elif sender == "REGEX":

                if action == "captcha":
                    if action_type == "ask":
                        share_failed_users(client, data)

                elif action == "regex":
                    if action_type == "update":
                        receive_regex(client, message, data)
                    elif action_type == "count":
                        if data == "ask":
                            send_count(client)

            elif sender == "USER":
                if action == "add":
                    if action_type == "bad":
                        receive_add_bad(client, data)

                elif action == "help":
                    if action_type == "confirm":
                        receive_help_confirm(client, data)
                    elif action_type == "log":
                        receive_check_log(client, message, data)

                elif action == "update":
                    if action_type == "ignore":
                        receive_ignore_ids(client, message, sender)

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
                        receive_warn_kicked_user(client, data)

        result = True
    except Exception as e:
        logger.warning(f"Process data error: {e}", exc_info=True)
    finally:
        glovar.locks["receive"].release()

    return result
