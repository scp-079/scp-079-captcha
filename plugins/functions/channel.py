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
from json import dumps
from typing import List, Optional, Union

from pyrogram import Client, Message

from .. import glovar
from .etc import code, code_block, general_link, lang, message_link, thread
from .file import crypt_file, data_to_file, delete_file, get_new_path, save
from .telegram import get_group_info, send_document, send_message

# Enable logging
logger = logging.getLogger(__name__)


def ask_for_help(client: Client, level: str, gid: int, uid: int, group: str = "single") -> bool:
    # Let USER help to delete all message from user, or ban user globally
    try:
        data = {
                "group_id": gid,
                "user_id": uid
        }

        if level == "ban":
            data["type"] = (glovar.configs[gid].get("restrict") and "restrict") or "ban"
        elif level == "delete":
            data["type"] = group

        data["delete"] = glovar.configs[gid].get("delete")

        share_data(
            client=client,
            receivers=["USER"],
            action="help",
            action_type=level,
            data=data
        )

        return True
    except Exception as e:
        logger.warning(f"Ask for help error: {e}", exc_info=True)

    return False


def declare_message(client: Client, gid: int, mid: int) -> bool:
    # Declare a message
    try:
        glovar.declared_message_ids[gid].add(mid)
        share_data(
            client=client,
            receivers=glovar.receivers["declare"],
            action="update",
            action_type="declare",
            data={
                "group_id": gid,
                "message_id": mid
            }
        )

        return True
    except Exception as e:
        logger.warning(f"Declare message error: {e}", exc_info=True)

    return False


def exchange_to_hide(client: Client) -> bool:
    # Let other bots exchange data in the hide channel instead
    try:
        glovar.should_hide = True
        share_data(
            client=client,
            receivers=["EMERGENCY"],
            action="backup",
            action_type="hide",
            data=True
        )

        # Send debug message
        text = (f"{lang('project')}{lang('colon')}{code(glovar.sender)}\n"
                f"{lang('issue')}{lang('colon')}{code(lang('exchange_invalid'))}\n"
                f"{lang('auto_fix')}{lang('colon')}{code(lang('protocol_1'))}\n")
        thread(send_message, (client, glovar.critical_channel_id, text))

        return True
    except Exception as e:
        logger.warning(f"Exchange to hide error: {e}", exc_info=True)

    return False


def format_data(sender: str, receivers: List[str], action: str, action_type: str,
                data: Union[bool, dict, int, str] = None) -> str:
    # See https://scp-079.org/exchange/
    text = ""
    try:
        data = {
            "from": sender,
            "to": receivers,
            "action": action,
            "type": action_type,
            "data": data
        }
        text = code_block(dumps(data, indent=4))
    except Exception as e:
        logger.warning(f"Format data error: {e}", exc_info=True)

    return text


def forward_evidence(client: Client, uid: int, level: str, rule: str, gid: int,
                     more: str = None) -> Optional[Union[bool, Message]]:
    # Forward the message to the channel as evidence
    result = None
    try:
        # Basic information
        text = (f"{lang('project')}{lang('colon')}{code(glovar.sender)}\n"
                f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                f"{lang('level')}{lang('colon')}{code(level)}\n"
                f"{lang('rule')}{lang('colon')}{code(rule)}\n")

        # Additional information
        text += f"{lang('message_type')}{lang('colon')}{code(lang('ser'))}\n"

        name = glovar.user_ids[uid]["name"]
        if name:
            text += f"{lang('user_name')}{lang('colon')}{code(name)}\n"

        joined = glovar.user_ids[uid]["wait"].get(gid, 0)
        if joined:
            text += f"{lang('joined')}{lang('colon')}{code(joined)}\n"

        # Extra information
        if more:
            text += f"{lang('more')}{lang('colon')}{code(more)}\n"

        # Attach report message
        result = send_message(client, glovar.logging_channel_id, text)
    except Exception as e:
        logger.warning(f"Forward evidence error: {e}", exc_info=True)

    return result


