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

from pyrogram import Client, Message

from .etc import code, delay, lang
from .filters import is_class_c
from .group import delete_message
from .telegram import send_report_message

# Enable logging
logger = logging.getLogger(__name__)


def delete_normal_command(client: Client, message: Message) -> bool:
    # Delete normal command
    result = False

    try:
        # Basic data
        gid = message.chat.id
        mid = message.message_id

        # Delete the command
        result = delete_message(client, gid, mid)
    except Exception as e:
        logger.warning(f"Delete normal command error: {e}", exc_info=True)

    return result


def delete_shared_command(client: Client, message: Message) -> bool:
    # Delete shared command
    result = False

    try:
        # Basic data
        gid = message.chat.id
        mid = message.message_id

        # Delete the command
        if is_class_c(None, message):
            delay(3, delete_message, [client, gid, mid])
        else:
            delete_message(client, gid, mid)

        result = True
    except Exception as e:
        logger.warning(f"Delete shared command error: {e}", exc_info=True)

    return result


def command_flood(client: Client, message: Message) -> bool:
    # Command flood
    result = False

    try:
        # Basic data
        gid = message.chat.id
        aid = message.from_user.id

        # Send the report message
        text = (f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('config_change'))}\n"
                f"{lang('status')}{lang('colon')}{code(lang('status_failed'))}\n"
                f"{lang('reason')}{lang('colon')}{code(lang('command_flood'))}\n")
        result = send_report_message(10, client, gid, text)
    except Exception as e:
        logger.warning(f"Command flood error: {e}", exc_info=True)

    return result
