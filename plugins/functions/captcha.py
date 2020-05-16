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
from random import choice, randint, sample, shuffle
from string import ascii_lowercase
from typing import List, Optional, Union

from captcha.image import ImageCaptcha
from claptcha import Claptcha
from pyrogram import Client, InlineKeyboardButton, InlineKeyboardMarkup, Message, User

from .. import glovar
from .channel import ask_help_welcome, send_debug
from .decorators import threaded
from .etc import button_data, code, get_channel_link, get_full_name, get_image_size, get_now, lang, mention_name
from .etc import mention_text, t2t
from .file import delete_file, get_new_path, save
from .filters import is_declared_message, is_flooded, is_limited_user, is_nm_text, is_should_ignore, is_watch_user
from .filters import is_wb_text
from .group import clear_joined_messages, delete_message, get_hint_text, get_pinned
from .ids import init_user_id
from .user import flood_user, restrict_user, terminate_user_punish, terminate_user_succeed, terminate_user_wrong
from .user import unrestrict_user
from .telegram import delete_messages, edit_message_photo, pin_chat_message
from .telegram import send_message, send_photo, send_report_message

# Enable logging
logger = logging.getLogger(__name__)


def add_wait(client: Client, gid: int, user: User, mid: int, aid: int = 0) -> bool:
    # Add user to the wait list
    result = False

    try:
        # Basic data
        uid = user.id
        name = get_full_name(user)
        now = get_now()

        # Check if the user should be added to the wait list
        if is_should_ignore(gid, user, aid):
            return True

        # Add the user to the wait list
        glovar.user_ids[uid]["name"] = name
        glovar.user_ids[uid]["wait"][gid] = now
        aid and glovar.user_ids[uid]["manual"].add(gid)
        save("user_ids")

        # Get group's waiting user list
        wait_user_list = [wid for wid in glovar.user_ids if glovar.user_ids[wid]["wait"].get(gid, 0)]

        # Restrict the user
        restrict_user(client, gid, uid)

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

        # Flood situation detected
        if len(wait_user_list) > glovar.limit_flood:
            # Add flood status
            add_flood(client, gid, mid, now)

            # Send the hint message
            text += f"{lang('message_type')}{lang('colon')}{code(lang('flood_static'))}\n"
            text += mention_users_text
            text += f"{lang('description')}{lang('colon')}{code(lang('description_hint'))}\n"
            send_hint(
                client=client,
                text=text,
                the_type="flood",
                gid=gid
            )

            # Delete old hint
            old_id = glovar.message_ids[gid]["hint"]
            glovar.message_ids[gid]["hint"] = 0
            old_id and delete_message(client, gid, old_id)
            old_id and save("message_ids")

            # Delete the joined service message
            delete_message(client, gid, mid)

        # Flood situation ongoing
        elif is_flooded(gid):
            delete_message(client, gid, mid)

        # Log flood user
        if is_flooded(gid):
            return flood_user(gid, uid, now, "challenge", mid, aid)

        # Check the group's hint config
        if not aid and not glovar.configs[gid].get("hint", True):
            return send_debug(
                client=client,
                gids=[gid],
                action=lang("action_wait"),
                uid=uid,
                aid=aid,
                em=mid,
                time=now
            )

        # Generate the hint text
        text += mention_users_text

        if aid == glovar.nospam_id:
            result = send_hint(
                client=client,
                the_type="nospam",
                gid=gid,
                user=user
            )
        elif aid:
            result = send_hint(
                client=client,
                the_type="manual",
                gid=gid,
                mid=mid,
                user=user
            )
        elif len(wait_user_list) == 1:
            result = send_hint(
                client=client,
                the_type="single",
                gid=gid,
                mid=mid,
                user=user
            )
        else:
            result = send_hint(
                client=client,
                text=text,
                the_type="normal",
                gid=gid,
                mid=mid
            )

        # Check if the message was sent successfully
        if not result:
            return add_failed(client, gid, uid, aid)

        # Send debug message
        result = send_debug(
            client=client,
            gids=[gid],
            action=lang("action_wait"),
            uid=uid,
            aid=aid,
            em=result,
            time=now
        )
    except Exception as e:
        logger.warning(f"Add wait error: {e}", exc_info=True)

    return result


