# SCP-079-CAPTCHA - Provide challenges for new joined members
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
from random import choice, randint, sample, shuffle
from string import ascii_lowercase
from typing import Optional

from captcha.image import ImageCaptcha
from claptcha import Claptcha
from pyrogram import Client, InlineKeyboardButton, InlineKeyboardMarkup, Message, User

from .. import glovar
from .channel import ask_help_welcome, get_debug_text
from .etc import button_data, code, general_link, get_channel_link, get_full_name, get_now, lang, mention_name
from .etc import mention_text, message_link, t2t, thread
from .file import delete_file, get_new_path, save
from .filters import is_class_d_user, is_declared_message, is_limited_user, is_nm_text, is_watch_user, is_wb_text
from .group import delete_message, get_pinned
from .ids import init_user_id
from .user import restrict_user, terminate_user, unrestrict_user
from .telegram import delete_messages, edit_message_photo, pin_chat_message
from .telegram import send_message, send_photo, send_report_message

# Enable logging
logger = logging.getLogger(__name__)


def add_wait(client: Client, gid: int, user: User, mid: int, aid: int = 0) -> bool:
    # Add user to the wait list
    try:
        # Basic data
        uid = user.id
        name = get_full_name(user)
        now = get_now()

        # Add the user
        glovar.user_ids[uid]["name"] = name
        glovar.user_ids[uid]["wait"][gid] = now
        aid and glovar.user_ids[uid]["manual"].add(gid)
        save("user_ids")

        # Get group's waiting user list
        wait_user_list = [wid for wid in glovar.user_ids if glovar.user_ids[wid]["wait"].get(gid, 0)]

        # Work with NOSPAM
        if len(wait_user_list) < glovar.limit_mention and glovar.nospam_id in glovar.admin_ids[gid]:
            # Check name
            name = get_full_name(user, True, True)

            if name and is_nm_text(name):
                glovar.user_ids[uid]["wait"] = {}
                glovar.user_ids[uid]["manual"] = set()
                save("user_ids")
                return True

        # Restrict the user
        restrict_user(client, gid, uid)

        # Check hint config
        if not glovar.configs[gid].get("hint"):
            # Send debug message
            mid_link = f"{get_channel_link(gid)}/{mid}"
            debug_text = get_debug_text(client, gid)
            debug_text += (f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                           f"{lang('action')}{lang('colon')}{code(lang('action_wait'))}\n")

            if aid:
                debug_text += f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"

            debug_text += f"{lang('triggered_by')}{lang('colon')}{general_link(mid, mid_link)}\n"
            thread(send_message, (client, glovar.debug_channel_id, debug_text))
            return True

        # Generate the hint text prefix
        count_text = f"{len(wait_user_list)} {lang('members')}"
        text = f"{lang('wait_user')}{lang('colon')}{code(count_text)}\n"

        # Choose the users to mention
        if len(wait_user_list) > glovar.limit_mention:
            mention_user_list = sample(wait_user_list, glovar.limit_mention)
        else:
            mention_user_list = wait_user_list

        # Mention previous users text
        mention_users_text = "".join(mention_text("\U00002060", wid) for wid in mention_user_list)

        # Flood situation
        if len(wait_user_list) > glovar.limit_static:
            # Send static hint
            text += f"{lang('message_type')}{lang('colon')}{code(lang('flood_static'))}\n"
            text += mention_users_text
            text += f"{lang('description')}{lang('colon')}{code(lang('description_hint'))}\n"

            if glovar.configs[gid].get("pin"):
                thread(send_pin, (client, gid, now))
            else:
                thread(send_static, (client, gid, text, True))

            # Delete old hint
            old_id = glovar.message_ids[gid]["hint"]
            glovar.message_ids[gid]["hint"] = 0
            old_id and delete_message(client, gid, old_id)
            save("message_ids")

            # Delete joined message
            delete_message(client, gid, mid)

            # Send debug message
            mid_link = f"{get_channel_link(gid)}/{mid}"
            debug_text = get_debug_text(client, gid)
            debug_text += (f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                           f"{lang('action')}{lang('colon')}{code(lang('action_wait'))}\n")

            if aid:
                debug_text += f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"

            debug_text += f"{lang('triggered_by')}{lang('colon')}{general_link(mid, mid_link)}\n"
            thread(send_message, (client, glovar.debug_channel_id, debug_text))

            return True

        # Generate the hint text
        text += mention_users_text

        if aid == glovar.nospam_id:
            description = lang("description_nospam")
        elif aid:
            description = lang("description_captcha")
        else:
            description = lang("description_hint")

        text += f"{lang('description')}{lang('colon')}{code(description)}\n"

        # Generate the markup
        markup = get_captcha_markup(the_type="hint")

        # Send the message
        result = send_message(client, gid, text, mid, markup)

        # Check if the message was sent successfully
        if result:
            # Update hint message id, delete old message
            new_id = result.message_id
            old_id = glovar.message_ids[gid]["hint"]
            glovar.message_ids[gid]["hint"] = new_id
            old_id and delete_message(client, gid, old_id)

            # Delete static messages
            old_ids = glovar.message_ids[gid]["flood"]
            old_ids and thread(delete_messages, (client, gid, old_ids))
            glovar.message_ids[gid]["flood"] = set()

            # Save message ids
            save("message_ids")

            # Send debug message
            debug_text = get_debug_text(client, gid)
            debug_text += (f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                           f"{lang('action')}{lang('colon')}{code(lang('action_wait'))}\n")

            if aid:
                debug_text += f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"

            debug_text += f"{lang('triggered_by')}{lang('colon')}{general_link(new_id, message_link(result))}\n"
            thread(send_message, (client, glovar.debug_channel_id, debug_text))
        else:
            unrestrict_user(client, gid, uid)
            glovar.user_ids[uid]["wait"].pop(gid, 0)
            aid and glovar.user_ids[uid]["manual"].discard(gid)

        save("user_ids")
    except Exception as e:
        logger.warning(f"Add wait error: {e}", exc_info=True)

    return False


