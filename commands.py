#!/usr/bin/env python3
import requests
import sys
import re
import json
import urllib.request
from bs4 import BeautifulSoup
from random import randint
import datetime
from tabulate import tabulate

# For obtaining Half-Life server info
import a2s

# For databases (.remind)
import sqlite3

# GeoIP for rtmp stream announcements
from geoip import geolite2

from settings import Settings

# Pre-compiled regular expressions
from regexp import _wiki_regex

# Bot utils
from utils import Utils


def cmd_remind(args: list, _from: str="N/A") -> str:
    date = " ".join(args)
    print(date)
    print(_from)
    dt, data = Utils._parse_time(date)

    if dt is None or data is None:
        return "Failed to parse timestamp."

    print(dt, data)
    if dt.year > 2030:
        return "Failed, date must be year < 2030."
    elif dt < datetime.datetime.now():
        return "Failed, can't remind to the past."
    try:
        conn = sqlite3.connect("reminds.db", detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        c.execute("INSERT INTO reminds (id, date, author, content, created_time) values (NULL, ?, ?, ?, ?)",
                  (dt.timestamp(), _from["name"], data, datetime.datetime.now()))

        conn.commit()
        conn.close()
        print(dt, data)

        return "Saved, maybe. Will remind you <b>{}</b> @ {} ".format(str(data), dt.strftime("%a %d.%m.%Y %H:%M:%S"))

    except Exception as e:
        print(e)
        return "Sry, I failed."


def cmd_roll(args: list) -> str:
    if args is None:
        maximum = 100
    else:
        try:
            maximum = int(args[0])
            if maximum >= 2147483647:
                maximum = 2147483647
        except ValueError:
            return "Error, can't cast number to integer."

    return u"{}".format(randint(0, maximum))


def cmd_google(args: list) -> str:
    inp = " ".join(args)
    payload = {"key": Settings.youtube_key, "q": inp, "cx": Settings.google_cx}
    request = requests.get(Settings.google_api_url, params=payload)

    print(request.text)
    json_res = request.json()

    if "error" in request.text:
        return "Error performing search."

    final = "<ol>"
    c = 0
    for i in json_res["items"]:
        if c < 3:
            url = i["link"]
            title = i["title"]
            final += "<li><b>{0}</b> <a href='{1}'>{1}</a></li>".format(title, url)
        else:
            break
        c += 1

    final += "</ol>"

    return final


def cmd_wiki(args: list) -> str:
    langcode = "en"
    args = " ".join(args)
    match = re.match(_wiki_regex, args)
    if match is not None:
        langcode = match.group(2)
        word = match.group(3)
        return Utils.get_wiki_result(langcode, word)
    else:
        return "Usage: .wiki [langcode] <query>"


def cmd_kernel(args: list) -> str:
    contents = requests.get("https://www.kernel.org/finger_banner").text
    contents = re.sub(r"The latest(\s*)", "", contents)
    contents = re.sub(r"version of the Linux kernel is:(\s*)", "- ", contents)
    lines = contents.split("\n")

    message = "Linux kernel versions: "
    message += ", ".join(line for line in lines[:-1])
    return message


def cmd_pure(args: list) -> str:
    if not args:
        info = a2s.info((Settings.hlds_server_ip, Settings.hlds_server_port))
        mapname = info.map_name
        number = 5
    else:
        mapname = args[0]
        if len(args) > 1:
            number = int(args[1])
        else:
            number = 5

    if mapname:
        ret_code = Utils.get_map(mapname, number)
        if ret_code == 404:
            ret_code = Utils.get_map(f"bhop_{mapname}", number) # Not found? Try bhop_MAPNAME first.

            if ret_code == 404:
                return "Error 404"
            else:
                return ret_code
        else:
            return ret_code

    return "Error."


def cmd_server(args: list) -> str:
    try:
        players_full = a2s.players((Settings.hlds_server_ip, Settings.hlds_server_port))
        info = a2s.info((Settings.hlds_server_ip, Settings.hlds_server_port))
        players_output = ""
        for player in players_full:
            players_output += f"<li><b>{Utils.strip_nick(player.name)}</b> | Time spent: {int(player.duration)} seconds</li>"

        return f"""<a href="steam://connect/{Settings.hlds_server_ip}:{Settings.hlds_server_port}">
        Join {Settings.hlds_server_ip}:{Settings.hlds_server_port}</a>
        <ul>
        <li><b>Map:</b> {info.map_name}</li>
        <li><b>Players:</b> {info.player_count}/{info.max_players}</li>
        <li><b>Player list:</b></li>
        </ul>
        <ol>{players_output}</ol>
        """

    except:
        return "Failed to contact the game server."

def cmd_osrs_wise(username: str, skill: str, other_argument: str) -> str:   # Check if the username is a list and extract the first element
    skill_short = {
        'total': 'overall',
        'att': 'attack',
        'def': 'defence',
        'str': 'strength',
        'hp': 'hitpoints',
        'range': 'ranged',
        'pray': 'prayer',
        'mage': 'magic',
        'cook': 'cooking',
        'wc': 'woodcutting',
        'fletch': 'fletching',
        'fish': 'fishing',
        'fm, fire': 'firemaking',
        'craft': 'crafting',
        'smith': 'smithing',
        'mine': 'mining',
        'herb': 'herblore',
        'agi': 'agility',
        'thieve, theif': 'thieving',
        'slay': 'slayer',
        'farm': 'farming',
        'rc, runecraft': 'runecrafting',
        'hunt': 'hunter',
        'con, cons': 'construction',
        'sail': 'sailing',
    }

    if skill in skill_short:
        skill = skill_short[skill]

    try:
        base_url = "https://api.wiseoldman.net/v2"
        endpoint = f"/players/{username}"

        response = requests.get(base_url + endpoint)

        if response.status_code == 404:
            # Send a POST request
            post_response = requests.post(base_url + endpoint)

            if post_response.status_code == 400:
                return f"Error: Player '{username}' not found"
            elif post_response.status_code == 200:
                response = post_response
            else:
                return f"Error: error: {post_response.status_code}"

        if response.status_code == 200:
            player_data = response.json()

            # check if the account has all the juicy info on wiseoldman or not
            if 'latestSnapshot' in player_data and (player_data['latestSnapshot'] is None):
                return f"""Error: Player '{username}' is incomplete or missing<br />
                        you just posted perma cringe to wiseoldmans db"""

            account_type = player_data['type']
            account_build = player_data['build']
            account_username = player_data['displayName']

            skill_data = player_data['latestSnapshot']['data']['skills'][skill]
            skill_xp = skill_data['experience']
            skill_rank = skill_data['rank']
            skill_level = skill_data['level']
            skill_ehp = skill_data['ehp']

            return f"""
                    <b style="color:#ff5558">{skill} stats</b>
                    <ul>
                    <li><b>Name:</b> {account_username}</b></li>
                    <li><b>Experience:</b> {skill_xp:,}</li>
                    <li><b>Rank:</b> {skill_rank:,}</li>
                    <li><b>Level:</b> {skill_level}</li>
                    <li><b>EHP:</b> {skill_ehp:.2f}</li>
                    <li><b>Type:</b> {account_type} - {account_build}</li>
                    </ul>
                    """
        else:
            return f"Error: Unexpected status code {response.status_code}"

    except Exception as e:
        return f"Error: {str(e)}"
      
def cmd_follow(args):
    name = args[0]
    connection = sqlite3.connect("twitch_streams.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = connection.cursor()
    c.execute("SELECT * FROM twitch_streams WHERE username=?;", [name,])
    res = c.fetchone()
    username, id = None, 1337


    """if not res:
        #twitch_req_session = requests.session()
        #twitch_req_session.headers = Const.twitch_req_session_headers
        #get_id = twitch_req_session.get("https://api.twitch.tv/kraken/users", params={"login": name})  # TODO: Unhardcode this shit
        #if get_id.status_code == 200:
        #   get_id_json = get_id.json()
        #   if get_id_json["_total"] == 1:
        #username = get_id_json["users"][0]["display_name"]
        #id = get_id_json["users"][0]["_id"]
        #   else:
        #       return "Either NONE or more than one channel found for this channel name. Fuck you."

        else:
            return "Failure to acquire ID for the specified channel."

    else:
        return "User <b>{0}</b> is already followed.".format(name)"""

    if id:
        c.execute("""INSERT INTO twitch_streams 
        (id, username, channel_id) values (NULL, ?, ?)""", (name, id))
        connection.commit()
        connection.close()

        return "User <b>{0}</b> followed.".format(name)

    #is_live_req = twitch_req_session.get("https://api.twitch.tv/kraken/streams/{}".format(ID_COLFRA))  # TODO: Unhardcode this shit


def cmd_unfollow(args):
    name = args[0]
    connection = sqlite3.connect("twitch_streams.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = connection.cursor()
    c.execute("SELECT * FROM twitch_streams WHERE username=?;", [name, ])
    res = c.fetchone()
    username, id = None, None

    if not res:
        connection.commit()
        connection.close()
        return "Channel {0} is not followed right now.".format(name)

    else:

        c.execute("""DELETE FROM twitch_streams WHERE id = ? AND username = ?""", (res[0], res[1]))
        connection.commit()
        connection.close()
        return "User <b>{0}</b> unfollowed.".format(name)

def cmd_list(args):
    connection = sqlite3.connect("twitch_streams.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = connection.cursor()
    c.execute("SELECT * FROM twitch_streams")
    res = c.fetchall()

    if not res:
        return "Error occurred lolmao."
    else:
        output = "List of followed channels: <ul>"
        for i in res:
            output += "<li>{0} | {1} | {2}</li>".format(i[0], i[1], i[2])
        output += "</ul>"
        return output


def cmd_currency(args: list) -> str:
    """
    Converts currencies  based on data from Czech National Bank
    Example input: .currency 1 EUR CZK
    Example output: 1 EUR = 24.65 CZK
    """
    amount = args[0]
    base = args[1].upper()
    target = args[2].upper()

    if args[2].lower() == "in" or args[2].lower() == "to":
        target = args[3].upper()

    req = requests.get("https://data.kurzy.cz/json/meny/b[6]den.json", params={"base": base})

    if req.status_code == 200:
        json_res = req.json()
        if "kurzy" in json_res:
            rates = json_res.get("kurzy")

            try:
                if base == "CZK":
                    target_rate_czk = rates.get(target).get("dev_stred")
                    result = float(amount) / target_rate_czk
                elif target == "CZK":
                    base_rate_czk = rates.get(base).get("dev_stred")
                    result = base_rate_czk * float(amount)
                else:
                    target_rate_czk = rates.get(target).get("dev_stred")
                    base_rate_czk = rates.get(base).get("dev_stred")
                    jednotka_czk = rates.get(base).get("jednotka")

                    res_in_czk = base_rate_czk * float(amount) * jednotka_czk
                    result = res_in_czk / target_rate_czk
                answer = "{0} {1} = <strong>{2:0.2f} {3}</strong>".format(amount, base, result, target)

            except Exception as e:
                answer = "There was an error."
                print(f"Currency: {e}")

            return answer
    else:
        return "There was an error: {req.status_code}"


def cmd_calculator(args: list) -> str:
    inp = " ".join(args)
    headers = {"User-Agent": "Nokia5250/10.0.011 (SymbianOS/9.4; U; Series60/5.0 Mozilla/5.0; Profile/MIDP-2.1 "
                             "Configuration/CLDC-1.1 ) AppleWebKit/525 (KHTML, like Gecko) Safari/525 3gpp-gba"}
    payload = {"q": inp, "hl": "cs"}
    req = requests.get("https://www.google.com/search?", params=payload, headers=headers, timeout=3)
    soup = BeautifulSoup(req.text, "lxml")

    result = soup.find("span", text=re.compile(r'.*Kalkulačka.*')).parent.parent.parent.parent
    table_result = result.find("tbody")
    spans = table_result.find_all("span")
    a = []
    for i in spans:
        a.append(i.get_text())

    return "{0} = {1}".format(a[1], a[0])


def cmd_translate(args: list) -> str:
    inp = " ".join(args)
    regex = re.compile(r"^([a-z]+[|][a-z]+)\s+(.*)$")  # TODO: compile elsewhere so it's worth it
    match = re.match(regex, inp)

    if match is not None:
        langcode = match.group(1) or "auto|en"
        word = match.group(2)
    else:
        return "Usage: .translate [lang|pair] [words]"

    payload = {"q": word, "langpair": langcode, "ie": "UTF8"}
    headers = {"User-Agent": "Nokia5250/10.0.011 (SymbianOS/9.4; U; Series60/5.0 Mozilla/5.0; Profile/MIDP-2.1 "
                             "Configuration/CLDC-1.1 ) AppleWebKit/525 (KHTML, like Gecko) Safari/525 3gpp-gba"}
    response = requests.get("https://translate.google.com/m", params=payload, headers=headers)

    if response.status_code == 200:
        output = response.content
        cteme = BeautifulSoup(output, "lxml")
        vysledek = cteme.find("div", attrs={"dir": "ltr"})

        vysledek = vysledek.text
        return "[{0}]: {1}".format(langcode, vysledek)
    else:
        return "Error."


def cmd_intensify(args: list) -> str:
    inp = " ".join(args)
    return "<span style='font-size: 36px'><b>[{} INTENSIFIES]</b></span>".format(inp.upper())


def cmd_youtube(args: list) -> str:
    # TODO REMOVE
    base_url = 'https://www.googleapis.com/youtube/v3/'
    search_api_url = base_url + 'search?part=id,snippet'
    # api_url = base_url + 'videos?part=snippet,statistics,contentDetails'
    # video_url = "%s"

    inp = " ".join(args)
    payload = {"key": Settings.youtube_key, "q": inp}
    request = requests.get(search_api_url, params=payload)

    print(request.text)
    json_res = request.json()

    if "error" in request.text:
        return "Error performing search."

    if json_res["pageInfo"]["totalResults"] == 0:
        return "No results found."

    final = "<ol>"
    for res in range(0, len(json_res["items"])):
        if res < 3:
            video_id = json_res["items"][res]["id"]["videoId"]
            json_snippet  = json_res["items"][res]["snippet"]
            video_title = json_snippet["title"]
            video_desc = json_snippet["description"]
            video_chan = json_snippet["channelTitle"]
            video_datetime = json_snippet["publishTime"]

            final += "<li><b>{0}</b> <a href='https://youtu.be/{1}'>https://youtu.be/{1}</a> | {3} ({2})<li>".format(
                video_title, video_id, video_datetime, video_chan)

    final += "</ol>"
    return final


def _get_urban_def(word, index):
    try:
        req = requests.get("https://urbanscraper.herokuapp.com/search/{0}".format(word), timeout=5)

    except Exception as e:
        print(f"[Urban] Error sending request to urbanscrapper. Reason: {e}")
        return "[Urban] Unknown error."

    parsed = req.json()
    return "[{0}]: {1}".format(parsed[index]["term"], parsed[index]["definition"]) \
    if len(parsed[index]["definition"]) < 150 \
    else "[{0}]: {1}… (more at {2})" .format(parsed[index]["term"],
    parsed[index]["definition"][:150], "<a href='https://urbandictionary.com/define.php?term={0}'>https://urbandictionary.com/define.php?term={0}</a>".format(urllib.request.quote(word)))  # url je rozbitý


def cmd_urban(args):
    args = " ".join(args)
    m = re.match(r"([0-9]+) (.*)", args)
    if m:
        index = int(m.group(1))
        args = str(m.group(2))
    else:
        index = 0
        args = args

    return _get_urban_def(args, index)


def cmd_weather(args: list) -> str:
    location = "".join(args)
    base_url = 'https://api.openweathermap.org/data/2.5/weather'
    payload = {"q": location, "appid": Settings.openweathermap_appid, "lang": "en", "units": "metric"}

    # now, to get the actual weather
    try:
        req = requests.get(base_url, payload)
        data = req.json()
        teplota = data["main"]["temp"]
        feels_like = data.get("main").get("feels_like")
        vlhkost = data["main"]["humidity"]
        vitr_rychlost = data["wind"]["speed"]
        vitr_uhel = data["wind"]["deg"]
        name = data["name"]

        if "weather" in data:
            popis = data["weather"][0]["description"]
        else:
            popis = "?"

    except KeyError:
        return "Could not get weather for that location."

    # put all the stuff we want to use in a dictionary for easy formatting of the output
    current = f"<strong>{name}</strong>: {popis} - {teplota}°C (feels like {feels_like}°C) - " \
                f"{vlhkost}% - {vitr_rychlost}km/h {vitr_uhel}°"

    print(current)
    return current


def cmd_streaming(args: str) -> str:
    currently_live = []
    final = f"""<span><strong style='color:{Settings.header_color}'><br/>Streamer list</strong>:</span><ul>"""

    currently_live = [x for x in Utils.past_publish.values() if "deleted" not in x]

    if len(currently_live) < 1:
        final = f"<span><strong style='color:{Settings.header_color}'><br/>Sorry, no streams</strong></span><ul>"
        return final

    # build the output
    for k in range(len(currently_live)):
        if currently_live[k]["stream_key"] not in Settings.ignored_stream_keys:
            country = Utils.get_geoip(currently_live[k]["ip_addr"]) or "N/A"
            final += """<li style="margin:10px">[{0}] streaming at</b><br/>
            <a href='rtmp://pooping.men/live/{1}'>rtmp://pooping.men/live/{1}</a><br/>
            ({2})</li>""".format(country,
                                 currently_live[k]["stream_key"],
                                 currently_live[k]["timestamp"])
    final += "</ul>"

    return final


if __name__ == "__main__":
    print(cmd_translate(["cs|en j"]))
    