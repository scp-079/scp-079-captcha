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
from functools import wraps

from pyrogram.errors import FloodWait

from .etc import thread, wait_flood

# Enable logging
logger = logging.getLogger(__name__)


def retry(func):
    # FloodWait retry
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = None
        while True:
            try:
                result = func(*args, **kwargs)
            except FloodWait as e:
                wait_flood(e)
            except Exception as e:
                logger.warning(f"Retry error: {e}", exc_info=True)
                break
            else:
                break
        return result
    return wrapper


def threaded(daemon: bool = True):
    # Run with thread
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return thread(func, args, kwargs, daemon)
        return wrapper
    return decorator
