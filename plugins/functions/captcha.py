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
from typing import Optional

from pyrogram import Client, InlineKeyboardButton, InlineKeyboardMarkup

from .. import glovar
from .etc import button_data, code, get_now, lang, text_mention, thread
from .telegram import send_message

# Enable logging
logger = logging.getLogger(__name__)


def add_wait(client: Client, gid: int, uid: int, mid: int) -> bool:
    # Add user to the wait list
    try:
        # Add the user
        now = get_now()
        glovar.user_ids[uid]["wait"][gid] = now

        # Check hint config
        if not glovar.configs[gid].get("hint"):
            return True

        # Generate the hint text
        wait_list = list(glovar.user_ids[uid]["wait"])
        count_text = f"{len(wait_list)} {lang('members')}"
        text = f"{lang('wait_user')}{lang('colon')}{code(count_text)}\n"

        for wid in wait_list:
            text += text_mention("\U00002060", wid)

        text += f"{lang('description')}{lang('colon')}{lang('description_captcha')}\n"

        # Generate the markup
        markup = get_captcha_markup("hint")

        # Send the message
        thread(send_message, (client, gid, text, mid, markup))
    except Exception as e:
        logger.warning(f"Add wait error: {e}", exc_info=True)

    return False


def get_captcha_markup(the_type: str, data: dict = None) -> Optional[InlineKeyboardMarkup]:
    # Get the captcha message's markup
    result = None
    try:
        if the_type == "hint":
            query_data = button_data("captcha", "check", None)
            result = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=lang("captcha_check"),
                            callback_data=query_data
                        ),
                        InlineKeyboardButton(
                            text=lang("captcha_go"),
                            url=glovar.captcha_link
                        )
                    ]
                ]
            )
        elif the_type == "verify" and data:
            pass
    except Exception as e:
        logger.warning(f"Get captcha markup error: {e}", exc_info=True)

    return result
