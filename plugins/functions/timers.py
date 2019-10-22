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

from pyrogram import Client

from .. import glovar
from .channel import share_data, share_regex_count
from .etc import code, general_link, lang, thread
from .file import save
from .group import leave_group
from .telegram import get_admins, get_group_info, send_message

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


def reset_data(client: Client) -> bool:
    # Reset user data every month
    try:
        glovar.bad_ids = {
            "channels": set(),
            "users": set()
        }
        save("bad_ids")

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