def question_answer(client: Client, uid: int, text: str) -> bool:
    # Answer the question
    try:
        answer = glovar.user_ids[uid].get("answer")
        limit = glovar.user_ids[uid].get("limit")

        if text:
            text = text.lower()
            text = t2t(text, True, True)

        if answer:
            answer = answer.lower()
            answer = t2t(answer, True, True)

        if text and answer and text == answer:
            question_status(client, uid, "succeed")
            terminate_user(
                client=client,
                the_type="succeed",
                uid=uid
            )
        else:
            glovar.user_ids[uid]["try"] += 1
            save("user_ids")

            if glovar.user_ids[uid]["try"] < limit:
                question_status(client, uid, "again")
                return True

            gid = min(glovar.user_ids[uid]["wait"], key=glovar.user_ids[uid]["wait"].get)
            question_status(client, uid, "wrong")
            terminate_user(
                client=client,
                the_type="wrong",
                uid=uid,
                gid=gid
            )

        return True
    except Exception as e:
        logger.warning(f"Question answer error: {e}", exc_info=True)

    return False


def question_ask(client: Client, user: User, mid: int) -> bool:
    # Ask a new question
    try:
        # Basic data
        uid = user.id
        now = get_now()

        # Get the question data
        if glovar.zh_cn:
            question_type = choice(glovar.question_types["chinese"])
        else:
            question_type = choice(glovar.question_types["english"])

        captcha = eval(f"captcha_{question_type}")()

        # Get limit
        limit = captcha["limit"]
        limit = limit or 1

        # Generate the question text
        question_text = captcha["question"]
        text = (f"{lang('user_name')}{lang('colon')}{mention_name(user)}\n"
                f"{lang('user_id')}{lang('colon')}{code(uid)}\n\n"
                f"{lang('description')}{lang('colon')}{code(lang('description_ask').format(limit))}\n\n"
                f"{lang('question')}{lang('colon')}{code(question_text)}\n")

        # Generate the markup
        markup = get_captcha_markup(the_type="ask", captcha=captcha, question_type=question_type)

        # Get the image
        image_path = captcha.get("image")

        # Send the question message
        if image_path:
            result = send_photo(
                client=client,
                cid=glovar.captcha_group_id,
                photo=image_path,
                caption=text,
                mid=mid,
                markup=markup
            )
            image_path.startswith("tmp/") and thread(delete_file, (image_path,))
        else:
            result = send_message(
                client=client,
                cid=glovar.captcha_group_id,
                text=text,
                mid=mid,
                markup=markup
            )

        # Check if the message was sent successfully
        if result:
            captcha_message_id = result.message_id
            glovar.user_ids[uid]["type"] = question_type
            glovar.user_ids[uid]["mid"] = captcha_message_id
            glovar.user_ids[uid]["time"] = now
            glovar.user_ids[uid]["answer"] = captcha["answer"]
            glovar.user_ids[uid]["limit"] = limit
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