def get_debug_text(client: Client, gids: List[int]) -> str:
    # Get a debug message text prefix, accept int list
    text = ""
    try:
        text = f"{lang('project')}{lang('colon')}{general_link(glovar.project_name, glovar.project_link)}\n"
        for group_id in gids:
            group_name, group_link = get_group_info(client, group_id)
            text += (f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                     f"{lang('group_id')}{lang('colon')}{code(group_id)}\n")
    except Exception as e:
        logger.warning(f"Get debug text error: {e}", exc_info=True)

    return text


def send_debug(client: Client, gids: List[int], action: str, uid: int, aid: int = 0, em: Message = None) -> bool:
    # Send the debug message
    try:
        text = get_debug_text(client, gids)
        text += (f"{lang('user_id')}{lang('colon')}{code(uid)}\n"
                 f"{lang('action')}{lang('colon')}{code(action)}\n")

        if aid:
            text += f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"

        if em:
            mid = em.message_id
            text += f"{lang('evidence')}{lang('colon')}{general_link(mid, message_link(em))}\n"

        thread(send_message, (client, glovar.debug_channel_id, text))

        return True
    except Exception as e:
        logger.warning(f"Send debug error: {e}", exc_info=True)

    return False


def share_data(client: Client, receivers: List[str], action: str, action_type: str,
               data: Union[bool, dict, int, str] = None, file: str = None, encrypt: bool = True) -> bool:
    # Use this function to share data in the channel
    try:
        if glovar.sender in receivers:
            receivers.remove(glovar.sender)

        if not receivers:
            return True

        if glovar.should_hide:
            channel_id = glovar.hide_channel_id
        else:
            channel_id = glovar.exchange_channel_id

        if file:
            text = format_data(
                sender=glovar.sender,
                receivers=receivers,
                action=action,
                action_type=action_type,
                data=data
            )
            if encrypt:
                # Encrypt the file, save to the tmp directory
                file_path = get_new_path()
                crypt_file("encrypt", file, file_path)
            else:
                # Send directly
                file_path = file

            result = send_document(client, channel_id, file_path, None, text)
            # Delete the tmp file
            if result:
                for f in {file, file_path}:
                    if "tmp/" in f:
                        thread(delete_file, (f,))
        else:
            text = format_data(
                sender=glovar.sender,
                receivers=receivers,
                action=action,
                action_type=action_type,
                data=data
            )
            result = send_message(client, channel_id, text)

        # Sending failed due to channel issue
        if result is False and not glovar.should_hide:
            # Use hide channel instead
            exchange_to_hide(client)
            thread(share_data, (client, receivers, action, action_type, data, file, encrypt))

        return True
    except Exception as e:
        logger.warning(f"Share data error: {e}", exc_info=True)

    return False


def share_regex_count(client: Client, word_type: str) -> bool:
    # Use this function to share regex count to REGEX
    try:
        if not glovar.regex.get(word_type):
            return True

        if not eval(f"glovar.{word_type}_words"):
            return True

        file = data_to_file(eval(f"glovar.{word_type}_words"))
        share_data(
            client=client,
            receivers=["REGEX"],
            action="regex",
            action_type="count",
            data=f"{word_type}_words",
            file=file
        )

        return True
    except Exception as e:
        logger.warning(f"Share regex update error: {e}", exc_info=True)

    return False


def update_score(client: Client, uid: int) -> bool:
    # Update a user's score, share it
    try:
        pass_count = len(glovar.user_ids[uid]["pass"])
        succeeded_count = len(glovar.user_ids[uid]["succeeded"])
        failed_count = len(glovar.user_ids[uid]["failed"])
        score = pass_count * -0.2 + succeeded_count * -0.3 + failed_count * 0.6
        glovar.user_ids[uid]["score"][glovar.sender.lower()] = score
        save("user_ids")
        share_data(
            client=client,
            receivers=glovar.receivers["score"],
            action="update",
            action_type="score",
            data={
                "id": uid,
                "score": round(score, 1)
            }
        )

        return True
    except Exception as e:
        logger.warning(f"Update score error: {e}", exc_info=True)

    return False
