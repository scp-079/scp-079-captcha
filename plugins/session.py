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

from . import glovar
from .functions.file import delete_file, save

# Enable logging
logger = logging.getLogger(__name__)


def renew() -> bool:
    # Renew the session
    result = False

    try:
        if not glovar.token:
            glovar.token = glovar.bot_token
            save("token")
            return False

        if glovar.token == glovar.bot_token:
            return False

        delete_file("bot.session")
        glovar.token = glovar.bot_token
        save("token")

        result = True
    except Exception as e:
        logger.warning(f"Renew error: {e}", exc_info=True)

    return result
