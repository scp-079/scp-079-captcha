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
from json import dumps
from typing import List, Union

from pyrogram import Chat, Client, Message

from .. import glovar
from .decorators import threaded
from .etc import code, code_block, general_link, get_channel_link, get_readable_time, lang, message_link, thread
from .file import crypt_file, data_to_file, delete_file, get_new_path, save
from .filters import is_class_d_user
from .telegram import get_group_info, send_document, send_message

# Enable logging
logger = logging.getLogger(__name__)


def ask_for_help(client: Client, level: str, gid: int, uid: int, group: str = "single") -> bool:
    # Let USER help to delete all message from user, or ban user globally
    result = False

    try:
        data = {
            "group_id": gid,
            "user_id": uid
        }

        if level == "ban":
            data["type"] = (glovar.configs[gid].get("restrict", False) and "restrict") or "ban"
        elif level == "delete":
            data["type"] = group

        data["delete"] = glovar.configs[gid].get("delete", True)

        result = share_data(
            client=client,
            receivers=["USER"],
            action="help",
            action_type=level,
            data=data
        )
    except Exception as e:
        logger.warning(f"Ask for help error: {e}", exc_info=True)

    return result


def ask_help_welcome(client: Client, uid: int, gids: List[int], mid: int = None) -> bool:
    # Ask help welcome
    result = False

    try:
        if is_class_d_user(uid):
            return False

        if all(glovar.tip_id not in glovar.trust_ids[gid] for gid in gids):
            return False

        result = share_data(
            client=client,
            receivers=["TIP"],
            action="help",
            action_type="welcome",
            data={
                "user_id": uid,
                "group_ids": gids,
                "message_id": mid
            }
        )
    except Exception as e:
        logger.warning(f"Ask help welcome error: {e}", exc_info=True)

    return result


def declare_message(client: Client, gid: int, mid: int) -> bool:
    # Declare a message
    result = False

    try:
        glovar.declared_message_ids[gid].add(mid)
        result = share_data(
            client=client,
            receivers=glovar.receivers["declare"],
            action="update",
            action_type="declare",
            data={
                "group_id": gid,
                "message_id": mid
            }
        )
    except Exception as e:
        logger.warning(f"Declare message error: {e}", exc_info=True)

    return result


def exchange_to_hide(client: Client) -> bool:
    # Let other bots exchange data in the hide channel instead
    result = False

    try:
        # Transfer the channel
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

        result = True
    except Exception as e:
        logger.warning(f"Exchange to hide error: {e}", exc_info=True)

    return result


def format_data(sender: str, receivers: List[str], action: str, action_type: str,
                data: Union[bool, dict, int, str] = None) -> str:
    # Get exchange string
    result = ""

    try:
        data = {
            "from": sender,
            "to": receivers,
            "action": action,
            "type": action_type,
            "data": data
        }
        result = code_block(dumps(data, indent=4))
    except Exception as e:
        logger.warning(f"Format data error: {e}", exc_info=True)

    return result


def get_debug_text(client: Client, context: Union[int, Chat, List[int]]) -> str:
    # Get a debug message text prefix
    result = ""

    try:
        # Prefix
        result = f"{lang('project')}{lang('colon')}{general_link(glovar.project_name, glovar.project_link)}\n"

        # List of group ids
        gids = context if isinstance(context, list) else []

        for group_id in gids:
            group_name, group_link = get_group_info(client, group_id)
            result += (f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                       f"{lang('group_id')}{lang('colon')}{code(group_id)}\n")

        if gids:
            return result

        # One group
        if isinstance(context, int):
            group_id = context
        else:
            group_id = context.id

        # Generate the group info text
        group_name, group_link = get_group_info(client, context)
        result += (f"{lang('group_name')}{lang('colon')}{general_link(group_name, group_link)}\n"
                   f"{lang('group_id')}{lang('colon')}{code(group_id)}\n")
    except Exception as e:
        logger.warning(f"Get debug text error: {e}", exc_info=True)

    return result


