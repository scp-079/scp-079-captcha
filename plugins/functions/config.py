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
from typing import Dict, List, Set, Union

from pyrogram import Client, Message

from .. import glovar
from .captcha import get_answers, get_markup_qns
from .channel import send_debug
from .command import command_error
from .decorators import threaded
from .etc import button_data, code, general_link, get_now, lang, thread
from .file import delete_file, file_txt, save
from .telegram import get_group_info, send_document, send_message, send_report_message

# Enable logging
logger = logging.getLogger(__name__)


def conflict_config(config: dict, config_list: List[str], master: str) -> dict:
    # Conflict config
    result = config

    try:
        if master not in config_list:
            return config

        if not config.get(master, False):
            return config

        config_list.remove(master)

        for other in config_list:
            result[other] = False
    except Exception as e:
        logger.warning(f"Conflict config error: {e}", exc_info=True)

    return result


def get_config_text(config: dict) -> str:
    # Get the group's config text
    result = ""

    try:
        # Basic
        default_text = (lambda x: lang("default") if x else lang("custom"))(config.get("default"))
        delete_text = (lambda x: lang("enabled") if x else lang("disabled"))(config.get("delete"))
        restrict_text = (lambda x: lang("enabled") if x else lang("disabled"))(config.get("restrict"))
        result += (f"{lang('config')}{lang('colon')}{code(default_text)}\n"
                   f"{lang('delete')}{lang('colon')}{code(delete_text)}\n"
                   f"{lang('restrict')}{lang('colon')}{code(restrict_text)}\n")

        # Others
        for the_type in ["ban", "forgive", "hint", "pass", "pin", "qns", "manual"]:
            the_text = (lambda x: lang("enabled") if x else lang("disabled"))(config.get(the_type))
            result += f"{lang(the_type)}{lang('colon')}{code(the_text)}\n"
    except Exception as e:
        logger.warning(f"Get config text error: {e}", exc_info=True)

    return result


def qns_add(client: Client, message: Message, gid: int, key: str, text: str, the_type: str = "add") -> bool:
    # Add or edit a custom question
    result = False

    try:
        # Basic data
        cid = message.chat.id
        aid = message.from_user.id
        mid = message.message_id
        now = get_now()

        # Check questions count
        if the_type == "add" and len(glovar.questions[gid]["qns"]) >= 20:
            return command_error(client, message, lang(f"action_qns_{the_type}"), lang("error_exceed_qns"),
                                 report=False)

        # Get text list
        text_list = [t for t in text.split("\n+++") if t]

        # Check the text list
        if not text_list or len(text_list) < 2:
            return command_error(client, message, lang(f"action_qns_{the_type}"), lang("command_para"), report=False)

        # Get question and answers
        question = text_list[0]
        correct = text_list[1]
        wrong = text_list[-1]

        # Check the question
        if len(question) > 140:
            return command_error(client, message, lang(f"action_qns_{the_type}"), lang("command_para"),
                                 lang("error_exceed_qn"), False)

        correct_list = {c for c in correct.split("\n") if c.strip()}

        if wrong == correct:
            wrong_list = set()
        else:
            wrong_list = {w for w in wrong.split("\n") if w.strip()}

        # Check the answers
        if any(w in correct_list for w in wrong_list):
            return command_error(client, message, lang(f"action_qns_{the_type}"), lang("command_para"),
                                 lang("error_duplicated"), False)

        if len(correct_list | wrong_list) > 6:
            return command_error(client, message, lang(f"action_qns_{the_type}"), lang("command_para"),
                                 lang("error_exceed_answers"), False)

        if any(len(a.encode()) > 15 for a in correct_list) or any(len(a.encode()) > 64 for a in wrong_list):
            return command_error(client, message, lang(f"action_qns_{the_type}"), lang("command_para"),
                                 lang("error_exceed_answer"), False)

        # Add or edit the answer
        if the_type == "add":
            glovar.questions[gid]["qns"][key] = {
                "time": now,
                "aid": aid,
                "question": question,
                "correct": correct_list,
                "wrong": wrong_list,
                "issued": 0,
                "engaged": 0,
                "solved": 0
            }
        else:
            glovar.questions[gid]["qns"][key]["time"] = now
            glovar.questions[gid]["qns"][key]["aid"] = aid
            glovar.questions[gid]["qns"][key]["question"] = question
            glovar.questions[gid]["qns"][key]["correct"] = correct_list
            glovar.questions[gid]["qns"][key]["wrong"] = wrong_list

        # Save the data
        save("questions")

        # Generate the text
        group_name, group_link = get_group_info(client, gid)
        text = (f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                f"{lang('group_id')}{lang('colon')}{code(gid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang(f'action_qns_{the_type}'))}\n"
                f"{lang('status')}{lang('colon')}{code(lang('status_succeeded'))}\n" + code("-" * 24) + "\n"
                f"{lang('qns_key')}{lang('colon')}{code(key)}\n" + code("-" * 24) + "\n"
                f"{lang('question')}{lang('colon')}{code(question)}\n" + code("-" * 24) + "\n")
        text += "\n".join("\t" * 4 + f"■ {code(c)}" for c in correct_list) + "\n"
        text += "\n".join("\t" * 4 + f"□ {code(w)}" for w in wrong_list) + "\n"

        # Generate the markup
        buttons = []
        answers = list(correct_list | wrong_list)
        answers = get_answers(answers)

        for answer in answers:
            buttons.append(
                {
                    "text": answer,
                    "data": button_data("none")
                }
            )

        markup = get_markup_qns(buttons)

        # Send the report message
        thread(send_message, (client, cid, text, mid, markup))

        result = True
    except Exception as e:
        logger.warning(f"Qns add error: {e}", exc_info=True)

    return result


