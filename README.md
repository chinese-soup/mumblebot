# Mumblebot

## About
* This is a very simple, yet extensible **Mumble bot** replying to chat message commands (think: IRC-like bot) built on the [pymumble](https://github.com/azlux/pymumble) library.

## Requirements
* Python >= 3.7 _(F-strings are used in the code)_
* [pymumble with py3 support](https://github.com/azlux/pymumble)
* * `protobuf`
* `requests`
* and more listed in [requirements.txt](requirements.txt)

## Usage
### Install requirements
```bash
$ # Create a virtualenv first, if needed
$ pip3 install -r requirements.txt # install requirements
$ pip3 install git+https://github.com/azlux/pymumble.git # pymumble_py3 is not avaialble in PyPI, install it from GitHub
```

### Copy/rename the settings file `settings.example.py` to `settings.py`
```bash
$ cp settings.example.py settings.py
```
### Change the `settings.py` file in your favourite text editor
* Set the `server_ip` variable to the Mumble server you want the bot to connect to.
* Set the `bot_nickname` variable to set the bot's nickname
* Change the command prefix, if needed, default "`.`" (e.g. `.kernel`) 
* Fill in the API keys for YouTube/Google/OpenWeatherMapAPI for `.youtube`/`.google`/`.weather` commands to work
* There's also code for checking when somebody joins an HLDS (Half-Life) server, you can make work by setting 
the `hlds_server_ip` and `hlds_server_port` variables.

### Start the bot:
```bash
$ python3 bot.py
```

## Available commands:
* `.remind 15min Wash the dishes` - sets a reminder that will post in 15 minutes and if espeak is available in $PATH, 
will read the reminder in voice as well, reminders are saved into an `sqlite` file database.
* `.youtube hello world` - searches for YouTube videos called "hello world", requires YouTube API key
* `.kernel` - lists current Linux kernel versions
* `.roll [number]` - rolls a number between 0-100, or between 0 and `[number]`
* `.currency 1 EUR CZK` - converts between currencies, using daily data from Czech National Bank
* `.weather Prague` - shows weather for the specified location, OpenWeatherAPI key is required to be set

## Extending with more commands
* Add a new function to `commands.py` with name in the format `cmd_CMDNAME`:
```python
def cmd_helloworld(args):
    return "Hello World!"
```
* After restarting the bot (see [Limitations](#Limitations)), the `.helloworld` command will now be available.
* The `args` parameter is a list of parameters passed to the command in chat, e.g. `.helloworld Hello World`
results in args holding: 
`args = ["Hello", "World"]`
* The return value of the command gets posted to the Mumble chat (see `on_message` in `bot.py`).

## Limitations
* Unability to disable / enable / create commands on-the-fly, i.e. bot needs to be restarted
