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
from random import choice, randint, sample, shuffle
from typing import Optional

from pyrogram import Client, InlineKeyboardButton, InlineKeyboardMarkup, User

from .. import glovar
from .channel import get_debug_text
from .etc import button_data, code, general_link, get_channel_link, get_full_name, get_now, lang, mention_name
from .etc import mention_text, message_link, thread
from .file import save
from .group import delete_message
from .user import restrict_user, terminate_user, unrestrict_user
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
        restrict_user(client, gid, uid)

        # Check hint config
        if not glovar.configs[gid].get("hint"):
            # Send debug message
            mid_link = f"{get_channel_link(gid)}/{mid}"
            debug_text = get_debug_text(client, gid)
            debug_text += (f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                           f"{lang('action')}{lang('colon')}{code(lang('action_wait'))}\n"
                           f"{lang('triggered_by')}{lang('colon')}{general_link(mid, mid_link)}\n")
            thread(send_message, (client, glovar.debug_channel_id, debug_text))
            return True

        # Generate the hint text
        wait_user_list = [wid for wid in glovar.user_ids if glovar.user_ids[wid]["wait"].get(gid, 0)]
        count_text = f"{len(wait_user_list)} {lang('members')}"
        text = f"{lang('wait_user')}{lang('colon')}{code(count_text)}\n"

        if len(wait_user_list) > glovar.limit_static:
            # Send static hint
            text += (f"{lang('message_type')}{lang('colon')}{code(lang('flood_static'))}\n"
                     f"{lang('description')}{lang('colon')}{code(lang('description_hint'))}\n")
            thread(send_static, (client, gid, text, True))

            # Delete old hint
            old_id, _ = glovar.message_ids[gid]["hint"]
            glovar.message_ids[gid]["hint"] = (0, 0)
            old_id and delete_message(client, gid, old_id) and save("message_ids")

            # Send debug message
            mid_link = f"{get_channel_link(gid)}/{mid}"
            debug_text = get_debug_text(client, gid)
            debug_text += (f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                           f"{lang('action')}{lang('colon')}{code(lang('action_wait'))}\n"
                           f"{lang('triggered_by')}{lang('colon')}{general_link(mid, mid_link)}\n")
            thread(send_message, (client, glovar.debug_channel_id, debug_text))

            return True

        if len(wait_user_list) > glovar.limit_mention:
            wait_user_list = sample(wait_user_list, glovar.limit_mention)

        for wid in wait_user_list:
            text += mention_text("\U00002060", wid)

        text += f"{lang('description')}{lang('colon')}{code(lang('description_hint'))}\n"

        # Generate the markup
        markup = get_captcha_markup("hint")

        # Send the message
        result = send_message(client, gid, text, mid, markup)
        if result:
            # Update hint message id
            new_id = result.message_id
            old_id, _ = glovar.message_ids[gid]["hint"]
            glovar.message_ids[gid]["hint"] = (new_id, now)
            old_id and delete_message(client, gid, old_id)

            # Update auto static message id
            old_id = glovar.message_ids[gid]["flood"]
            glovar.message_ids[gid]["flood"] = 0
            old_id and delete_message(client, gid, old_id)

            # Save message ids
            save("message_ids")

            # Send debug message
            debug_text = get_debug_text(client, gid)
            debug_text += (f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                           f"{lang('action')}{lang('colon')}{code(lang('action_wait'))}\n"
                           f"{lang('triggered_by')}{lang('colon')}{general_link(new_id, message_link(result))}\n")
            thread(send_message, (client, glovar.debug_channel_id, debug_text))
        else:
            unrestrict_user(client, gid, uid)
            glovar.user_ids[uid]["wait"].pop(gid, 0)

        save("user_ids")
    except Exception as e:
        logger.warning(f"Add wait error: {e}", exc_info=True)

    return False


def answer_question(client: Client, uid: int, text: str) -> bool:
    # Answer question
    try:
        answer = glovar.user_ids[uid]["answer"]

        if text and answer and text == answer:
            terminate_user(
                client=client,
                the_type="succeed",
                uid=uid
            )
        else:
            glovar.user_ids[uid]["try"] += 1
            save("user_ids")
            if glovar.user_ids[uid]["try"] == glovar.limit_try:
                gid = min(glovar.user_ids[uid]["wait"], key=glovar.user_ids[uid]["wait"].get)
                terminate_user(
                    client=client,
                    the_type="wrong",
                    uid=uid,
                    gid=gid
                )

        return True
    except Exception as e:
        logger.warning(f"Answer question error: {e}", exc_info=True)

    return False


def ask_question(client: Client, user: User, mid: int) -> bool:
    # Ask a new question
    try:
        # Basic data
        uid = user.id
        now = get_now()

        # Get the question data
        the_type = choice(["math"])
        captcha = eval(f"captcha_{the_type}")(uid)

        if not captcha:
            return True

        # Generate the question text
        question_text = captcha["question"]
        text = (f"{lang('user_name')}{lang('colon')}{mention_name(user)}\n"
                f"{lang('user_id')}{lang('colon')}{code(uid)}\n\n"
                f"{lang('description')}{lang('colon')}{code(lang('description_ask'))}\n\n"
                f"{lang('question')}{lang('colon')}{code(question_text)}\n")

        # Generate the markup
        markup = get_captcha_markup("ask", captcha)

        # Send the message
        result = send_message(client, glovar.captcha_group_id, text, mid, markup)
        if result:
            captcha_message_id = result.message_id
            glovar.user_ids[uid]["mid"] = captcha_message_id
            glovar.user_ids[uid]["time"] = now
            glovar.user_ids[uid]["answer"] = captcha["answer"]
        else:
            wait_group_list = list(glovar.user_ids[uid]["wait"])

            for gid in wait_group_list:
                unrestrict_user(client, gid, uid)

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
                markup_list[0].append(
                    InlineKeyboardButton(
                        text=candidate,
                        callback_data=button
                    )
                )

            result = InlineKeyboardMarkup(markup_list)
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


def send_static(client: Client, gid: int, text: str, flood: bool = False) -> bool:
    # Send static message
    try:
        markup = get_captcha_markup("hint")
        result = send_message(client, gid, text, None, markup)
        if result:
            new_id = result.message_id
            old_type = (lambda x: "flood" if x else "static")(flood)
            old_id = glovar.message_ids[gid][old_type]
            old_id and delete_message(client, gid, old_id)
            glovar.message_ids[gid][old_type] = new_id
            save("message_ids")
    except Exception as e:
        logger.warning(f"Send static error: {e}", exc_info=True)

    return False