def question_change(client: Client, uid: int, mid: int) -> bool:
    # Change the question
    try:
        # Basic data
        name = glovar.user_ids[uid]["name"]
        limit = glovar.user_ids[uid]["limit"]
        tried = glovar.user_ids[uid]["try"]

        # Check limit
        if tried >= limit:
            return True

        # Check changed status
        if uid not in glovar.changed_ids:
            glovar.changed_ids.add(uid)
        else:
            return True

        # Get the question data
        if glovar.zh_cn:
            question_type = choice(glovar.question_types["chinese"])
        else:
            question_type = choice(glovar.question_types["english"])

        captcha = eval(f"captcha_{question_type}")()

        # Get limit
        limit = limit - tried - 1
        limit = limit or 1

        # Generate the question text
        question_text = captcha["question"]
        text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                f"{lang('user_id')}{lang('colon')}{code(uid)}\n\n"
                f"{lang('description')}{lang('colon')}{code(lang('description_ask').format(limit))}\n\n"
                f"{lang('question')}{lang('colon')}{code(question_text)}\n")

        # Generate the markup
        markup = get_captcha_markup(the_type="ask", captcha=captcha)

        # Get the image
        image_path = captcha.get("image") or "assets/none.png"

        # Edit the question message
        result = edit_message_photo(
            client=client,
            cid=glovar.captcha_group_id,
            mid=mid,
            photo=image_path,
            caption=text,
            markup=markup
        )
        image_path.startswith("tmp/") and thread(delete_file, (image_path,))

        # Check if the message was edited successfully
        if result:
            glovar.user_ids[uid]["type"] = question_type
            glovar.user_ids[uid]["answer"] = captcha["answer"]
            glovar.user_ids[uid]["limit"] = limit
            glovar.user_ids[uid]["try"] = 0

        save("user_ids")

        return True
    except Exception as e:
        logger.warning(f"Question change error: {e}", exc_info=True)

    return False


def question_status(client: Client, uid: int, the_type: str) -> bool:
    # Reply question status
    try:
        # Decide the description
        if the_type == "again":
            description = lang("description_again")
        elif the_type == "succeed":
            description = lang("description_succeed")
        elif the_type == "wrong":
            description = lang("description_wrong")
        else:
            description = ""

        # Send the report message
        name = glovar.user_ids[uid]["name"]
        mid = glovar.user_ids[uid]["mid"]
        text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                f"{lang('description')}{lang('colon')}{code(description)}\n")
        thread(send_report_message, (10, client, glovar.captcha_group_id, text, mid))

        return True
    except Exception as e:
        logger.warning(f"Question status error: {e}", exc_info=True)

    return False


def captcha_chengyu() -> dict:
    # Chengyu CAPTCHA
    result = {}
    try:
        question = choice(glovar.chinese_words["chengyu"])
        answer = question

        image = ImageCaptcha(width=300, height=150, fonts=[glovar.font_chinese])
        image_path = f"{get_new_path('.png')}"
        image.write(question, image_path)

        result = {
            "image": image_path,
            "question": lang("question_chengyu"),
            "answer": answer,
            "limit": glovar.limit_try
        }
    except Exception as e:
        logger.warning(f"Captcha chengyu error: {e}", exc_info=True)

    return result


def captcha_food() -> dict:
    # Food CAPTCHA
    result = {}
    try:
        question = choice(glovar.chinese_words["food"])
        answer = question
        candidates = [answer]

        for _ in range(2):
            candidate = choice(glovar.chinese_words["food"])

            while candidate in candidates:
                candidate = choice(glovar.chinese_words["food"])

            candidates.append(candidate)

        shuffle(candidates)

        image = ImageCaptcha(width=300, height=150, fonts=[glovar.font_chinese])
        image_path = f"{get_new_path('.png')}"
        image.write(question, image_path)

        result = {
            "image": image_path,
            "question": lang("question_food"),
            "answer": answer,
            "candidates": candidates,
            "limit": glovar.limit_try - 1
        }
    except Exception as e:
        logger.warning(f"Captcha food error: {e}", exc_info=True)

    return result


