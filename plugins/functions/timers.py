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

from pyrogram import Client, InlineKeyboardButton, InlineKeyboardMarkup

from .. import glovar
from .channel import share_data, share_regex_count
from .etc import code, general_link, get_now, lang, thread
from .file import save
from .group import delete_message, leave_group
from .telegram import edit_message_text, export_chat_invite_link, get_admins, get_group_info, send_message
from .user import kick_user, terminate_user, unrestrict_user

# Enable logging
logger = logging.getLogger(__name__)


def backup_files(client: Client) -> bool:
    # Backup data files to BACKUP
    try:
        for file in glovar.file_list:
            # Check
            if not eval(f"glovar.{file}"):
                continue

            # Share
            share_data(
                client=client,
                receivers=["BACKUP"],
                action="backup",
                action_type="data",
                data=file,
                file=f"data/{file}"
            )
            sleep(5)

        return True
    except Exception as e:
        logger.warning(f"Backup error: {e}", exc_info=True)

    return False


def interval_min_01(client: Client) -> bool:
    # Execute every minute
    glovar.locks["message"].acquire()
    try:
        # Basic data
        now = get_now()

        # Remove users from CAPTCHA group
        for uid in list(glovar.user_ids):
            time = glovar.user_ids[uid]["time"]
            if time and now - time > glovar.time_remove:
                glovar.user_ids[uid]["time"] = 0
                kick_user(client, glovar.captcha_group_id, uid)

        save("user_ids")

        # Check timeout
        for uid in list(glovar.user_ids):
            if not glovar.user_ids[uid]["wait"]:
                continue

            for gid in list(glovar.user_ids[uid]["wait"]):
                time = glovar.user_ids[uid]["wait"][gid]
                if now - time > glovar.time_captcha:
                    terminate_user(
                        client=client,
                        the_type="timeout",
                        uid=uid,
                        gid=gid
                    )

        # Delete hint messages
        wait_group_list = {gid for uid in list(glovar.user_ids) for gid in list(glovar.user_ids[uid]["wait"])}
        for gid in list(glovar.message_ids):
            mid, time = glovar.message_ids[gid]["hint"]
            if mid and (now - time > glovar.time_captcha or gid not in wait_group_list):
                glovar.message_ids[gid]["hint"] = (0, 0)
                delete_message(client, gid, mid)

        save("message_ids")

        return True
    except Exception as e:
        logger.warning(f"Interval min 01 error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return False


def interval_min_10() -> bool:
    # Execute every 10 minutes
    glovar.locks["message"].acquire()
    try:
        # Clear recorded users
        for gid in list(glovar.recorded_ids):
            glovar.recorded_ids[gid] = set()

        return True
    except Exception as e:
        logger.warning(f"Interval min 10 error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return False


def new_invite_link(client: Client, the_type: str) -> bool:
    # Generate new invite link
    glovar.locks["invite"].acquire()
    try:
        # Basic data
        mid = glovar.invite["id"]

        # Generate link
        link = export_chat_invite_link(client, glovar.captcha_group_id)

        if not link:
            return True

        glovar.invite["link"] = link

        # Generate text and markup
        text = f"{lang('description')}{lang('colon')}{code(lang('invite_text'))}\n"
        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=lang("invite_button"),
                        url=link
                    )
                ]
            ]
        )

        if the_type == "edit" and mid:
            result = edit_message_text(client, glovar.captcha_channel_id, mid, text, markup)
            if result:
                save("invite")
                return True

        result = send_message(client, glovar.captcha_channel_id, text, None, markup)
        if result:
            glovar.invite["id"] = result.message_id
            mid and delete_message(client, glovar.captcha_channel_id, mid)

        save("invite")

        return True
    except Exception as e:
        logger.warning(f"New invite link error: {e}", exc_info=True)
    finally:
        glovar.locks["invite"].release()

    return False


