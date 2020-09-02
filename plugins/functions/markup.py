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
from typing import Dict, List, Optional, Tuple, Union

from pyrogram.types import CallbackGame, InlineKeyboardButton, InlineKeyboardMarkup

from .etc import get_length

# Enable logging
logger = logging.getLogger(__name__)


def get_inline(buttons: List[Dict[str, Union[str, bytes, CallbackGame, None]]]) -> Optional[InlineKeyboardMarkup]:
    # Get a inline reply markup
    result = None

    try:
        if not buttons:
            return None

        length = len(buttons)

        if length > 6:
            return None

        markup_list: List[List[InlineKeyboardButton]] = [[]]

        for button in buttons:
            text = button.get("text")
            data = button.get("data")
            url = button.get("url")
            switch_inline_query = button.get("switch_inline_query")
            switch_inline_query_current_chat = button.get("switch_inline_query_current_chat")
            callback_game = button.get("callback_game")

            if length <= 6 and (length % 3) and not (length % 2) and len(markup_list[-1]) == 2:
                markup_list.append([])

            elif len(markup_list[-1]) == 3:
                markup_list.append([])

            elif (len(markup_list[-1]) == 2
                  and get_length(text) <= 12
                  and all(get_length(m.text) <= 12 for m in markup_list[-1])):
                pass

            elif (len(markup_list[-1]) == 1
                  and get_length(text) <= 18
                  and get_length(markup_list[-1][-1].text) <= 18):
                pass

            elif markup_list[-1]:
                markup_list.append([])

            markup_list[-1].append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=data,
                    url=url,
                    switch_inline_query=switch_inline_query,
                    switch_inline_query_current_chat=switch_inline_query_current_chat,
                    callback_game=callback_game
                )
            )

        result = InlineKeyboardMarkup(markup_list)
    except Exception as e:
        logger.warning(f"Get inline error: {e}", exc_info=True)

    return result


def get_text_and_markup(text: str) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    # Get inline markup from text
    result = (text, None)

    try:
        # Check the text
        if not text or not text.strip():
            return text, None

        # Get text list
        text = text.strip()
        text_list = [t for t in text.split("\n++++++\n") if t]

        # Check the text list
        if not text_list or len(text_list) != 2:
            return text, None

        # Get buttons
        text = text_list[0]
        buttons_text = text_list[1]
        button_list = [b.strip() for b in buttons_text.split("\n") if b.strip()]
        buttons = []

        for button in button_list:
            button = [b.strip() for b in button.split("||") if b.strip()]

            if len(button) != 2:
                return text, None

            button_text = button[0]
            button_url = button[1]

            if button_url.startswith("@") or " " in button_url:
                return text, None

            buttons.append(
                {
                    "text": button_text,
                    "url": button_url
                }
            )

        # Get markup
        result = (text, get_inline(buttons))
    except Exception as e:
        logger.warning(f"Get text and markup error: {e}", exc_info=True)

    return result