def captcha_letter() -> dict:
    # Letter CAPTCHA
    result = {}
    try:
        question = ""

        for _ in range(randint(3, 6)):
            question += choice(ascii_lowercase)

        answer = question

        image = Claptcha(source=question, font=glovar.font_english, size=(300, 150), noise=glovar.noise)
        image_path = f"{get_new_path('.png')}"
        image.write(image_path)

        result = {
            "image": image_path,
            "question": lang("question_letter"),
            "answer": answer,
            "limit": glovar.limit_try + 1
        }
    except Exception as e:
        logger.warning(f"Captcha letter error: {e}", exc_info=True)

    return result


def captcha_math() -> dict:
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
            "question": question,
            "answer": answer,
            "candidates": candidates,
            "limit": glovar.limit_try
        }
    except Exception as e:
        logger.warning(f"Captcha math error: {e}", exc_info=True)

    return result


def captcha_math_pic() -> dict:
    # Math picture CAPTCHA
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

        image = ImageCaptcha(width=300, height=150, fonts=[glovar.font_number])
        image_path = f"{get_new_path('.png')}"
        image.write(question, image_path)

        result = {
            "image": image_path,
            "question": lang("question_math_pic"),
            "answer": answer,
            "candidates": candidates,
            "limit": glovar.limit_try
        }
    except Exception as e:
        logger.warning(f"Captcha math pic error: {e}", exc_info=True)

    return result


def captcha_pic() -> dict:
    # Picture CAPTCHA
    result = {}
    try:
        answer = choice(list(glovar.pics))
        question = choice(glovar.pics[answer])
        candidates = [answer]

        for _ in range(2):
            candidate = choice(list(glovar.pics))

            while candidate in candidates:
                candidate = choice(list(glovar.pics))

            candidates.append(candidate)

        shuffle(candidates)

        image_path = question

        result = {
            "image": image_path,
            "question": lang("question_pic"),
            "answer": answer,
            "candidates": candidates,
            "limit": glovar.limit_try
        }
    except Exception as e:
        logger.warning(f"Captcha pic error: {e}", exc_info=True)

    return result


def captcha_number() -> dict:
    # Number CAPTCHA
    result = {}
    try:
        question = ""

        for _ in range(randint(3, 6)):
            question += str(randint(0, 9))

        answer = question

        image = Claptcha(source=question, font=glovar.font_number, size=(300, 150), noise=glovar.noise)
        image_path = f"{get_new_path('.png')}"
        image.write(image_path)

        result = {
            "image": image_path,
            "question": lang("question_number"),
            "answer": answer,
            "limit": glovar.limit_try + 1
        }
    except Exception as e:
        logger.warning(f"Captcha number error: {e}", exc_info=True)

    return result


def get_captcha_markup(the_type: str, captcha: dict = None, question_type: str = "",
                       static: bool = False) -> Optional[InlineKeyboardMarkup]:
    # Get the captcha message's markup
    result = None
    try:
        # Question markup
        if the_type == "ask" and captcha:
            markup_list = []

            # Candidates buttons
            candidates = captcha.get("candidates")

            if candidates:
                markup_list.append([])

                for candidate in candidates:
                    button = button_data("q", "a", candidate)
                    markup_list[0].append(
                        InlineKeyboardButton(
                            text=candidate,
                            callback_data=button
                        )
                    )

            # Change button
            if question_type and question_type in glovar.question_types["changeable"]:
                button = button_data("q", "c", question_type)
                markup_list.append(
                    [
                        InlineKeyboardButton(
                            text=lang("question_change"),
                            callback_data=button
                        )
                    ]
                )

            if not markup_list:
                return None

            result = InlineKeyboardMarkup(markup_list)

        # Hint markup
        elif the_type == "hint":
            query_data = button_data("hint", "check", None)

            if static:
                captcha_link = glovar.captcha_link
            elif glovar.locks["invite"].acquire(blocking=False):
                captcha_link = glovar.invite["link"]
                glovar.locks["invite"].release()
            else:
                captcha_link = glovar.captcha_link

            result = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=lang("captcha_check"),
                            callback_data=query_data
                        ),
                        InlineKeyboardButton(
                            text=lang("captcha_go"),
                            url=captcha_link
                        )
                    ]
                ]
            )
    except Exception as e:
        logger.warning(f"Get captcha markup error: {e}", exc_info=True)

    return result


