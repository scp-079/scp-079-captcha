# SCP-079-CAPTCHA

This bot is used to provide challenges for new joined members.

## How to use

See [this article](https://scp-079.org/captcha/).

## To Do List

- [x] Basic functions

## Requirements

- Python 3.6 or higher
- Debian 10: `sudo apt update && sudo apt install opencc -y`
- pip: `pip install -r requirements.txt` or `pip install -U APScheduler emoji OpenCC pyAesCrypt pyrogram[fast]`

## Files

- assets
    - `chengyu.txt` : From [THUOCL](http://thuocl.thunlp.org)
    - `food.txt` : From [THUOCL](http://thuocl.thunlp.org)
    - `none.png` : Blank image
- plugins
    - functions
        - `captcha.py` : Functions about CAPTCHA
        - `channel.py` : Functions about channel
        - `etc.py` : Miscellaneous
        - `file.py` : Save files
        - `filters.py` : Some filters
        - `group.py` : Functions about group
        - `ids.py` : Modify id lists
        - `receive.py` : Receive data from exchange channel
        - `telegram.py` : Some telegram functions
        - `timers.py` : Timer functions
        - `user.py` : Functions about user and channel object
    - handlers
        - `callback.py` : Handle callbacks
        - `command.py` : Handle commands
        - `message.py`: Handle messages
    - `glovar.py` : Global variables
- `.gitignore` : Ignore
- `config.ini.example` -> `config.ini` : Configuration
- `LICENSE` : GPLv3
- `main.py` : Start here
- `README.md` : This file
- `requirements.txt` : Managed by pip

## Contribute

Welcome to make this project even better. You can submit merge requests, or report issues.

## License

Licensed under the terms of the [GNU General Public License v3](LICENSE).
