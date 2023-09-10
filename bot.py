#!/usr/bin/env python3

import time
import re
import requests
import sys
import random
import os

# pymumble
import pymumble_py3
from pymumble_py3.messages import TextMessage
from pymumble_py3.callbacks import PYMUMBLE_CLBK_TEXTMESSAGERECEIVED as TEXT_RECEIVED
from pymumble_py3.callbacks import PYMUMBLE_CLBK_USERCREATED as USER_CREATED
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

from mcstatus import JavaServer

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
mumble = pymumble_py3.Mumble(server, nick, password=passwd, reconnect=True, certfile="data/public.pem", keyfile="data/private.pem")
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
cur.execute("""CREATE TABLE IF NOT EXISTS intros (id INTEGER PRIMARY KEY, date INTEGER, author text, content text, created_time TIMESTAMP);""")
cur.close()

class Sounds:
    sound_filenames = [x for x in os.listdir("data/sounds/") if x[0] != "."]
    sound_names = [x.split(".")[0] for x in sound_filenames if x[0] != "."]
    sound_filenames.sort()
    sound_names.sort()
    sound_map = {key: value for (key, value) in zip(sound_names, sound_filenames)}
    sounds_joined = "|".join(sound_names)
    sounds_re = re.compile(f"^({sounds_joined})((p|r|e|$){{1,4}})$")

def cmd_reload(args: list):
    Sounds.sound_filenames = [x for x in os.listdir("data/sounds/") if x[0] != "."]
    Sounds.sound_names = [x.split(".")[0] for x in Sounds.sound_filenames if x[0] != "."]
    Sounds.sound_filenames.sort()
    Sounds.sound_names.sort()
    Sounds.sound_map = {key: value for (key, value) in zip(Sounds.sound_names, Sounds.sound_filenames)}
    Sounds.sounds_joined = "|\\b".join(Sounds.sound_names)
    Sounds.sounds_re = re.compile(f"^({Sounds.sounds_joined})((p|r|e|$){{1,4}})$")

def add_af_helper(af, append):
    if not af:
        af += append
    else:
        af += f",{append}"
    return af

def sound_command(filename, pitch_shift=False, reverse=False, reverb=False):
    cmd = ["ffmpeg", "-i", filename, "-ac", "1", "-f", "s16le", "-ar", "48000"]
    af = ""

    if pitch_shift:
        meme = random.randint(1, 15) / 10
        af = add_af_helper(af, f"asetrate=44100*{meme},aresample=44100,atempo=1/{meme}")

    if reverse:
        af = add_af_helper(af, "areverse")

    if af:
        cmd += ["-af", af]
    else:
        cmd = ["ffmpeg", "-i", filename, "-ac", "1", "-f", "s16le", "-ar", "48000"]

    cmd.append("-")

    if reverb:
        sp = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL,
                              stdin=subprocess.DEVNULL)

        cmd_reverb = ["ffmpeg",
                      "-f",
                      "s16le",
                      "-i",
                      "pipe:",
                      "-i",
                      "data/tunnel_entrance_b_4way_mono.wav",
                      "-filter_complex",
                      '[0] [1] afir=dry=9:wet=2 [reverb]; [0] [reverb] amix=inputs=2:weights=10 8',
                      "-f",
                      "s16le",
                      "-"]
        sp_reverb = subprocess.Popen(cmd_reverb, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL,
                              stdin=sp.stdout)


        result = sp_reverb.stdout.read()
        mumble.sound_output.add_sound(result)

    else:
        sp = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL,
                              stdin=subprocess.DEVNULL).stdout.read()
        mumble.sound_output.add_sound(sp)

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

        if title is None:
            return

        mumble.my_channel().send_text_message("[Title] {}".format(title))

    else:
        print("Didn't match a http link", match)

    match_intensify = re_intensify.match(msg_fake)

    if match_intensify is not None:
        mumble.my_channel().send_text_message(f"<span style='font-size: 36px'><b>[{match_intensify.group(1).upper()} INTENSIFIES]</b></span>")

    match_implying = re_implying.match(msg)
    pitched = False
    reversed = False
    reverb = False

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

    elif msg.startswith(".sounds"):
        mumble.my_channel().send_text_message(f"[<i>{Settings.bot_nickname}</i>] List of sound commands: {' | '.join(Sounds.sound_names)}")


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

        if cmd_fname is not None: # we haven't found a command that matches, return early

            args = msg[1:] or None

            if cmd_fname in _GLOBALS:
                if "cmd_remind" == cmd_fname:
                    return_value = _GLOBALS[cmd_fname](args, mumble.users[data.actor])

                elif "cmd_intro" == cmd_fname:
                    return_value = _GLOBALS[cmd_fname](args, mumble.users[data.actor])

                else:
                    return_value = _GLOBALS[cmd_fname](args)

                if return_value is None:
                    print("[<i>{0}</i>] Error: return value is None.".format(fname))
                    # mumble.my_channel().send_text_message("[<i>{0}</i>] Error.".format(fname))
                else:
                    mumble.my_channel().send_text_message("{0}".format(return_value))
            else:
                # It oculd be a sound
                print("Ignored.")
        else:
            # Could be a sound
            sounds_re_match = Sounds.sounds_re.match(fname)

            if sounds_re_match is not None:
                matched_sound = sounds_re_match.group(1)
                soundfile = Sounds.sound_map[matched_sound]
                bruh_file = f"data/sounds/{soundfile}"

                modifiers = sounds_re_match.group(2)

                if "p" in modifiers:
                    pitched = True
                if "r" in modifiers:
                    reversed = True
                if "e" in modifiers:
                    reverb = True

                sound_command(bruh_file, pitched, reversed, reverb)