@threaded()
def send_debug(client: Client, gids: List[int], action: str,
               uid: int = 0, aid: int = 0,
               em: Union[int, Message] = 0, time: int = 0, duration: int = 0,
               total: int = 0, count: int = 0,
               more: str = "", file: str = "") -> bool:
    # Send the debug message
    result = False

    try:
        if not gids:
            return False

        text = get_debug_text(client, gids)

        if uid:
            text += f"{lang('user_id')}{lang('colon')}{code(uid)}\n"

        text += f"{lang('action')}{lang('colon')}{code(action)}\n"

        if aid:
            text += f"{lang('admin_group')}{lang('colon')}{code(aid)}\n"

        if em and isinstance(em, Message):
            mid = em.message_id
            text += f"{lang('triggered_by')}{lang('colon')}{general_link(mid, message_link(em))}\n"
        elif em and isinstance(em, int):
            mid_link = f"{get_channel_link(gids[0])}/{em}"
            text += f"{lang('triggered_by')}{lang('colon')}{general_link(em, mid_link)}\n"

        if time:
            text += f"{lang('triggered_time')}{lang('colon')}{code(get_readable_time(time))}\n"

        if duration:
            text += f"{lang('flood_duration')}{lang('colon')}{code(str(duration) + ' ' + lang('seconds'))}\n"

        if total:
            text += f"{lang('flood_total')}{lang('colon')}{code(str(total) + ' ' + lang('members'))}\n"

        if count:
            text += f"{lang('flood_count')}{lang('colon')}{code(str(count)  + ' ' + lang('members'))}\n"

        if more:
            text += f"{lang('more')}{lang('colon')}{code(more)}\n"

        if file:
            result = bool(send_document(client, glovar.debug_channel_id, file, None, text))
            thread(delete_file, (file,))
        else:
            result = bool(send_message(client, glovar.debug_channel_id, text))
    except Exception as e:
        logger.warning(f"Send debug error: {e}", exc_info=True)

    return result


@threaded()
def share_data(client: Client, receivers: List[str], action: str, action_type: str,
               data: Union[bool, dict, int, str] = None, file: str = None, encrypt: bool = True) -> bool:
    # Use this function to share data in the channel
    result = False

    try:
        if glovar.sender in receivers:
            receivers.remove(glovar.sender)

        if not receivers:
            return False

        if glovar.should_hide:
            channel_id = glovar.hide_channel_id
        else:
            channel_id = glovar.exchange_channel_id

        # Plain text
        if not file:
            text = format_data(
                sender=glovar.sender,
                receivers=receivers,
                action=action,
                action_type=action_type,
                data=data
            )
            result = send_message(client, channel_id, text)
            return ((result is False and not glovar.should_hide)
                    and share_data_failed(client, receivers, action, action_type, data, file, encrypt))

        # Share with a file
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

        if not result:
            return ((result is False and not glovar.should_hide)
                    and share_data_failed(client, receivers, action, action_type, data, file, encrypt))

        # Delete the tmp file
        for f in {file, file_path}:
            f.startswith("tmp/") and thread(delete_file, (f,))

        result = bool(result)
    except Exception as e:
        logger.warning(f"Share data error: {e}", exc_info=True)

    return result


@threaded()
def share_data_failed(client: Client, receivers: List[str], action: str, action_type: str,
                      data: Union[bool, dict, int, str] = None, file: str = None, encrypt: bool = True) -> bool:
    # Sharing data failed, use the exchange channel instead
    result = False

    try:
        exchange_to_hide(client)
        result = share_data(
            client=client,
            receivers=receivers,
            action=action,
            action_type=action_type,
            data=data,
            file=file,
            encrypt=encrypt
        )
    except Exception as e:
        logger.warning(f"Share data failed error: {e}", exc_info=True)

    return result


def share_regex_count(client: Client, word_type: str) -> bool:
    # Use this function to share regex count to REGEX
    result = False

    try:
        if not glovar.regex.get(word_type):
            return False

        if not eval(f"glovar.{word_type}_words"):
            return False

        file = data_to_file(eval(f"glovar.{word_type}_words"))
        result = share_data(
            client=client,
            receivers=["REGEX"],
            action="regex",
            action_type="count",
            data=f"{word_type}_words",
            file=file
        )
    except Exception as e:
        logger.warning(f"Share regex update error: {e}", exc_info=True)

    return result


def update_score(client: Client, uid: int) -> bool:
    # Update a user's score, share it
    result = False

    try:
        pass_count = len(glovar.user_ids[uid]["pass"])
        succeeded_count = len(glovar.user_ids[uid]["succeeded"])
        failed_count = len([gid for gid in glovar.user_ids[uid]["failed"]
                            if glovar.user_ids[uid]["failed"][gid] >= 0])
        score = pass_count * -0.2 + succeeded_count * -0.3 + failed_count * 0.6
        glovar.user_ids[uid]["score"][glovar.sender.lower()] = score
        save("user_ids")
        result = share_data(
            client=client,
            receivers=glovar.receivers["score"],
            action="update",
            action_type="score",
            data={
                "id": uid,
                "score": round(score, 1)
            }
        )
    except Exception as e:
        logger.warning(f"Update score error: {e}", exc_info=True)

    return result