def reset_data(client: Client) -> bool:
    # Reset user data every month
    glovar.locks["message"].acquire()
    try:
        glovar.bad_ids = {
            "channels": set(),
            "users": set()
        }
        save("bad_ids")

        for uid in list(glovar.user_ids):
            for gid in list(glovar.user_ids[uid]["wait"]):
                unrestrict_user(client, gid, uid)

        glovar.user_ids = {}
        save("user_ids")

        glovar.watch_ids = {
            "ban": {},
            "delete": {}
        }
        save("watch_ids")

        # Send debug message
        text = (f"{lang('project')}{lang('colon')}{general_link(glovar.project_name, glovar.project_link)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('reset'))}\n")
        thread(send_message, (client, glovar.debug_channel_id, text))

        return True
    except Exception as e:
        logger.warning(f"Reset data error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return False


def send_count(client: Client) -> bool:
    # Send regex count to REGEX
    glovar.locks["regex"].acquire()
    try:
        for word_type in glovar.regex:
            share_regex_count(client, word_type)
            word_list = list(eval(f"glovar.{word_type}_words"))
            for word in word_list:
                eval(f"glovar.{word_type}_words")[word] = 0

            save(f"{word_type}_words")

        return True
    except Exception as e:
        logger.warning(f"Send count error: {e}", exc_info=True)
    finally:
        glovar.locks["regex"].release()

    return False


def update_admins(client: Client) -> bool:
    # Update admin list every day
    glovar.locks["admin"].acquire()
    try:
        group_list = list(glovar.admin_ids)
        for gid in group_list:
            try:
                should_leave = True
                reason = "permissions"
                admin_members = get_admins(client, gid)
                if admin_members and any([admin.user.is_self for admin in admin_members]):
                    glovar.admin_ids[gid] = {admin.user.id for admin in admin_members
                                             if ((not admin.user.is_bot and not admin.user.is_deleted)
                                                 or admin.user.id in glovar.bot_ids)}
                    if glovar.user_id not in glovar.admin_ids[gid]:
                        reason = "user"
                    else:
                        for admin in admin_members:
                            if admin.user.is_self:
                                if admin.can_delete_messages and admin.can_restrict_members:
                                    should_leave = False

                    if should_leave:
                        group_name, group_link = get_group_info(client, gid)
                        share_data(
                            client=client,
                            receivers=["MANAGE"],
                            action="leave",
                            action_type="request",
                            data={
                                "group_id": gid,
                                "group_name": group_name,
                                "group_link": group_link,
                                "reason": reason
                            }
                        )
                        reason = lang(f"reason_{reason}")
                        project_link = general_link(glovar.project_name, glovar.project_link)
                        debug_text = (f"{lang('project')}{lang('colon')}{project_link}\n"
                                      f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                                      f"{lang('group_id')}{lang('colon')}{code(gid)}\n"
                                      f"{lang('status')}{lang('colon')}{code(reason)}\n")
                        thread(send_message, (client, glovar.debug_channel_id, debug_text))
                    else:
                        save("admin_ids")
                elif admin_members is False or any([admin.user.is_self for admin in admin_members]) is False:
                    # Bot is not in the chat, leave automatically without approve
                    group_name, group_link = get_group_info(client, gid)
                    leave_group(client, gid)
                    share_data(
                        client=client,
                        receivers=["MANAGE"],
                        action="leave",
                        action_type="info",
                        data=gid
                    )
                    project_text = general_link(glovar.project_name, glovar.project_link)
                    debug_text = (f"{lang('project')}{lang('colon')}{project_text}\n"
                                  f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                                  f"{lang('group_id')}{lang('colon')}{code(gid)}\n"
                                  f"{lang('status')}{lang('colon')}{code(lang('leave_auto'))}\n"
                                  f"{lang('reason')}{lang('colon')}{code(lang('reason_leave'))}\n")
                    thread(send_message, (client, glovar.debug_channel_id, debug_text))
            except Exception as e:
                logger.warning(f"Update admin in {gid} error: {e}", exc_info=True)

        return True
    except Exception as e:
        logger.warning(f"Update admin error: {e}", exc_info=True)
    finally:
        glovar.locks["admin"].release()

    return False


def update_status(client: Client, the_type: str) -> bool:
    # Update running status to BACKUP
    try:
        share_data(
            client=client,
            receivers=["BACKUP"],
            action="backup",
            action_type="status",
            data={
                "type": the_type,
                "backup": glovar.backup
            }
        )

        return True
    except Exception as e:
        logger.warning(f"Update status error: {e}", exc_info=True)

    return False