def qns_remove(client: Client, message: Message, gid: int, key: str) -> bool:
    # Remove a custom question
    result = False

    try:
        # Basic data
        cid = message.chat.id
        mid = message.message_id
        question = glovar.questions[gid]["qns"][key]["question"]

        # Pop the data
        glovar.questions[gid]["qns"].pop(key, {})
        save("questions")

        # Generate the text
        group_name, group_link = get_group_info(client, gid)
        text = (f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                f"{lang('group_id')}{lang('colon')}{code(gid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('action_qns_remove'))}\n"
                f"{lang('status')}{lang('colon')}{code(lang('status_succeeded'))}\n" + code("-" * 24) + "\n"
                f"{lang('qns_key')}{lang('colon')}{code(key)}\n" + code("-" * 24) + "\n"
                f"{lang('question')}{lang('colon')}{code(question)}\n")

        # Send the report message
        thread(send_message, (client, cid, text, mid))

        result = True
    except Exception as e:
        logger.warning(f"Qns remove error: {e}", exc_info=True)

    return result


@threaded()
def qns_show(client: Client, message: Message, gid: int, file: bool = False) -> bool:
    # Show all custom questions
    result = False

    try:
        # Basic data
        cid = message.chat.id
        mid = message.message_id

        with glovar.locks["config"]:
            questions = glovar.questions[gid]["qns"]

        # Check data
        if not questions:
            return command_error(client, message, lang("action_qns_show"), lang("error_none"), report=False)

        # Send as file
        if file or len(questions) > 5:
            return qns_show_file(client, message, gid, questions)

        # Generate the text
        group_name, group_link = get_group_info(client, gid)
        text = (f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                f"{lang('group_id')}{lang('colon')}{code(gid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('action_qns_show'))}\n"
                f"{lang('qns_total')}{lang('colon')}{code(len(questions))}\n\n")

        for key in questions:
            aid = questions[key]["aid"]
            question = questions[key]["question"]
            correct_list = questions[key]["correct"]
            wrong_list = questions[key]["wrong"]
            issued = questions[key]["issued"]
            engaged = questions[key]["engaged"]
            solved = questions[key]["solved"]
            percent_passed = (solved / (issued or 1)) * 100
            percent_engaged = (engaged / (issued or 1)) * 100
            percent_wrong = ((engaged - solved) / (engaged or 1)) * 100

            text += code("-" * 24) + "\n\n"
            text += (f"{lang('qns_key')}{lang('colon')}{code(key)}\n"
                     f"{lang('modified_by')}{lang('colon')}{code(aid)}\n"
                     f"{lang('qns_issued')}{lang('colon')}{code(issued)}\n"
                     f"{lang('percent_passed')}{lang('colon')}{code(f'{percent_passed:.1f}%')}\n"
                     f"{lang('percent_engaged')}{lang('colon')}{code(f'{percent_engaged:.1f}%')}\n"
                     f"{lang('percent_wrong')}{lang('colon')}{code(f'{percent_wrong:.1f}%')}\n"
                     f"{lang('question')}{lang('colon')}{code(question)}\n")
            text += "\n".join("\t" * 4 + f"■ {code(c)}" for c in correct_list) + "\n"
            text += "\n".join("\t" * 4 + f"□ {code(w)}" for w in wrong_list)

            if wrong_list:
                text += "\n\n"
            else:
                text += "\n"

        # Send the report message
        send_message(client, cid, text, mid)

        result = True
    except Exception as e:
        logger.warning(f"Qns show error: {e}", exc_info=True)

    return result