def add_failed(client: Client, gid: int, uid: int, aid: int) -> bool:
    # Add wait failed
    result = False

    try:
        unrestrict_user(client, gid, uid)
        glovar.user_ids[uid]["wait"].pop(gid, 0)
        aid and glovar.user_ids[uid]["manual"].discard(gid)
        save("user_ids")
    except Exception as e:
        logger.warning(f"Add failed error: {e}", exc_info=True)

    return result


def add_flood(client: Client, gid: int, mid: int, now: int) -> bool:
    result = False

    try:
        # Update flood status
        glovar.pinned_ids[gid]["last"] = now
        save("pinned_ids")

        # Activate flood mode
        if is_flooded(gid):
            return True

        glovar.pinned_ids[gid]["start"] = now
        clear_joined_messages(client, gid, mid)
        result = send_debug(
            client=client,
            gids=[gid],
            action=lang("action_flood"),
            time=now
        )
    except Exception as e:
        logger.warning(f"Add flood error: {e}", exc_info=True)

    return result


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
            "limit": glovar.limit_try
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


def get_markup_ask(captcha: dict, question_type: str = "") -> Optional[InlineKeyboardMarkup]:
    # Question markup
    result = None

    try:
        if not captcha:
            return None

        markup_list = []

        # Candidates buttons
        candidates: List[str] = captcha.get("candidates", [])
        candidates and markup_list.append([])

        # Single line mode
        image_path = captcha.get("image")
        width, _ = get_image_size(image_path)
        single = width and width < 300

        for candidate in candidates:
            length = len(candidate.encode())
            button = button_data("q", "a", candidate)

            if markup_list[-1] is not [] and (single or length > 12):
                markup_list.append([])

            markup_list[-1].append(
                InlineKeyboardButton(
                    text=candidate,
                    callback_data=button
                )
            )

        # Change button
        if not question_type or question_type not in glovar.question_types["changeable"]:
            result = InlineKeyboardMarkup(markup_list) if markup_list else None
            return result

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
    except Exception as e:
        logger.warning(f"Get markup ask error: {e}", exc_info=True)

    return result


def get_markup_hint(single: bool = False, static: bool = False,
                    pinned: Message = None) -> Optional[InlineKeyboardMarkup]:
    # Get the hint message's markup
    result = None

    try:
        query_data = button_data("hint", "check", None)

        if static:
            captcha_link = glovar.captcha_link
        elif glovar.locks["invite"].acquire(blocking=False):
            captcha_link = glovar.invite.get("link", glovar.captcha_link)
            glovar.locks["invite"].release()
        else:
            captcha_link = glovar.captcha_link

        markup_list = [[]]

        if not single:
            markup_list[0].append(
                InlineKeyboardButton(
                    text=lang("captcha_check"),
                    callback_data=query_data
                )
            )

        markup_list[0].append(
            InlineKeyboardButton(
                text=lang("captcha_go"),
                url=captcha_link
            )
        )

        if not pinned:
            return InlineKeyboardMarkup(markup_list)

        markup_list.append(
            [
                InlineKeyboardButton(
                    text=lang("old_pinned"),
                    url=get_channel_link(pinned)
                )
            ]
        )

        result = InlineKeyboardMarkup(markup_list)
    except Exception as e:
        logger.warning(f"Get markup hint error: {e}", exc_info=True)

    return result


def question_answer(client: Client, uid: int, text: str) -> bool:
    # Answer the question
    result = False

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
            return terminate_user_succeed(
                client=client,
                uid=uid
            )

        glovar.user_ids[uid]["try"] += 1
        save("user_ids")

        if glovar.user_ids[uid]["try"] < limit:
            return question_status(client, uid, "again")

        question_status(client, uid, "wrong")
        result = terminate_user_wrong(
            client=client,
            uid=uid
        )
    except Exception as e:
        logger.warning(f"Question answer error: {e}", exc_info=True)

    return result


def question_ask(client: Client, user: User, mid: int) -> bool:
    # Ask a new question
    result = False

    try:
        # Basic data
        uid = user.id
        now = get_now()

        # Get the question data
        if "Hans" in glovar.lang:
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
                f"{lang('attention')}{lang('colon')}{code(lang('question_attention'))}\n\n"
                f"{lang('description')}{lang('colon')}{code(lang('description_ask').format(limit))}\n\n"
                f"{lang('question')}{lang('colon')}{code(question_text)}\n")

        # Generate the markup
        markup = get_markup_ask(captcha, question_type)

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
            image_path.startswith("tmp/") and delete_file(image_path)
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

        result = True
    except Exception as e:
        logger.warning(f"Ask question error: {e}", exc_info=True)

    return result