def send_pin(client: Client, gid: int, now: int) -> bool:
    # Send pin message
    glovar.locks["pin"].acquire()
    try:
        if not glovar.pinned_ids[gid]["start"]:
            glovar.pinned_ids[gid]["start"] = now

        glovar.pinned_ids[gid]["time"] = now
        save("pinned_ids")

        if glovar.pinned_ids[gid]["new_id"]:
            return True

        text = f"{lang('description')}{lang('colon')}{code(lang('description_hint'))}\n"
        markup = get_captcha_markup(the_type="hint", static=True)
        result = send_message(client, gid, text, None, markup)

        if not result:
            return False

        new_id = result.message_id
        old_ids = glovar.message_ids[gid]["flood"]
        old_ids and delete_messages(client, gid, old_ids)

        pinned_message = get_pinned(client, gid)

        if pinned_message:
            old_id = pinned_message.message_id
        else:
            old_id = 0

        result = pin_chat_message(client, gid, new_id)

        if not result:
            return False

        glovar.pinned_ids[gid]["new_id"] = new_id
        glovar.pinned_ids[gid]["old_id"] = old_id
        save("pinned_ids")

        return True
    except Exception as e:
        logger.warning(f"Send pin error: {e}", exc_info=True)
    finally:
        glovar.locks["pin"].release()

    return False


def send_static(client: Client, gid: int, text: str, flood: bool = False) -> bool:
    # Send static message
    try:
        markup = get_captcha_markup(the_type="hint", static=True)
        result = send_message(client, gid, text, None, markup)

        if not result:
            return False

        new_id = result.message_id

        if flood:
            old_ids = glovar.message_ids[gid]["flood"]
            old_ids and delete_messages(client, gid, old_ids)
            glovar.message_ids[gid]["flood"].add(new_id)
        else:
            old_id = glovar.message_ids[gid]["static"]
            old_id and delete_message(client, gid, old_id)
            glovar.message_ids[gid]["static"] = new_id

        save("message_ids")

        return True
    except Exception as e:
        logger.warning(f"Send static error: {e}", exc_info=True)

    return False


def user_captcha(client: Client, message: Optional[Message], gid: int, user: User, mid: int, now: int,
                 aid: int = 0) -> bool:
    # User CAPTCHA
    try:
        # Basic data
        uid = user.id

        # Check if the user is Class D personnel
        if is_class_d_user(user):
            return True

        # Init the user's status
        if not init_user_id(uid):
            return True

        # Get user status
        user_status = glovar.user_ids[uid]

        # Check pass list
        pass_time = user_status["pass"].get(gid, 0)

        if pass_time:
            return True

        # Check wait list
        wait_time = user_status["wait"].get(gid, 0)

        if wait_time:
            return True

        # Check succeeded list
        succeeded_time = user_status["succeeded"].get(gid, 0)

        if now - succeeded_time < glovar.time_recheck:
            return True

        # Check name
        name = get_full_name(user, True, True)
        wb_name = is_wb_text(name, False)

        # Auto pass
        if user_status["succeeded"] and not wb_name:
            succeeded_time = max(user_status["succeeded"].values())

            if succeeded_time and now - succeeded_time < glovar.time_remove + 70:
                not aid and ask_help_welcome(client, uid, [gid], mid)
                return True

            if glovar.configs[gid].get("pass"):
                if (succeeded_time and now - succeeded_time < glovar.time_recheck
                        and not is_watch_user(user, "ban", now)
                        and not is_watch_user(user, "delete", now)
                        and not is_limited_user(gid, user, now, False)):
                    not aid and ask_help_welcome(client, uid, [gid], mid)
                    return True

        # Check failed list
        failed_time = user_status["failed"].get(gid, 0)

        if now - failed_time < glovar.time_punish:
            terminate_user(
                client=client,
                the_type="punish",
                uid=uid,
                gid=gid
            )
            delete_message(client, gid, mid)
            return True

        # Check declare status
        if message and is_declared_message(None, message):
            return False

        # Add to wait list
        add_wait(client, gid, user, mid, aid)
    except Exception as e:
        logger.warning(f"User captcha error: {e}", exc_info=True)

    return False