def qns_show_file(client: Client, message: Message, gid: int,
                  questions: Dict[str, Dict[str, Union[int, str, Set[str]]]]) -> bool:
    # Show all custom questions as TXT file
    result = False

    try:
        # Basic data
        cid = message.chat.id
        mid = message.message_id

        # Generate the text
        group_name, group_link = get_group_info(client, gid)
        caption = (f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                   f"{lang('group_id')}{lang('colon')}{code(gid)}\n"
                   f"{lang('action')}{lang('colon')}{code(lang('action_qns_show'))}\n\n")
        text = (f"{lang('group_name')}{lang('colon')}{group_name}\n"
                f"{lang('group_id')}{lang('colon')}{gid}\n"
                f"{lang('qns_total')}{lang('colon')}{len(questions)}\n\n")

        for key in questions:
            aid = questions[key]["aid"]
            question = questions[key]["question"]
            correct_list = questions[key]["correct"]
            wrong_list = questions[key]["wrong"]
            issued = questions[key]["issued"]
            engaged = questions[key]["engaged"]
            solved = questions[key]["solved"]
            percent_passed = (solved / (issued or 1)) * 100
            percent_engaged = (engaged / (issued or 1)) * 100
            percent_wrong = ((engaged - solved) / (engaged or 1)) * 100

            text += ("-" * 24) + "\n\n"
            text += (f"{lang('qns_key')}{lang('colon')}{key}\n"
                     f"{lang('modified_by')}{lang('colon')}{aid}\n"
                     f"{lang('qns_issued')}{lang('colon')}{issued}\n"
                     f"{lang('percent_passed')}{lang('colon')}{f'{percent_passed:.1f}%'}\n"
                     f"{lang('percent_engaged')}{lang('colon')}{f'{percent_engaged:.1f}%'}\n"
                     f"{lang('percent_wrong')}{lang('colon')}{f'{percent_wrong:.1f}%'}\n"
                     f"{lang('question')}{lang('colon')}{question}\n")
            text += "\n".join("\t" + f"■ {c}" for c in correct_list) + "\n"
            text += "\n".join("\t" + f"□ {w}" for w in wrong_list)

            if wrong_list:
                text += "\n\n"
            else:
                text += "\n"

        # Save to a file
        file = file_txt(text)

        # Send the report message
        send_document(client, cid, file, None, caption, mid)

        # Delete the file
        delete_file(file)

        result = True
    except Exception as e:
        logger.warning(f"Qns show file error: {e}", exc_info=True)

    return result


def start_qns(client: Client, message: Message, key: str) -> bool:
    # Start qns
    result = False

    try:
        # Basic data
        cid = message.chat.id
        uid = message.from_user.id
        mid = message.message_id
        gid = glovar.starts[key]["cid"]
        aid = glovar.starts[key]["uid"]

        # Check the permission
        if uid != aid:
            return False

        # Send the report message
        group_name, group_link = get_group_info(client, gid)
        text = (f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                f"{lang('group_id')}{lang('colon')}{code(gid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('action_qns'))}\n"
                f"{lang('description')}{lang('colon')}{code(lang('description_qns'))}\n")
        thread(send_message, (client, cid, text, mid))

        result = True
    except Exception as e:
        logger.warning(f"Start qns error: {e}", exc_info=True)

    return result


def update_config(client: Client, message: Message, config: dict, more: str = "") -> bool:
    # Update a group's config
    result = False

    try:
        # Basic data
        gid = message.chat.id
        aid = message.from_user.id

        # Update the config
        glovar.configs[gid] = deepcopy(config)
        save("configs")

        # Send the report message
        text = (f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"
                f"{lang('action')}{lang('colon')}{code(lang('config_change'))}\n"
                f"{lang('status')}{lang('colon')}{code(lang('status_succeeded'))}\n")

        if more:
            text += f"{lang('more')}{lang('colon')}{code(more)}\n"

        thread(send_report_message, (15, client, gid, text))

        # Send the debug message
        send_debug(
            client=client,
            gids=[gid],
            action=lang("config_change"),
            aid=aid,
            more=more
        )

        result = True
    except Exception as e:
        logger.warning(f"Update config error: {e}", exc_info=True)

    return result
