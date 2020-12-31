# SCP-079-CAPTCHA

This bot is used to provide challenges for newly joined members.

## How to use

- [Demo](https://t.me/SCP_079_CAPTCHA_BOT)
- Read [the document](https://scp-079.org/captcha/) to learn more
- [README](https://scp-079.org/readme/) of the SCP-079 Project's demo bots
- Discuss [group](https://t.me/SCP_079_CHAT)

## Requirements

- Python 3.6 or higher
- Debian 10: `sudo apt update && sudo apt install fonts-arphic-gkai00mp fonts-freefont-ttf opencc -y`
- pip: `pip install -r requirements.txt` 

## Files

- assets
    - `chengyu.txt` : From [THUOCL](http://thuocl.thunlp.org)
    - `fail.png` : Image for failure
    - `food.txt` : From [THUOCL](http://thuocl.thunlp.org)
    - `none.png`: Image for none
    - `succeed.png` : Image for success
- languages
   - `cmn-Hans.yml` : Mandarin Chinese (Simplified)
   - `cmn-Hant-TW.yml` : Mandarin Chinese in Taiwan (Traditional)
   - `en.yml` : English
- plugins
    - functions
        - `challenge.py` : Functions about CAPTCHA
        - `channel.py` : Functions about channel
        - `command.py` : Functions about command
        - `config.py` : Functions about group settings
        - `decorators.py` : Some decorators
        - `etc.py` : Miscellaneous
        - `file.py` : Save files
        - `filters.py` : Some filters
        - `group.py` : Functions about group
        - `ids.py` : Modify id lists
        - `markup.py` : Get reply markup
        - `receive.py` : Receive data from exchange channel
        - `telegram.py` : Some telegram functions
        - `timers.py` : Timer functions
        - `user.py` : Functions about user and channel object
    - handlers
        - `callback.py` : Handle callbacks
        - `command.py` : Handle commands
        - `message.py`: Handle messages
    - `checker.py` : Check the format of `config.ini`
    - `glovar.py` : Global variables
    - `session.py` : Manage `bot.session`
- `.gitignore` : Ignore
- `config.ini.example` -> `config.ini` : Configuration
- `LICENSE` : GPLv3
- `main.py` : Start here
- `README.md` : This file
- `start.txt.example` -> `start.txt` : Start template
- `requirements.txt` : Managed by pip

## Contribution

Contributions are always welcome, whether it's modifying source code to add new features or bug fixes, documenting new file formats or simply editing some grammar.

You can also join the [discuss group](https://t.me/SCP_079_CHAT) if you are unsure of anything.

## Translation

- [Choose Language Tags](https://www.w3.org/International/questions/qa-choosing-language-tags)
- [Language Subtag Registry](https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry)

## License

Licensed under the terms of the [GNU General Public License v3](LICENSE).
