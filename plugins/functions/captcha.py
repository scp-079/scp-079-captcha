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
from random import choice, randint, shuffle
from typing import Optional

from pyrogram import Client, InlineKeyboardButton, InlineKeyboardMarkup, User

from .. import glovar
from .etc import button_data, code, get_full_name, get_now, lang, text_mention
from .file import save
from .group import delete_message
from .user import restrict_user
from .telegram import send_message

# Enable logging
logger = logging.getLogger(__name__)


def add_wait(client: Client, gid: int, user: User, mid: int) -> bool:
    # Add user to the wait list
    try:
        # Basic data
        uid = user.id
        name = get_full_name(user)
        now = get_now()

        # Add the user
        glovar.user_ids[uid]["name"] = name
        glovar.user_ids[uid]["wait"][gid] = now
        save("user_ids")

        # Check hint config
        if not glovar.configs[gid].get("hint"):
            return True

        # Generate the hint text
        wait_list = [wid for wid in glovar.user_ids if glovar.user_ids[wid]["wait"].get(gid, 0)]
        count_text = f"{len(wait_list)} {lang('members')}"
        text = f"{lang('wait_user')}{lang('colon')}{code(count_text)}\n"

        for wid in wait_list:
            text += text_mention("\U00002060", wid)

        text += f"{lang('description')}{lang('colon')}{lang('description_hint')}\n"

        # Generate the markup
        markup = get_captcha_markup("hint")

        # Send the message
        result = send_message(client, gid, text, mid, markup)
        if result:
            restrict_user(client, gid, uid)
            glovar.user_ids[uid]["restricted"].add(gid)
            new_id = result.message_id
            old_id, _ = glovar.message_ids[gid]["hint"]
            glovar.message_ids[gid]["hint"] = (new_id, now)
            save("message_ids")
            old_id and delete_message(client, gid, old_id)
        else:
            glovar.user_ids[uid]["wait"].pop(gid, 0)

        save("user_ids")
    except Exception as e:
        logger.warning(f"Add wait error: {e}", exc_info=True)

    return False


def ask_question(client: Client, user: User, mid: int) -> bool:
    # Ask a new question
    try:
        # Basic data
        uid = user.id
        name = get_full_name(user)

        # Get the question data
        the_type = choice(["math"])
        captcha = eval(f"captcha_{the_type}")

        if not captcha:
            return True

        # Generate the question text
        question_text = captcha["question"]
        text = (f"{lang('user_name')}{lang('colon')}{code(name)}\n"
                f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                f"{lang('description')}{lang('colon')}{code(lang('description_ask'))}\n"
                f"{lang('question')}{lang('colon')}{code(question_text)}\n")

        # Generate the markup
        markup = get_captcha_markup("ask", captcha)

        # Send the message
        result = send_message(client, glovar.captcha_group_id, text, mid, markup)
        if result:
            captcha_message_id = result.message_id
            glovar.user_ids[uid]["mid"] = captcha_message_id
        else:
            glovar.user_ids[uid]["wait"] = {}

        save("user_ids")

        return True
    except Exception as e:
        logger.warning(f"Ask question error: {e}", exc_info=True)

    return False


def captcha_math(uid: int) -> dict:
    # Math CAPTCHA
    result = {}
    try:
        operators = ["-", "+"]
        operator = choice(operators)
        num_1 = randint(1, 100)
        num_2 = randint(1, 100)

        question = f"{num_1} {operator} {num_2} = ?"
        answer = str(eval(f"{num_1} {operator} {num_2}"))
        candidates = [answer]

        for _ in range(2):
            candidate = str(randint(-99, 200))

            while candidate in candidates:
                candidate = str(randint(-99, 200))

            candidates.append(candidate)

        shuffle(candidates)

        result = {
            "user_id": uid,
            "question": question,
            "answer": answer,
            "candidates": candidates
        }
    except Exception as e:
        logger.warning(f"Captcha math error: {e}", exc_info=True)

    return result


def get_captcha_markup(the_type: str, captcha: dict = None) -> Optional[InlineKeyboardMarkup]:
    # Get the captcha message's markup
    result = None
    try:
        if the_type == "ask" and captcha:
            uid = captcha["user_id"]
            candidates = captcha["candidates"]
            markup_list = [[]]
            for candidate in candidates:
                button = button_data("answer", candidate, uid)
                markup_list[0][0].append(
                    InlineKeyboardButton(
                        text=candidate,
                        callback_data=button
                    )
                )
        elif the_type == "hint":
            query_data = button_data("hint", "check", None)
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
    except Exception as e:
        logger.warning(f"Get captcha markup error: {e}", exc_info=True)

    return result