def question_change(client: Client, uid: int, mid: int) -> bool:
    # Change the question
    result = False

    try:
        # Basic data
        name = glovar.user_ids[uid]["name"]
        limit = glovar.user_ids[uid]["limit"]
        tried = glovar.user_ids[uid]["try"]

        # Check limit
        if tried >= limit:
            return False

        # Check changed status
        if uid not in glovar.changed_ids:
            glovar.changed_ids.add(uid)
        else:
            return False

        # Get the question data
        if "Hans" in glovar.lang:
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
        markup = get_markup_ask(captcha)

        # Get the image
        image_path = captcha.get("image", "") or "assets/none.png"

        # Edit the question message
        result = edit_message_photo(
            client=client,
            cid=glovar.captcha_group_id,
            mid=mid,
            photo=image_path,
            caption=text,
            markup=markup
        )
        image_path.startswith("tmp/") and delete_file(image_path)

        # Check if the message was edited successfully
        if not result:
            return False

        glovar.user_ids[uid]["type"] = question_type
        glovar.user_ids[uid]["answer"] = captcha["answer"]
        glovar.user_ids[uid]["limit"] = limit
        glovar.user_ids[uid]["try"] = 0
        save("user_ids")

        result = True
    except Exception as e:
        logger.warning(f"Question change error: {e}", exc_info=True)

    return result


def question_status(client: Client, uid: int, the_type: str) -> bool:
    # Reply question status
    result = False

    try:
        # Generate the text
        name = glovar.user_ids[uid]["name"]
        mid = glovar.user_ids[uid]["mid"]
        text = (f"{lang('user_name')}{lang('colon')}{mention_text(name, uid)}\n"
                f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                f"{lang('description')}{lang('colon')}{code(lang(f'description_{the_type}'))}\n")

        # Add suggestion
        if the_type == "wrong":
            text += f"{lang('suggestion')}{lang('colon')}{code(lang('suggestion_wrong'))}\n"

        # Get the markup
        if the_type == "succeed" and glovar.more:
            markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=glovar.more_text,
                            url=glovar.more_link
                        )
                    ]
                ]
            )
        else:
            markup = None

        # Decide the time
        if the_type == "again":
            secs = 10
        elif the_type == "succeed":
            secs = 20
        elif the_type == "wrong":
            secs = 15
        else:
            secs = 5

        # Send the message
        result = send_report_message(secs, client, glovar.captcha_group_id, text, mid, markup)
    except Exception as e:
        logger.warning(f"Question status error: {e}", exc_info=True)

    return result


def send_hint(client: Client, the_type: str, gid: int,
              text: str = "", mid: int = None, user: User = None) -> Union[bool, Message]:
    # Send hint message
    result = False

    try:
        # Flood and static hint
        if the_type == "flood" and glovar.configs[gid].get("pin", True):
            result = send_pin(client, gid)
        elif the_type == "flood":
            result = send_static(client, gid, text, True)
        elif the_type == "static":
            text = get_hint_text(gid, "static")
            result = send_static(client, gid, text)

        if the_type in {"flood", "static"}:
            return result

        # Regular hint text
        if the_type == "manual":
            text = get_hint_text(gid, "manual", user)
        elif the_type == "nospam":
            text = get_hint_text(gid, "nospam", user)
        elif the_type == "single":
            text = get_hint_text(gid, "single", user)
        else:
            text += f"{lang('description')}{lang('colon')}{code(lang('description_hint'))}\n"

        # Regular hint markup
        markup = get_markup_hint(single=the_type in {"manual", "nospam", "single"})

        # Send the hint
        result = send_message(
            client=client,
            cid=gid,
            text=text,
            mid=mid,
            markup=markup
        )

        # Init the data
        if the_type in {"manual", "nospam"} and glovar.message_ids[gid].get(the_type) is None:
            glovar.message_ids[gid][the_type] = {}

        # Update the hint message
        if the_type == "manual":
            new_id = result.message_id
            glovar.message_ids[gid]["manual"][new_id] = get_now()
        elif the_type == "nospam":
            new_id = result.message_id
            glovar.message_ids[gid]["nospam"][new_id] = get_now()
        else:
            new_id = result.message_id
            old_id = glovar.message_ids[gid]["hint"]
            glovar.message_ids[gid]["hint"] = new_id
            old_id and delete_message(client, gid, old_id)
            old_ids = glovar.message_ids[gid]["flood"]
            old_ids and delete_messages(client, gid, old_ids)

        # Save message ids
        save("message_ids")
    except Exception as e:
        logger.warning(f"Send hint error: {e}", exc_info=True)

    return result


