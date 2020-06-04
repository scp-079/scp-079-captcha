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
from copy import deepcopy
from time import sleep
from typing import Dict

from pyrogram import Client

from .. import glovar
from .channel import share_data, share_regex_count
from .decorators import threaded
from .etc import code, general_link, get_now, get_readable_time, lang, thread
from .file import file_tsv, save
from .filters import is_class_e_user, is_flooded
from .group import delete_hint, leave_group, save_admins
from .telegram import export_chat_invite_link, get_admins, get_group_info
from .telegram import get_members, send_message
from .user import check_timeout_user, forgive_users, kick_user, lift_ban, remove_group_user, unban_user

# Enable logging
logger = logging.getLogger(__name__)


@threaded()
def backup_files(client: Client) -> bool:
    # Backup data files to BACKUP
    result = False

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

        result = True
    except Exception as e:
        logger.warning(f"Backup error: {e}", exc_info=True)

    return result


def clear_blacklist(client: Client) -> bool:
    # Clear CAPTCHA group banned members
    result = False

    try:
        members = get_members(client, glovar.captcha_group_id, "kicked")

        if not members:
            return False

        for member in members:
            if not member.restricted_by or not member.restricted_by.is_self:
                continue

            user = member.user
            uid = user.id
            unban_user(client, glovar.captcha_group_id, uid, lock=True)

        result = True
    except Exception as e:
        logger.warning(f"Clear blacklist error: {e}", exc_info=True)

    return result


def clear_members(client: Client) -> bool:
    # Clear CAPTCHA group members
    result = False

    try:
        members = get_members(client, glovar.captcha_group_id, "all")

        if not members:
            return False

        for member in members:
            user = member.user

            if is_class_e_user(user):
                continue

            uid = user.id
            user_data = glovar.user_ids.get(uid, {})

            if user_data and (user_data.get("wait") or user_data.get("time")):
                continue

            kick_user(client, glovar.captcha_group_id, uid, lock=True)

        result = True
    except Exception as e:
        logger.warning(f"Clear members error: {e}", exc_info=True)

    return result


def interval_hour_01() -> bool:
    # Execute every hour
    result = False

    glovar.locks["config"].acquire()

    try:
        # Basic data
        now = get_now()

        # Clear starts data
        for key in list(glovar.starts):
            if glovar.starts[key]["until"] > now:
                continue

            glovar.starts.pop(key, {})

        save("starts")

        result = True
    except Exception as e:
        logger.warning(f"Interval hour 01 error: {e}", exc_info=True)
    finally:
        glovar.locks["config"].release()

    return result