def on_userjoin(data):
    print("User joined!!")
    username = data["name"]

    connection = sqlite3.connect("reminds.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = connection.cursor()
    c.execute("SELECT * FROM intros WHERE author = ?", (username,))
    res = c.fetchone()

    if not res:
        output = f"Welcome, {username}. "
    else:
        sound_name = res[3]
        output = f"Welcome, {username}. Sound: {sound_name}"

        sound_gaga = Sounds.sound_map.get(sound_name)
        if sound_gaga:
            sound_command(os.path.join("data/sounds/", sound_gaga))
        else:
            output += f". Sound {sound_name} not found."

    mumble.my_channel().send_text_message(output)

mumble.callbacks.set_callback(TEXT_RECEIVED, on_message)
mumble.callbacks.set_callback(USER_CREATED, on_userjoin)

def cmd_intro(args: list, _from: str="") -> str:
    if args:
        data = " ".join(args)
    else:
        data = None

    username = _from["name"]

    if not _from:
        return "Couldn't find your username."

    try:
        conn = sqlite3.connect("reminds.db", detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        c.execute("SELECT * FROM intros WHERE author = ?", (username,))
        res = c.fetchone()

        if not data and res:
            return f"Your sound is `{res[3]}`"

        if not res:
            c.execute("INSERT INTO intros (id, author, content, created_time) values (NULL, ?, ?, ?)",
                  (username, data, datetime.datetime.now()))
        else:
            c.execute("UPDATE intros SET content = (?) WHERE author = (?)", (data, username))

        conn.commit()
        conn.close()

        return "Saved, cya next time!"

    except Exception as e:
        print(e)
        return "Sry, I failed."


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
                        # print("[STREAM] new 'deleteStream' log entry")

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
                            pass
                            # print(f"[STREAM] I have never seen this stream ({session_id}), so I can't mark this as deleted.")
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


def check_minecraft_servers(timer, mc_players_old, just_started=False):
    timer += 1

    if timer > 15 or just_started:
        timer = 0  # Reset timer, regardless of result
        try:
            minecraft_servers = Settings.minecraft_servers

            for server in minecraft_servers:
                mc_server = JavaServer.lookup(f"{server['ip']}:{server['port']}")
                status = mc_server.status()

                mc_players = [player.name for player in status.players.sample] if status.players.sample else []

                # Convert both old and current player lists to sets for efficient comparison
                mc_players_set = set(mc_players)
                mc_players_old_set = set(mc_players_old)

                # Find new players (players in the current set but not in the old set)
                new_players = mc_players_set - mc_players_old_set

                if new_players:
                    if not just_started:
                        # Announce the new player(s)
                        new_players_text = ', '.join(new_players)
                        mumble.my_channel().send_text_message(
                            f"""<br />
                            <span style="font-size:8pt"><b style="color:#ff5558">{new_players_text}</b> joined:<br />
                            {status.motd.parsed[0]}<br />
                            players: {status.players.online}/{status.players.max}</span>"""
                        )

            # Update the old player list after processing all servers
            mc_players_old = mc_players

        except Exception as e:
            print("Failed to contact Minecraft servers:", str(e))

    return timer, mc_players_old



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
mc_players_old = []
timer = 0


# Run periodic stuff manually first, to get initial states in
streams_value = check_streams(streams_value, initial_start)
ag_records_value = check_ag_records(streams_value, initial_start)
ag_server_value, players_old = check_ag_server(streams_value, players_old, initial_start)
mc_server_value, mc_players_old = check_minecraft_servers(timer, mc_players_old, initial_start)

while True: # Run periodically in the non-pymumble thread
    value = check_remind(value)
    streams_value = check_streams(streams_value)
    ag_records_value = check_ag_records(ag_records_value)
    ag_server_value, players_old = check_ag_server(ag_server_value, players_old)

    mc_server_value, mc_players_old = check_minecraft_servers(mc_server_value, mc_players_old)

    time.sleep(1)