def send_pin(client: Client, gid: int) -> bool:
    # Send pin message
    result = False

    glovar.locks["pin"].acquire()

    try:
        if glovar.pinned_ids[gid]["new_id"]:
            return True

        text = get_hint_text(gid, "flood")
        pinned_message = get_pinned(client, gid, False)
        markup = get_markup_hint(static=True, pinned=pinned_message)
        result = send_message(client, gid, text, None, markup)

        if not result:
            return False

        new_id = result.message_id
        old_ids = glovar.message_ids[gid]["flood"]
        old_ids and delete_messages(client, gid, old_ids)

        if pinned_message:
            old_id = pinned_message.message_id
        else:
            old_id = 0

        result = pin_chat_message(client, gid, new_id)

        if not result:
            delete_message(client, gid, new_id)
            return False

        glovar.pinned_ids[gid]["old_id"] = old_id
        glovar.pinned_ids[gid]["new_id"] = new_id
        save("pinned_ids")

        result = True
    except Exception as e:
        logger.warning(f"Send pin error: {e}", exc_info=True)
    finally:
        glovar.locks["pin"].release()

    return result


@threaded()
def send_static(client: Client, gid: int, text: str, flood: bool = False) -> bool:
    # Send static message
    result = False

    try:
        markup = get_markup_hint(static=True)
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

        result = True
    except Exception as e:
        logger.warning(f"Send static error: {e}", exc_info=True)

    return result


def user_captcha(client: Client, message: Optional[Message], gid: int, user: User, mid: int, now: int,
                 aid: int = 0) -> bool:
    # User CAPTCHA
    result = False

    try:
        # Basic data
        uid = user.id

        # Check if the user should be added to the wait list
        if is_should_ignore(gid, user, aid):
            return True

        # Init the user's status
        if not init_user_id(uid):
            return False

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
        name = get_full_name(user, True, True, True)
        ban_name = is_nm_text(name)
        wb_name = is_wb_text(name, False)

        # Succeeded auto pass
        succeeded_time = max(user_status["succeeded"].values()) if user_status["succeeded"] else 0

        still_in_captcha_group = (succeeded_time
                                  and not (ban_name or wb_name)
                                  and user_status["time"]
                                  and now - succeeded_time < glovar.time_remove + 30)

        if still_in_captcha_group:
            not aid and ask_help_welcome(client, uid, [gid], mid)
            return True

        do_not_need_recheck = (succeeded_time
                               and not (ban_name or wb_name)
                               and glovar.configs[gid].get("pass", True)
                               and succeeded_time and now - succeeded_time < glovar.time_recheck
                               and not is_watch_user(user, "ban", now)
                               and not is_watch_user(user, "delete", now)
                               and not is_limited_user(gid, user, now, False))

        if do_not_need_recheck:
            not aid and ask_help_welcome(client, uid, [gid], mid)
            return True

        # White list auto pass
        if glovar.configs[gid].get("pass", True) and uid in glovar.white_ids:
            not aid and ask_help_welcome(client, uid, [gid], mid)
            return True

        # Check failed list
        failed_time = user_status["failed"].get(gid, 0)

        if now - failed_time <= glovar.time_punish:
            terminate_user_punish(
                client=client,
                uid=uid,
                gid=gid
            )
            delete_message(client, gid, mid)
            return True

        # Check declare status
        if message and is_declared_message(None, message):
            return False

        # Add to wait list
        result = add_wait(client, gid, user, mid, aid)
    except Exception as e:
        logger.warning(f"User captcha error: {e}", exc_info=True)

    return result