def interval_min_01(client: Client) -> bool:
    # Execute every minute
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        now = get_now()

        # Check users
        for uid in list(glovar.user_ids):
            # Remove users from the CAPTCHA group
            remove_group_user(client, uid, now)

            # Terminate timeout users
            check_timeout_user(client, uid, now)

            # Lift the ban on users
            lift_ban(client, uid, now)

        # Save the user_ids
        save("user_ids")

        # Clear changed ids
        glovar.changed_ids = set()

        # Check the flood status
        for gid in list(glovar.pinned_ids):
            # Basic data
            start = glovar.pinned_ids[gid]["start"]
            last = glovar.pinned_ids[gid]["last"]

            # Check pinned status
            if not start:
                continue

            # Check normal time
            if now - last < glovar.time_captcha * 3:
                continue

            # Check confirm status
            if gid in glovar.flooded_ids:
                continue

            # Get group's waiting user list
            wait_user_list = [wid for wid in glovar.user_ids if glovar.user_ids[wid]["wait"].get(gid, 0)]

            # Flood situation ongoing
            if len(wait_user_list) > glovar.limit_flood:
                continue

            # Ask for help
            glovar.flooded_ids.add(gid)
            save("flooded_ids")
            share_data(
                client=client,
                receivers=["USER"],
                action="help",
                action_type="confirm",
                data={
                    "group_id": gid,
                    "begin": now - glovar.time_captcha * 3,
                    "end": now,
                    "limit": glovar.limit_flood
                }
            )

        # Delete hint messages
        delete_hint(client)

        result = True
    except Exception as e:
        logger.warning(f"Interval min 01 error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


def interval_min_10(client: Client) -> bool:
    # Execute every 10 minutes
    result = False

    try:
        # Clear blacklist
        clear_blacklist(client)

        # Clear members
        clear_members(client)

        # New invite link
        new_invite_link(client)

        result = True
    except Exception as e:
        logger.warning(f"Interval min 10 error: {e}", exc_info=True)

    return result


def new_invite_link(client: Client, manual: bool = False) -> bool:
    # Generate new invite link
    result = False

    glovar.locks["invite"].acquire()

    try:
        # Basic data
        now = get_now()

        # Check flood status
        if any(is_flooded(gid) for gid in list(glovar.configs)):
            return False

        # Copy the data
        with glovar.locks["message"]:
            user_ids = deepcopy(glovar.user_ids)

        # Check if there is a waiting
        if any(user_ids[uid]["wait"] for uid in user_ids):
            return False

        # Check the link time
        if not manual and now - glovar.invite.get("time", 0) < glovar.time_invite:
            return False

        # Generate link
        link = export_chat_invite_link(client, glovar.captcha_group_id)

        if not link:
            return False

        glovar.invite["link"] = link
        save("invite")

        result = True
    except Exception as e:
        logger.warning(f"New invite link error: {e}", exc_info=True)
    finally:
        glovar.locks["invite"].release()

    return result


def reset_data(client: Client) -> bool:
    # Reset user data every month
    result = False

    glovar.locks["message"].acquire()

    try:
        glovar.bad_ids = {
            "users": set()
        }
        save("bad_ids")

        glovar.left_group_ids = set()
        save("left_group_ids")

        forgive_users(client)
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

        result = True
    except Exception as e:
        logger.warning(f"Reset data error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result


def send_count(client: Client) -> bool:
    # Send regex count to REGEX
    result = False

    glovar.locks["regex"].acquire()

    try:
        for word_type in glovar.regex:
            share_regex_count(client, word_type)
            word_list = list(eval(f"glovar.{word_type}_words"))

            for word in word_list:
                eval(f"glovar.{word_type}_words")[word] = 0

            save(f"{word_type}_words")

        result = True
    except Exception as e:
        logger.warning(f"Send count error: {e}", exc_info=True)
    finally:
        glovar.locks["regex"].release()

    return result


@threaded()
def share_failed_users(client: Client, data: Dict[str, int] = None) -> bool:
    # Share failed users
    result = False

    glovar.locks["failed"].acquire()

    try:
        # Check the config
        if not glovar.failed:
            return True

        # User list
        users = list(glovar.failed_ids)

        # Check the list
        if not users:
            return True

        # Init data
        lines = []

        # Get users
        for uid in users:
            username = glovar.failed_ids[uid]["username"]
            first_name = glovar.failed_ids[uid]["first"]
            last_name = glovar.failed_ids[uid]["last"]
            bio = glovar.failed_ids[uid]["bio"]
            reason = glovar.failed_ids[uid]["reason"]
            lines.append([username, first_name, last_name, bio, reason])

        # Save the tsv file
        file = file_tsv(
            first_line=["username", "first name", "last name", "bio", "reason"],
            lines=lines,
            prefix=f"CAPTCHA-FAILED-{get_readable_time()}-"
        )
        share_data(
            client=client,
            receivers=["REGEX"],
            action="captcha",
            action_type="result",
            data=data,
            file=file,
            encrypt=False
        )

        # Reset data
        if data and data["admin_id"]:
            return True

        glovar.failed_ids = {}
        save("failed_ids")

        result = True
    except Exception as e:
        logger.warning(f"Share failed users error: {e}", exc_info=True)
    finally:
        glovar.locks["failed"].release()

    return result


def update_admins(client: Client) -> bool:
    # Update admin list every day
    result = False

    glovar.locks["admin"].acquire()

    try:
        # Basic data
        group_list = list(glovar.admin_ids)

        # Check groups
        for gid in group_list:
            group_name, group_link = get_group_info(client, gid)
            admin_members = get_admins(client, gid)

            # Bot is not in the chat, leave automatically without approve
            if admin_members is False or any(admin.user.is_self for admin in admin_members) is False:
                leave_group(client, gid)
                share_data(
                    client=client,
                    receivers=["MANAGE"],
                    action="leave",
                    action_type="info",
                    data={
                        "group_id": gid,
                        "group_name": group_name,
                        "group_link": group_link
                    }
                )
                project_text = general_link(glovar.project_name, glovar.project_link)
                debug_text = (f"{lang('project')}{lang('colon')}{project_text}\n"
                              f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                              f"{lang('group_id')}{lang('colon')}{code(gid)}\n"
                              f"{lang('status')}{lang('colon')}{code(lang('leave_auto'))}\n"
                              f"{lang('reason')}{lang('colon')}{code(lang('reason_leave'))}\n")
                thread(send_message, (client, glovar.debug_channel_id, debug_text))
                continue

            # Check the admin list
            if not (admin_members and any([admin.user.is_self for admin in admin_members])):
                continue

            # Save the admin list
            save_admins(gid, admin_members)

            # Ignore the group
            if gid in glovar.lack_group_ids:
                continue

            # Check the permissions
            if glovar.user_id not in glovar.admin_ids[gid]:
                reason = "user"
            elif any(admin.user.is_self
                     and admin.can_delete_messages
                     and admin.can_restrict_members
                     and admin.can_pin_messages
                     for admin in admin_members):
                glovar.lack_group_ids.discard(gid)
                save("lack_group_ids")
                continue
            else:
                reason = "permissions"
                glovar.lack_group_ids.add(gid)
                save("lack_group_ids")

            # Send the leave request
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

        result = True
    except Exception as e:
        logger.warning(f"Update admin error: {e}", exc_info=True)
    finally:
        glovar.locks["admin"].release()

    return result


def update_status(client: Client, the_type: str) -> bool:
    # Update running status to BACKUP
    result = False

    try:
        result = share_data(
            client=client,
            receivers=["BACKUP"],
            action="backup",
            action_type="status",
            data={
                "type": the_type,
                "backup": glovar.backup
            }
        )
    except Exception as e:
        logger.warning(f"Update status error: {e}", exc_info=True)

    return result
