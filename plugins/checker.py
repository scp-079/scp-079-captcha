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
from os.path import exists

# Enable logging
logger = logging.getLogger(__name__)


def check_all(values: dict, broken: bool) -> bool:
    # Check all values in config.ini
    error = ""

    sections = list(values)
    sections.sort()

    for section in sections:
        data = values[section]
        error += eval(f"check_{section}")(data, broken)

    if not error:
        return True

    raise_error(error)


def check_bots(values: dict, broken: bool) -> str:
    # Check all values in bots section
    result = ""

    for key in values:
        if values[key] <= 0:
            result += f"[ERROR] [bots] {key} - should be a positive integer\n"

        if not broken or not result:
            continue

        raise_error(result)

    return result


def check_captcha(values: dict, broken: bool) -> str:
    # Check all values in captcha section
    result = ""

    for key in values:
        if values[key] in {"", "[DATA EXPUNGED]"}:
            result += f"[ERROR] [captcha] {key} - please fill something except [DATA EXPUNGED]\n"
        elif key == "captcha_link" and (values[key].startswith("@") or " " in values[key]):
            result += f"[ERROR] [captcha] {key} - please input a valid url\n"
        elif key.startswith("font") and not exists(values[key]):
            result += f"[ERROR] [captcha] {key} - font file does not exist\n"
        elif key == "noise" and values[key] <= 0:
            result += f"[ERROR] [captcha] {key} - should be a positive float\n"

        if not broken or not result:
            continue

        raise_error(result)

    return result


def check_channels(values: dict, broken: bool) -> str:
    # Check all values in channels section
    result = ""

    for key in values:
        if values[key] >= 0:
            result += f"[ERROR] [channels] {key} - should be a negative integer\n"
        elif key.endswith("channel_id") and not str(values[key]).startswith("-100"):
            result += f"[ERROR] [channels] {key} - please use a channel instead\n"
        elif not str(values[key]).startswith("-100"):
            result += f"[ERROR] [channels] {key} - please use a supergroup instead\n"

        if not broken or not result:
            continue

        raise_error(result)

    return result


def check_custom(values: dict, broken: bool) -> str:
    # Check all values in custom section
    result = ""

    for key in values:
        if values[key] in {"", "[DATA EXPUNGED]"}:
            result += f"[ERROR] [custom] {key} - please fill something except [DATA EXPUNGED]\n"
        elif key.endswith("link") and (values[key].startswith("@") or " " in values[key]):
            result += f"[ERROR] [custom] {key} - please input a valid url\n"
        elif key == "more" and values[key] not in {False, True}:
            result += f"[ERROR] [custom] {key} - please fill a valid boolean value\n"

        if not broken or not result:
            continue

        raise_error(result)

    return result


def check_emoji(values: dict, broken: bool) -> str:
    # Check all values in emoji section
    result = ""

    for key in values:
        if key != "emoji_protect" and values[key] <= 0:
            result += f"[ERROR] [emoji] {key} - should be a positive integer"
        elif key == "emoji_protect" and values[key] in {"", "[DATA EXPUNGED]"}:
            result += f"[ERROR] [emoji] {key} - please fill something except [DATA EXPUNGED]\n"

        if not broken or not result:
            continue

        raise_error(result)

    return result


def check_encrypt(values: dict, broken: bool) -> str:
    # Check all values in encrypt section
    result = ""

    for key in values:
        if key == "key" and key in {b"", b"[DATA EXPUNGED]", "", "[DATA EXPUNGED]"}:
            result += f"[ERROR] [encrypt] {key} - please fill a valid key\n"
        elif key == "password" and key in {"", "[DATA EXPUNGED]"}:
            result += f"[ERROR] [encrypt] {key} - please fill a valid password\n"

        if not broken or not result:
            continue

        raise_error(result)

    return result


def check_language(values: dict, broken: bool) -> str:
    # Check all values in language section
    result = ""

    for key in values:
        if key == "lang" and values[key] in {"", "[DATA EXPUNGED]"}:
            result += f"[ERROR] [language] {key} - please fill something except [DATA EXPUNGED]\n"
        elif key == "lang" and not exists(f"languages/{values[key]}.yml"):
            result += f"[ERROR] [language] {key} - language {values[key]} does not exist\n"
        elif key == "normalize" and values[key] not in {False, True}:
            result += f"[ERROR] [language] {key} - please fill a valid boolean value\n"

        if not broken or not result:
            continue

        raise_error(result)

    return result


def check_limit(values: dict, broken: bool) -> str:
    # Check all values in limit section
    result = ""

    for key in values:
        if values[key] <= 0:
            result += f"[ERROR] [limit] {key} - should be a positive integer\n"

        if not broken or not result:
            continue

        raise_error(result)

    return result


def check_mode(values: dict, broken: bool) -> str:
    # Check all values in mode section
    result = ""

    for key in values:
        if values[key] not in {False, True}:
            result += f"[ERROR] [mode] {key} - please fill a valid boolean value\n"

        if not broken or not result:
            continue

        raise_error(result)

    return result


def check_time(values: dict, broken: bool) -> str:
    # Check all values in time section
    result = ""

    for key in values:
        if key == "date_reset" and values[key] in {"", "[DATA EXPUNGED]"}:
            result += f"[ERROR] [time] {key} - please fill a correct format string\n"
        elif key.startswith("time") and values[key] <= 0:
            result += f"[ERROR] [time] {key} - should be a positive integer\n"

        if not broken or not result:
            continue

        raise_error(result)

    return result


def raise_error(error: str):
    error = "-" * 24 + f"\nBot refused to start because:\n" + "-" * 24 + f"\n{error}" + "-" * 24
    logger.critical(error)
    raise SystemExit(error)
