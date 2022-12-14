#!/usr/bin/env python3

import time
import re
import requests
import sys
import random

# pymumble
import pymumble_py3
from pymumble_py3.messages import TextMessage
from pymumble_py3.callbacks import PYMUMBLE_CLBK_TEXTMESSAGERECEIVED as TEXT_RECEIVED

# beautifulsoup
from bs4 import BeautifulSoup

# subprocess to call ffmpeg
import subprocess

# sqlite3
import sqlite3

# Bot commands
from commands import *

# Bot utils
from utils import Utils

# Half-Life server querying
import a2s
from steam import game_servers as gs

# Pre-compiled regular expressions
from regexp import _stream_all_regex, link_re, re_implying, re_intensify

if sys.argv[1]:
    server = sys.argv[1]
else:
    server = Settings.server_ip

if sys.argv[2]:
    nick = sys.argv[2]
else:
    nick = Settings.bot_nickname

passwd = Settings.server_password

# Set up pymumble
mumble = pymumble_py3.Mumble(server, nick, password=passwd, reconnect=True)
mumble.start()
mumble.is_ready()
print(mumble.users.myself)
print(dir(mumble.users))
# mumble.users.myself.deafen()
mumble.set_receive_sound(False)
_GLOBALS = globals()

# Reminders stuff
connection = sqlite3.connect("reminds.db", detect_types=sqlite3.PARSE_DECLTYPES)
cur = connection.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS reminds (id INTEGER PRIMARY KEY, date INTEGER, author text, content text, created_time TIMESTAMP);""")
cur.close()


def on_message(data):
    """
    Mumble lib on_message callback
    :param data:
    :return:
    """
    print("on_message", data)

    msg = data.message

    soup = BeautifulSoup(msg, 'lxml')
    msg_fake = soup.get_text()
    match = link_re.match(msg_fake)
    print(msg_fake)

    # TODO: MOVE v THESE v TO functions #

    if match is not None:
        print(match.group(1))
        if "youtube.com" in match.group(1) or "youtu.be" in match.group(1):
            title = Utils.get_youtube_url(match.group(1))

        else:
            title = Utils.get_url(match)

        if title is not None:
            mumble.my_channel().send_text_message("[Title] {}".format(title))

        else:
            print("Got none from get_url()")

    else:
        print("Didn't match a http link", match)

    match_intensify = re_intensify.match(msg_fake)

    if match_intensify is not None:
        mumble.my_channel().send_text_message(f"<span style='font-size: 36px'><b>[{match_intensify.group(1).upper()} INTENSIFIES]</b></span>")

    match_implying = re_implying.match(msg)

    if match_implying is not None:
        inp = match_implying

        try:
            search = inp.group(1)
        except Exception as e:
            search = inp

        try:
            num = int(inp.group(3))
        except Exception as e:
            num = -1

        try:
            filetype = inp.group(2)
        except Exception as e:
            filetype = ""

        search2 = search.replace(filetype, "")
        if "http" in search: return

        payload = {"q": search2, "key": Settings.youtube_key, "cx": Settings.youtube_cx, "searchType": "image", "fileType": filetype}
        request = requests.get(Settings.google_api_url, params=payload)

        print(request.text)
        json_res = request.json()

        data = json_res
        mumble.my_channel().send_text_message("<span style='color: #789922;'>&gt;<strong>{0}</strong></span> <a href='{1}'>{1}</a>".format(search, data["items"][num]["link"]))

    if msg.startswith(".commands") or msg.startswith(".help"):
        commands = [i.replace("cmd_", ".") if i.startswith("cmd_") else "" for i in globals()]
        mumble.my_channel().send_text_message(f"[<i>{Settings.bot_nickname}</i>] List of commands: {' '.join(commands)}")

    elif msg.startswith(Settings.command_prefix):
        msg = msg.strip().split()
        fname = msg[0].replace(Settings.command_prefix, "")
        cmd_fname = None
        available_cmds_list = [x.replace("cmd_", "") for x in list(_GLOBALS) if x.startswith("cmd_")]

        for i in available_cmds_list:
            tmp = i[0:len(fname)] # Find a command that matches, e.g. ".we" matches the ".weather" cmd
            if tmp == fname:
                cmd_fname = "cmd_{}".format(i)
                break

        if cmd_fname is None: # we haven't found a command that matches, return early
            return

        args = msg[1:] or None

        if cmd_fname in _GLOBALS:
            if "cmd_remind" == cmd_fname:
                return_value = _GLOBALS[cmd_fname](args, mumble.users[data.actor])
            else:
                return_value = _GLOBALS[cmd_fname](args)

            if return_value is None:
                print("[<i>{0}</i>] Error: return value is None.".format(fname))
                # mumble.my_channel().send_text_message("[<i>{0}</i>] Error.".format(fname))
            else:
                mumble.my_channel().send_text_message("{0}".format(return_value))
        else:
            print("Ignored.")

mumble.callbacks.set_callback(TEXT_RECEIVED, on_message)


def check_remind(timer: int) -> int:
    """
    Checks reminders every 5 seconds, if a reminder's time passed,
    posts the reminder to chat and removes it from database..
    :param timer:
    :return:
    """
    timer += 1

    if timer > 5:
        timer = 0

        conn = sqlite3.connect("reminds.db", detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        ts = datetime.datetime.now().timestamp()

        c.execute("SELECT * FROM reminds")  # WHERE date >= ? =< ;")
        for row in c:
            if int(row["date"]) < ts:
                print(row["id"])
                print(type(row["id"]))
                c.execute("DELETE FROM reminds WHERE id = ?", (int(row["id"]),))
                mumble.my_channel().send_text_message("[<i>Reminder</i>] Hey, <b>{0}</b>: {1} (saved {2})"
                                                      .format(row["author"], row["content"], row["created_time"].strftime("%a %d.%m.%Y %H:%M:%S")))

                speech = "Hey, {}, reminder: {}".format(row["author"], row["content"])
                espeak_cmd = ["espeak", "--stdout", "-a", "20", speech]
                espeak_pipe = subprocess.Popen(espeak_cmd, stdout=subprocess.PIPE).stdout

                cmd = ["ffmpeg", "-i", "-", "-ac", "1", "-f", "s16le", "-ar", "48000", "-"]
                sound = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                         stdin=espeak_pipe).stdout.read()

                mumble.sound_output.add_sound(sound)

        conn.commit()
        conn.close()

    return timer


def check_streams(timer: int, just_started: bool = False) -> int:
    """
    Checks for any new lines in the RTMP stream log
    if just_started is True, don't post anything to prevent spam,
    since we're first grabbing a cache of srevious streams,
    which may have already been posted.
    """
    timer += 1

    # Run this every 15 seconds or when script starts
    if timer > 15 or just_started:
        session = requests.session()
        timer = 0

        # Grab log file
        if Settings.stream_alert_username is not None and Settings.stream_alert_password is not None:
            session.auth = (Settings.stream_alert_username, Settings.stream_alert_password)
            log_result = session.get(Settings.stream_alert_url)

            # if succsessful
            if log_result.status_code == 200:
                log_result_text = log_result.text

                # process line of log
                for stream in _stream_all_regex.finditer(log_result_text):
                    timestamp = stream.group(1)
                    session_id = stream.group(2)
                    # group 3 is fucked
                    publish_or_delete = stream.group(4) if stream.group(6) is None else stream.group(6)
                    stream_key = stream.group(5)
                    ip_addr = stream.group(7)

                    single_stream = {"timestamp": timestamp,
                                     "stream_key": stream_key,
                                     "ip_addr": ip_addr}

                    country = Utils.get_geoip(single_stream["ip_addr"]) or "N/A"

                    # process and log 'publish' line
                    if publish_or_delete == "publish":
                        print("[STREAM] new 'publish' log entry")

                        if session_id in Utils.past_publish:
                            print("[STREAM] I already posted this: {0}".format(single_stream))
                            print("[STREAM] Ignoring ^".format(single_stream))

                        else:
                            # brand new publish
                            Utils.past_publish[session_id] = single_stream
                            print(f"[STREAM] New unseen publish. Added entry to _past_publish, session_id={session_id}")

                            # announce to mumble, make sure stream key isn't on the ignore list
                            if not just_started and single_stream["stream_key"] not in Settings.ignored_stream_keys:

                                mumble.my_channel().send_text_message(
                                    f"""<strong style='color:{Settings.header_color}'><br/>Stream alert</strong>:
                                    <span><ul style="list-style-type:none">
                                    <li>Someone [{country}] started streaming.<br/>
                                    <a href='rtmp://pooping.men/live/{single_stream["stream_key"]}'>rtmp://pooping.men/live/{single_stream["stream_key"]}</a><br/>
                                    ({single_stream["timestamp"]})</li></ul></span>"""
                                )
                            else:
                                # first time check_streams is ran the function
                                # processes all past disconnect and publishes without posting them
                                print("[STREAM] I've just started so I'm going to skip posting these to the Mumble.")

                    #  process and log 'deleteStream'
                    #  doesn't necessarily mean a stream was deleted. it's more 'disconnect'
                    elif publish_or_delete == "deleteStream":
                        print("[STREAM] new 'deleteStream' log entry")

                        if session_id in Utils.past_publish:
                            if "deleted" in Utils.past_publish[session_id]:
                                print("[STREAM] I already marked this stream as deleted: {0}".format(single_stream))

                            else:
                                # new unseen deletion
                                print("[STREAM] New unseen delete.")

                                if not just_started and Settings.announce_disconnects:  # announce disconnect to mumble (if enabled)
                                    print(f"""[STREAM] a stream just ended, session_id:{single_stream["session_id"]}""")

                                    mumble.my_channel().send_text_message(
                                        f"""<strong style='color:{Settings.header_color}'><br/>Stream ended</strong>:
                                        <br/><span>Someone [{country}] stopped streaming</span>""")

                                Utils.past_publish[session_id]["deleted"] = True

                        else:
                            print(f"[STREAM] I have never seen this stream ({session_id}), so I can't mark this as "
                                  f"deleted.")
                    else:
                        # Something is wrong in the log if we got here
                        print("[STREAM:WARN] new 'unknown' log entry: {}".format(single_stream))

                print("[STREAM] Log grab result: {}".format(log_result))
            else:
                pass
    return timer


def check_ag_server(timer, players_old, just_started=False):
    timer += 1

    if timer > 15 or just_started:
        timer = 0 # Reset timer, regardless of result
        try:
            players_full = gs.a2s_players((Settings.hlds_server_ip, Settings.hlds_server_port))

            players = [Utils.strip_nick(x["name"]) for x in players_full if not x["name"].startswith("BOT:") and not x["name"].startswith("HLKZ Dummy")]

            players_set = set(players)
            players_old_set = set(players_old)

            diff = players_set - players_old_set
            diff = list(diff)
            if len(diff) > 0:
                if not just_started:
                    info = a2s.info((Settings.hlds_server_ip, Settings.hlds_server_port))
                    rules = gs.a2s_rules((Settings.hlds_server_ip, Settings.hlds_server_port))

                    mumble.my_channel().send_text_message(
                        f"""<span style='font-size: 8pt'><b>{' | '.join(diff)} joined the AG server</b>. Map = {info.map_name}
                        | Timeleft = {rules['amx_timeleft']} |
                        <a href="steam://connect/81.2.254.217:27015">Join server</a></span>""")

            players_old = players

        except:
            print("Failed to contact server-")

    return timer, players_old


def check_ag_records(timer, just_started=False):
    timer += 1

    if timer > 10 or just_started:
        timer = 0  # Reset timer

        try:
            wr_log_result = requests.get(Settings.ag_records_url)

            if wr_log_result.status_code == 200:
                log_result_text = wr_log_result.text
                lines = log_result_text.split("\n")

                for wr in lines:
                    try:
                        if wr == "":
                            print("[AG Records] Continuing, not a WR logfile line.")
                            continue

                        wrr, hlkz, nickname, mapname, rank, typeg, recordtime = wr.split("|")

                        if wr in Utils.past_records:
                            print("I already posted this: {0}".format(wr))

                        else:
                            if len(Utils.past_records) > 35:
                                Utils.past_records.pop(0)

                            Utils.past_records.append(wr)
                            print("[AG Records] Hello, new stream appeared: {0}".format(wr))

                            if not just_started:
                                mumble.my_channel().send_text_message(
                                    f"""<span style='font-size: 8pt'><strong>New AG {typeg} record</strong>
                                    on <b>{mapname}</b>: 
                                    {nickname} is now place #{rank} with a time of {recordtime}</span>"""
                                )
                                print(f"""<span style='font-size: 8pt'><strong>New AG {typeg} record</strong>
                                    on <b>{mapname}</b>: 
                                    {nickname} is now place #{rank} with a time of {recordtime}</span>""")
                            else:
                                print("[RECORD] Sorry, I literally just booted up, ignoring all previous streams.")

                    except Exception as e:
                        print(f"[AG Records] Couldn't split to wr,hlkz,nickname,rank,type,time. Orig line = {wr}")
                    # print(res)

                else:
                    print("[STREAM] Log grab result: {}".format(wr_log_result))

        except Exception as e:
            print(f"Failed to contact server {e}")

    else:
        # print("[Server] Not yet.")
        pass

    return timer

# Prepare initial vars for periodic checks
value = 0
streams_value = 0
players_old = []
initial_start = True

# Run periodic stuff manually first, to get initial states in
streams_value = check_streams(streams_value, initial_start)
ag_records_value = check_ag_records(streams_value, initial_start)
ag_server_value, players_old = check_ag_server(streams_value, players_old, initial_start)

while True: # Run periodically in the non-pymumble thread
    value = check_remind(value)
    streams_value = check_streams(streams_value)
    ag_records_value = check_ag_records(ag_records_value)
    ag_server_value, players_old = check_ag_server(ag_server_value, players_old)

    time.sleep(1)
