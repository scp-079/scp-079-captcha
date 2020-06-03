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
from json import loads

from pyrogram import Client, CallbackQuery

from .. import glovar
from ..functions.captcha import question_answer, question_change
from ..functions.etc import get_int, get_text, lang, thread
from ..functions.filters import authorized_group, captcha_group, from_user, is_class_e_user, test_group
from ..functions.telegram import answer_callback, edit_message_reply_markup

# Enable logging
logger = logging.getLogger(__name__)


@Client.on_callback_query(~captcha_group & ~test_group & authorized_group)
def check_wait(client: Client, callback_query: CallbackQuery) -> bool:
    # Answer the check query
    result = False

    try:
        # Basic data
        gid = callback_query.message.chat.id
        uid = callback_query.from_user.id
        callback_data = loads(callback_query.data)
        action = callback_data["a"]
        action_type = callback_data["t"]

        if action != "hint":
            return False

        if action_type != "check":
            return False

        # Get the user's status
        user_status = glovar.user_ids.get(uid, {})

        # Generate the answer text
        if user_status and user_status["wait"].get(gid, 0):
            text = lang("check_yes")
        elif user_status and (user_status["pass"].get(gid, 0) or user_status["succeeded"].get(gid, 0)):
            text = lang("check_pass")
        elif is_class_e_user(uid):
            text = lang("check_admin")
        else:
            text = lang("check_no")

        # Answer the callback
        thread(answer_callback, (client, callback_query.id, text, True))

        result = True
    except Exception as e:
        logger.warning(f"Check wait error: {e}", exc_info=True)

    return result


@Client.on_callback_query(from_user)
def example(client: Client, callback_query: CallbackQuery) -> bool:
    # Edit the example message's reply markup
    result = False

    try:
        # Basic data
        cid = callback_query.message.chat.id
        mid = callback_query.message.message_id
        callback_data = loads(callback_query.data)
        action = callback_data["a"]

        # Check the action
        if action != "none":
            return False

        # Edit the message
        thread(edit_message_reply_markup, (client, cid, mid, None))
    except Exception as e:
        logger.warning(f"Example error: {e}", exc_info=True)

    return result


@Client.on_callback_query(captcha_group)
def question(client: Client, callback_query: CallbackQuery) -> bool:
    # Answer the question query
    result = False

    glovar.locks["message"].acquire()

    try:
        # Basic data
        uid = callback_query.from_user.id
        callback_data = loads(callback_query.data)
        action = callback_data["a"]
        action_type = callback_data["t"]
        data = callback_data["d"]

        # Check action
        if action != "q":
            return True

        # Get the user id
        message = callback_query.message
        message_text = get_text(message)
        oid = get_int(message_text.split("\n")[1].split(lang("colon"))[1])

        # Check permission
        if not oid or uid != oid:
            return True

        # Check user status
        if not glovar.user_ids.get(uid, {}) or not glovar.user_ids[uid]["answer"]:
            return True

        # Answer the question
        if action_type == "a":
            text = data
            question_answer(client, uid, text)

        # Change the question
        elif action_type == "c":
            mid = message.message_id
            question_change(client, uid, mid)

        # Answer the callback
        thread(answer_callback, (client, callback_query.id, ""))

        result = True
    except Exception as e:
        logger.warning(f"Question error: {e}", exc_info=True)
    finally:
        glovar.locks["message"].release()

    return result
