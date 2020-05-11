# SCP-079-CAPTCHA

This bot is used to provide challenges for newly joined members.

## How to use

- Read [the document](https://scp-079.org/captcha/) to learn more
- [README](https://scp-079.org/readme/) of the SCP-079 Project's demo bots
- Discuss [group](https://t.me/SCP_079_CHAT)

## Requirements

- Python 3.6 or higher
- Debian 10: `sudo apt update && sudo apt install fonts-arphic-gkai00mp fonts-freefont-ttf opencc -y`
- pip: `pip install -r requirements.txt` 
- or pip: `pip install -U APScheduler captcha claptcha emoji OpenCC Pillow pyAesCrypt pyrogram pyyaml tgcrypto`

## Files

- assets
    - `chengyu.txt` : From [THUOCL](http://thuocl.thunlp.org)
    - `fail.png` : Image for failure
    - `food.txt` : From [THUOCL](http://thuocl.thunlp.org)
    - `none.png`: Image for none
    - `succeed.png` : Image for success
- languages
   - `cmn-Hans.yml` : Mandarin Chinese (Simplified)
   - `en.yml` : English
- plugins
    - functions
        - `captcha.py` : Functions about CAPTCHA
        - `channel.py` : Functions about channel
        - `command.py` : Functions about command
        - `decorators.py` : Some decorators
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

Welcome to make this project even better.

If you are willing to contribute, please [apply](https://t.me/SCP_079_TICKET_BOT) to join our private group on GitLab.

## Translation

- [Choose Language Tags](https://www.w3.org/International/questions/qa-choosing-language-tags)
- [Language Subtag Registry](https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry)

## License

Licensed under the terms of the [GNU General Public License v3](LICENSE).
